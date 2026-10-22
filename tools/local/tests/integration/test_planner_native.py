"""Real native cookies/nonces against an explicitly named, owned local snapshot.

PHP=/opt/homebrew/opt/php@8.3/bin/php LINKER_PLANNER_TEST_INSTANCE=p548 \
uv run --locked --project tools/local pytest \
tools/local/tests/integration/test_planner_native.py -q

This never addresses production. Test accounts use reserved .invalid addresses;
the owned local stack captures every mail. Native fixture credentials stay in
memory/environment and are never printed. Project evidence remains in this
instance's private test workspace, not in the production project store.
"""

from __future__ import annotations

import copy
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from typing import Any

import pytest

from linker_local.cli import require_php
from linker_local.instance import Instance, home
from linker_local.registry import Registry
from linker_local.wpcli import WpCli

ROOT = "/wp-json/linker/v1/planner/"


@dataclass
class Reply:
    status: int
    headers: dict[str, str]
    body: bytes

    def object(self) -> dict[str, Any]:
        value = json.loads(self.body)
        assert isinstance(value, dict)
        return value


@dataclass
class Account:
    user: int
    login: str
    password: str = field(repr=False)


class Browser:
    def __init__(self, site: str) -> None:
        self.site = site
        self.cookies = CookieJar()
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.context: dict[str, Any] = {}
        self.rest_nonce = ""

    def http(
        self,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        method: str | None = None,
    ) -> Reply:
        request = urllib.request.Request(
            self.site + path, data=body, headers=headers or {}, method=method
        )
        try:
            response = self.client.open(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return Reply(
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )

    def rpc(
        self, path: str, command: dict[str, Any], **overrides: str
    ) -> Reply:
        headers = {"Content-Type": "application/json", "Origin": self.site}
        if self.rest_nonce:
            headers["X-WP-Nonce"] = self.rest_nonce
        if self.context.get("kind") == "guest":
            headers["X-Linker-Planner-Nonce"] = self.context["nonce"]
        headers.update(overrides)
        reply = self.http(
            ROOT + path, body=json.dumps(command, separators=(",", ":")).encode(),
            headers=headers,
        )
        directives = {part.strip() for part in reply.headers.get("cache-control", "").split(",")}
        assert {"no-store", "private"} <= directives and "public" not in directives
        assert "access-control-allow-origin" not in reply.headers
        return reply

    def bootstrap(self) -> dict[str, Any]:
        reply = self.rpc("bootstrap", {"schema_version": 1})
        assert reply.status == 200, reply.body
        self.context = reply.object()
        if not self.context["cookie_confirmed"]:
            reply = self.rpc("bootstrap", {"schema_version": 1})
            assert reply.status == 200, reply.body
            self.context = reply.object()
        assert self.context["cookie_confirmed"] is True
        return self.context

    def create(self, title: str) -> dict[str, Any]:
        reply = self.rpc("rpc/projects/create", {
            "schema_version": 1, "title": title, "inputs": {}, "key": str(uuid.uuid4()),
        })
        assert reply.status == 200, reply.body
        return reply.object()

    def read(self, project: dict[str, Any]) -> Reply:
        return self.rpc("rpc/projects/read", {
            "schema_version": 1, "project_id": project["id"], "revision": None,
        })

    def native_cookie(self) -> Cookie:
        return next(c for c in self.cookies if c.name.startswith("wp_woocommerce_session_"))

    def login(self, login: str, password: str) -> None:
        self.http("/wp-login.php")
        reply = self.http("/wp-login.php", body=urllib.parse.urlencode({
            "log": login, "pwd": password, "wp-submit": "Log In",
            "testcookie": "1", "redirect_to": self.site + "/my-account/",
        }).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": self.site})
        assert reply.status == 200
        assert any(c.name.startswith("wordpress_logged_in_") for c in self.cookies)
        html = self.http("/my-account/").body.decode()
        match = re.search(r'data-rest-nonce="([a-zA-Z0-9]+)"', html)
        assert match, "the rendered account page must supply its native REST nonce"
        self.rest_nonce = match[1]

    def logout(self) -> None:
        page = self.http("/my-account/").body.decode()
        match = re.search(r'href="([^"]*(?:customer-logout|action=logout)[^"]*)"', page)
        assert match
        target = urllib.parse.urlsplit(html.unescape(match[1]))
        self.http(target.path + ("?" + target.query if target.query else ""))
        self.rest_nonce = ""


@pytest.fixture(scope="module")
def local() -> tuple[Instance, WpCli]:
    name = os.environ.get("LINKER_PLANNER_TEST_INSTANCE", "")
    if not name:
        pytest.skip("name the owned local instance explicitly")
    instance = Registry(home()).get(name)
    assert instance is not None and instance.is_provisioned()
    repo = Path(__file__).resolve().parents[4]
    plugin = instance.wp_content / "plugins/linker-tools"
    assert plugin.resolve() == (repo / "plugins/linker-tools").resolve()
    assert instance.snapshot_file.is_file(), "use the actual site snapshot"
    return instance, WpCli(require_php(), instance)


@pytest.fixture
def account(local: tuple[Instance, WpCli]) -> Iterator[Account]:
    yield from native_account(local)


@pytest.fixture
def second_account(local: tuple[Instance, WpCli]) -> Iterator[Account]:
    yield from native_account(local)


def native_account(local: tuple[Instance, WpCli]) -> Iterator[Account]:
    _, wp = local
    login = "planner_fixture_" + uuid.uuid4().hex
    password = uuid.uuid4().hex + uuid.uuid4().hex
    result = wp.run(
        "eval",
        '$login = getenv("LINKER_PLANNER_FIXTURE_LOGIN"); '
        '$id = wp_insert_user(array("user_login" => $login, '
        '"user_pass" => getenv("LINKER_PLANNER_FIXTURE_PASSWORD"), '
        '"user_email" => $login . "@example.invalid", "role" => "customer")); '
        'if (is_wp_error($id)) { throw new Exception("fixture user failed"); } echo $id;',
        env={"LINKER_PLANNER_FIXTURE_LOGIN": login, "LINKER_PLANNER_FIXTURE_PASSWORD": password},
    )
    user = int(result)
    try:
        yield Account(user, login, password)
    finally:
        wp.run("user", "delete", str(user), "--yes")


def test_native_guest_save_replay_conflict_and_private_ownership(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    scope = first.context["query_scope"]
    command = {"schema_version": 1, "title": "Native save evidence", "inputs": {}, "key": str(uuid.uuid4())}
    created = first.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    project = created.object()
    assert first.rpc("rpc/projects/create", command).object() == project
    assert first.read(project).object() == project
    assert second.read(project).status == 404
    assert second.rpc("rpc/projects/read", {"schema_version": 1, "project_id": project["id"], "revision": None}, **{
        "X-Linker-Planner-Principal-Kind": "user", "X-Linker-Planner-Principal-Subject": "wp:1:user:1",
    }).status == 404
    changed = {"schema_version": 1, "project_id": project["id"], "expected_revision": 1, "inputs": {"site": {"country": "FR"}}, "key": str(uuid.uuid4())}
    revision = first.rpc("rpc/projects/revise", changed)
    assert revision.status == 200, revision.body
    assert revision.object()["revision"] == 2
    assert first.rpc("rpc/projects/revise", changed).object() == revision.object()
    changed["key"] = str(uuid.uuid4())
    assert first.rpc("rpc/projects/revise", changed).status == 409
    assert first.rpc("rpc/projects/read", {"schema_version": 1, "project_id": project["id"], "revision": 1}).object() == project
    assert first.bootstrap()["query_scope"] == scope
    assert first.read(project).object()["inputs"] == {"site": {"country": "FR"}}


def test_nonce_origin_body_and_unknown_route_are_private(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {"schema_version": 1, "page_size": 10, "after": None}
    assert browser.rpc("rpc/projects/list", command, **{"X-Linker-Planner-Nonce": ""}).status == 403
    assert browser.rpc("rpc/projects/list", command, **{"X-Linker-Planner-Nonce": "bad"}).status == 403
    assert browser.rpc("rpc/projects/list", command, Origin="https://foreign.invalid").status == 403
    assert browser.rpc("rpc/projects/list", command, **{"Content-Type": "text/plain"}).status == 415
    assert Browser(instance.url).rpc("rpc/projects/list", command).status == 401
    assert browser.rpc("rpc/identity/claim-session", {"schema_version": 1}).status == 404
    assert browser.rpc("bootstrap", {"schema_version": True}).status == 400
    for method in ("GET", "HEAD", "OPTIONS"):
        reply = browser.http(ROOT + "unknown", headers={"Origin": "https://foreign.invalid"}, method=method)
        assert reply.status in (200, 404, 405)
        directives = {part.strip() for part in reply.headers.get("cache-control", "").split(",")}
        assert {"no-store", "private"} <= directives and "public" not in directives
        assert "access-control-allow-origin" not in reply.headers


def test_native_revoked_tampered_and_expired_cookies_cannot_read(local: tuple[Instance, WpCli]) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    project = browser.create("Native revocation evidence")
    cookie = browser.native_cookie()
    original = cookie.value
    assert isinstance(original, str)
    cookie.value = original[:-1] + ("a" if original[-1] != "a" else "b")
    assert browser.read(project).status == 401
    cookie.value = original
    guest = urllib.parse.unquote(original).split("|")[0]
    assert re.fullmatch(r"t_[a-f0-9]{30}", guest)
    # A native fixture invokes Woo's own private hash method to mint a valid
    # but expired cookie. The application contains no copy of that algorithm.
    expired = wp.run("eval", '$id = getenv("LINKER_PLANNER_FIXTURE_GUEST"); '
        '$expiry = time() - 60; $session = new WC_Session_Handler(); '
        '$hash = (new ReflectionMethod($session, "hash"))->invoke($session, $id . "|" . $expiry); '
        'echo $id . "|" . $expiry . "|" . ($expiry - 60) . "|" . $hash;',
        env={"LINKER_PLANNER_FIXTURE_GUEST": guest})
    cookie.value = urllib.parse.quote(expired)
    assert browser.read(project).status == 401
    cookie.value = original
    wp.run("eval", '(new WC_Session_Handler())->delete_session(getenv("LINKER_PLANNER_FIXTURE_GUEST"));', env={"LINKER_PLANNER_FIXTURE_GUEST": guest})
    assert browser.read(project).status == 401
    old_scope = browser.context["query_scope"]
    assert browser.bootstrap()["query_scope"] != old_scope
    assert browser.read(project).status == 404


def test_cart_token_clone_never_inherits_project_ownership(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    owner = Browser(instance.url)
    owner.bootstrap()
    project = owner.create("Cart-token ownership evidence")
    cart = owner.http("/wp-json/wc/store/v1/cart")
    assert cart.status == 200 and cart.headers.get("cart-token")
    clone = Browser(instance.url)
    token = urllib.parse.quote(cart.headers["cart-token"], safe="")
    result = clone.rpc("bootstrap?session=" + token, {"schema_version": 1})
    assert result.status == 200, result.body
    clone.bootstrap()
    assert clone.read(project).status == 404
    assert owner.read(project).status == 200


def test_native_login_claim_survives_upstream_outage_and_logout(
    local: tuple[Instance, WpCli], account: Account
) -> None:
    instance, wp = local
    user, login, password = account.user, account.login, account.password
    owner = Browser(instance.url)
    owner.bootstrap()
    project = owner.create("Native login recovery evidence")
    previous = Browser(instance.url)
    for cookie in owner.cookies:
        previous.cookies.set_cookie(copy.copy(cookie))
    previous.context = dict(owner.context)
    url = wp.run("option", "get", "linker_planner_url")
    try:
        # Only this owned instance's new planner is unavailable. Existing site
        # services, ports and other sessions are neither stopped nor changed.
        wp.run("option", "update", "linker_planner_url", "http://127.0.0.1:1/planning")
        owner.login(login, password)
        pending = wp.run("eval", 'echo (new \\Linker\\Tools\\Planner\\ClaimOutbox())->pending((int) getenv("LINKER_PLANNER_FIXTURE_USER")) ? "yes" : "no";', env={"LINKER_PLANNER_FIXTURE_USER": str(user)})
        assert pending == "yes"
        assert owner.rpc("bootstrap", {"schema_version": 1}).status == 503
    finally:
        wp.run("option", "update", "linker_planner_url", url)
    assert owner.bootstrap()["kind"] == "user"
    assert owner.context["claim_pending"] is False
    assert owner.read(project).object() == project
    assert previous.read(project).status in (401, 404)
    old_scope = previous.context["query_scope"]
    assert previous.bootstrap()["query_scope"] != old_scope
    assert previous.read(project).status == 404
    nonce = owner.rest_nonce
    owner.rest_nonce = ""
    assert owner.rpc("bootstrap", {"schema_version": 1}).status == 403
    owner.rest_nonce = nonce
    owner.logout()
    assert owner.bootstrap()["kind"] == "guest"
    assert owner.read(project).status == 404


@contextmanager
def failed_native_insert(instance: Instance) -> Iterator[str]:
    """Inject a native insert refusal in only this owned local HTTP instance.

    No application debug route or production flag is added. The short-lived
    local MU fixture checks both the local PHP server and an unpredictable
    request header, and is removed even if an assertion fails.
    """
    path = instance.wp_content / "mu-plugins/linker-planner-claim-acceptance.php"
    assert not path.exists(), "preserve an existing local fixture"
    token = uuid.uuid4().hex
    source = '''<?php
if (PHP_SAPI !== 'cli-server' || !hash_equals('TOKEN', $_SERVER['HTTP_X_LINKER_PLANNER_FIXTURE'] ?? '')) { return; }
add_filter('wp_insert_post_empty_content', static function ($empty, $post) {
    return ($post['post_type'] ?? '') === 'linker_planner_claim' ? true : $empty;
}, 10, 2);
'''
    path.write_text(source.replace("TOKEN", token))
    path.chmod(0o600)
    try:
        yield token
    finally:
        path.unlink()


def test_native_insert_failure_tickets_stay_bound_across_shared_browser_accounts(
    local: tuple[Instance, WpCli], account: Account, second_account: Account,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    first_project = browser.create("Account A insert recovery evidence")
    # Attach the fixture header to this browser's actual native requests only.
    with failed_native_insert(instance) as token:
        browser.client.addheaders = [("X-Linker-Planner-Fixture", token)]
        browser.login(account.login, account.password)
        assert browser.bootstrap()["claim_pending"] is True
        assert browser.read(first_project).status == 404
        assert any(c.name.startswith("linker_planner_transition_") for c in browser.cookies)
        browser.logout()
        browser.bootstrap()
        second_project = browser.create("Account B insert recovery evidence")
        browser.login(second_account.login, second_account.password)
        assert browser.bootstrap()["claim_pending"] is True
        tickets = [c for c in browser.cookies if c.name.startswith("linker_planner_transition_")]
        assert len(tickets) == 2
        assert all(c.has_nonstandard_attr("HttpOnly") for c in tickets)
    browser.client.addheaders = []
    assert browser.bootstrap()["claim_pending"] is False
    assert browser.read(second_project).status == 200
    assert browser.read(first_project).status == 404
    assert not any(c.name.startswith("linker_planner_transition_") for c in browser.cookies)
    # Execute the actual native background dispatcher for account A's event.
    wp.run("action-scheduler", "run", "--group=linker-planner", "--batch-size=25", "--force")
    first = Browser(instance.url)
    first.login(account.login, account.password)
    assert first.bootstrap()["kind"] == "user"
    assert first.read(first_project).status == 200
    assert first.read(second_project).status == 404


def test_actual_native_dispatch_refuses_before_its_json_parser(local: tuple[Instance, WpCli]) -> None:
    _, wp = local
    result = wp.run("eval", '''
class LinkerPlannerParserProbe extends WP_REST_Request {
    public array $parser_bytes = array();
    protected function parse_json_params() {
        $this->parser_bytes[] = strlen((string) $this->get_body());
        return parent::parse_json_params();
    }
}
$server = rest_get_server();
$bodies = array(
    '{"schema_version":1,"blob":"' . str_repeat('x', 16 * 1024 * 1024) . '"}',
    '{"schema_version":' . str_repeat('[', 100) . '1' . str_repeat(']', 100) . '}',
    '{"schema_version":' . str_repeat('[', 600) . '1' . str_repeat(']', 600) . '}',
    wp_json_encode(array('schema_version' => str_repeat('{["\\\\', 1000))),
);
$result = array();
foreach ($bodies as $body) {
    $request = new LinkerPlannerParserProbe('POST', '/linker/v1/planner/bootstrap');
    $request->set_header('content-type', 'application/json');
    $request->set_header('origin', home_url());
    $request->set_body($body);
    $response = $server->dispatch($request);
    $result[] = array('status' => $response->get_status(), 'largest_parser_input' => $request->parser_bytes ? max($request->parser_bytes) : 0);
}
echo wp_json_encode($result);
''')
    cases = json.loads(result)
    assert cases[:3] == [
        {"status": 413, "largest_parser_input": 0},
        {"status": 400, "largest_parser_input": 0},
        {"status": 400, "largest_parser_input": 0},
    ]
    # Literal quote/bracket/backslash data is not container nesting. Native
    # parsing executes, then the bootstrap schema rejects the wrong value.
    assert cases[3]["status"] == 400 and cases[3]["largest_parser_input"] > 1000


def test_permanent_engine_replay_uses_no_new_quota_after_native_receipt_forgetting(local: tuple[Instance, WpCli]) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    key = str(uuid.uuid4())
    command = {"schema_version": 1, "title": "Permanent replay evidence", "inputs": {"object": {}, "array": [], "one": 1.0}, "key": key}
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    # Mimic the native journal's receipt-forgetting boundary for this fixture
    # UUID only; do not advance global time or delete other native receipts.
    before = wp.run("eval", '''
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
unset($state['receipts'][getenv('LINKER_PLANNER_FIXTURE_OPERATION')]);
update_option($name, wp_json_encode($state), false);
echo hash('sha256', wp_json_encode($state));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": key})
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    after = wp.run("eval", 'echo hash("sha256", get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION));')
    assert before == after, "permanent replay must not reserve a new quota receipt"
    command["inputs"] = {"changed": True}
    assert browser.rpc("rpc/projects/create", command).status == 409
