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

import base64
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


def test_geometry_review_and_saved_source_use_the_actual_native_gateway(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    owner, foreign = Browser(instance.url), Browser(instance.url)
    owner.bootstrap()
    foreign.bootstrap()
    project = owner.create("Synthetic native geometry review")
    path = Path(__file__).resolve().parents[4] / "fixtures/planning/geometry-flat.json"
    geometry = json.loads(path.read_text())
    review_body = {"schema_version": 1, "project_id": project["id"], "geometry": geometry}
    report = owner.rpc("rpc/geometry/review", review_body)
    assert report.status == 200, report.body
    assert report.object()["module_count"] == 5
    assert report.object()["declared_stc_kwp"] == 2.5
    assert report.object()["engineering_status"] == "not_evaluated"
    assert owner.read(project).object()["inputs"] == {}
    assert foreign.rpc("rpc/geometry/review", {**review_body, "geometry": {}}).status == 404
    geometry["arrays"][0]["source_id"] = "missing"
    command = {"schema_version": 1, "project_id": project["id"], "expected_revision": 1, "inputs": {"geometry": geometry}, "key": str(uuid.uuid4())}
    assert owner.rpc("rpc/projects/revise", command).status == 422
    assert owner.read(project).object()["revision"] == 1
    geometry["arrays"][0]["source_id"] = "survey"
    # Correcting a refused input is a new intent, not a changed-key replay.
    command["key"] = str(uuid.uuid4())
    saved = owner.rpc("rpc/projects/revise", command)
    assert saved.status == 200, saved.body
    assert saved.object()["revision"] == 2
    assert owner.rpc("rpc/projects/revise", command).object() == saved.object()
    reopened = owner.read(project).object()
    assert reopened["inputs"] == {"geometry": geometry}
    assert owner.rpc("rpc/geometry/review", review_body).object()["geometry_sha256"] == report.object()["geometry_sha256"]


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


def test_native_recovery_grants_and_original_create_receipt_cross_login(
    local: tuple[Instance, WpCli], account: Account, second_account: Account
) -> None:
    instance, _ = local
    owner = Browser(instance.url)
    guest = owner.bootstrap()
    assert owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()["scopes"] == []
    command = {"schema_version": 1, "title": "Synthetic lost acknowledgement", "inputs": {}, "key": str(uuid.uuid4())}
    original = owner.rpc("rpc/projects/create", command).object()
    owner.login(account.login, account.password)
    signed_in = owner.bootstrap()
    page = owner.rpc("rpc/recovery/scopes", {"after": None, "schema_version": 1})
    assert page.status == 200
    assert set(page.object()["scopes"]) == {guest["query_scope"], signed_in["query_scope"]}
    assert owner.rpc("rpc/projects/create", command).object() == original
    assert owner.rpc("rpc/projects/list", {"schema_version": 1, "page_size": 20, "after": None}).object()["items"][0]["id"] == original["id"]
    assert owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": "invalid"}).status == 422
    assert owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None, "user": account.user}).status == 422
    owner.logout()
    owner.bootstrap()
    assert owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()["scopes"] == []
    assert owner.read(original).status == 404
    owner.login(second_account.login, second_account.password)
    second = owner.bootstrap()
    scopes = owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()["scopes"]
    assert signed_in["query_scope"] not in scopes and guest["query_scope"] not in scopes
    assert second["query_scope"] in scopes and owner.read(original).status == 404
    owner.logout()
    owner.login(account.login, account.password)
    renewed = owner.bootstrap()
    scopes = owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()["scopes"]
    assert {guest["query_scope"], signed_in["query_scope"], renewed["query_scope"]} <= set(scopes)
    assert second["query_scope"] not in scopes
    assert owner.rpc("rpc/projects/create", command).object() == original


def test_native_recovery_grants_paginate_without_omission_or_other_account_data(
    local: tuple[Instance, WpCli], account: Account
) -> None:
    instance, wp = local
    synthetic = sorted(uuid.uuid4().hex + uuid.uuid4().hex for _ in range(67))
    result = wp.run("eval", '$registry = new \\Linker\\Tools\\Planner\\RecoveryScopes(); foreach (json_decode(getenv("LINKER_PLANNER_FIXTURE_SCOPES"), true) as $scope) { if (!$registry->remember((int) getenv("LINKER_PLANNER_FIXTURE_USER"), $scope)) { throw new Exception("scope fixture failed"); } } echo "ok";', env={"LINKER_PLANNER_FIXTURE_USER": str(account.user), "LINKER_PLANNER_FIXTURE_SCOPES": json.dumps(synthetic)})
    assert result == "ok"
    owner = Browser(instance.url)
    owner.login(account.login, account.password)
    owner.bootstrap()
    scopes: list[str] = []
    after = None
    while True:
        page = owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": after}).object()
        assert 0 < len(page["scopes"]) <= 32
        assert page["scopes"] == sorted(set(page["scopes"]))
        assert after is None or page["scopes"][0] > after
        scopes.extend(page["scopes"])
        after = page["next"]
        if after is None:
            break
    assert len(scopes) == len(set(scopes))
    assert set(synthetic) <= set(scopes)


@contextmanager
def failed_native_dispatch(instance: Instance) -> Iterator[str]:
    """Local-only timeout after quota dispatch, before an engine mutation.

    Unlike a missing engine during replay, this leaves an actual dispatched
    native receipt with no permanent engine receipt. Recovery must handle both.
    """
    path = instance.wp_content / "mu-plugins/linker-planner-dispatch-acceptance.php"
    assert not path.exists()
    token = uuid.uuid4().hex
    source = '''<?php
if (PHP_SAPI !== 'cli-server' || !hash_equals('TOKEN', $_SERVER['HTTP_X_LINKER_PLANNER_FIXTURE'] ?? '')) { return; }
add_filter('pre_http_request', static function ($pre, $args, $url) {
    if (str_ends_with($url, '/projects/create') && !str_contains($url, '/operations/replay/')) { return new WP_Error('synthetic_dispatch_timeout', 'Synthetic local dispatch refusal'); }
    return $pre;
}, 10, 3);
'''
    path.write_text(source.replace("TOKEN", token))
    path.chmod(0o600)
    try:
        yield token
    finally:
        path.unlink()


def test_native_uncommitted_dispatched_guest_intent_can_retry_after_login(
    local: tuple[Instance, WpCli], account: Account
) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {"schema_version": 1, "title": "Synthetic admitted but uncommitted request", "inputs": {}, "key": str(uuid.uuid4())}
    with failed_native_dispatch(instance) as token:
        reply = browser.rpc("rpc/projects/create", command, **{"X-Linker-Planner-Fixture": token})
        assert reply.status == 503
    assert browser.rpc("rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}).object()["items"] == []
    browser.login(account.login, account.password)
    browser.bootstrap()
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    assert len(browser.rpc("rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}).object()["items"]) == 1


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


def test_native_parser_limits_cover_unsupported_methods_and_reused_requests(local: tuple[Instance, WpCli]) -> None:
    _, wp = local
    result = wp.run("eval", '''
class LinkerPlannerMethodProbe extends WP_REST_Request {
    public array $parser_bytes = array();
    protected function parse_json_params() {
        $this->parser_bytes[] = strlen((string) $this->get_body());
        return parent::parse_json_params();
    }
}
$server = rest_get_server();
$result = array();
foreach (array('GET', 'HEAD', 'PUT', 'PATCH', 'DELETE', 'OPTIONS') as $method) {
    foreach (array(
        '{"schema_version":' . str_repeat('[', 100) . '1' . str_repeat(']', 100) . '}',
        '{"blob":"' . str_repeat('x', 16 * 1024 * 1024) . '"}',
    ) as $index => $body) {
        $request = new LinkerPlannerMethodProbe($method, '/linker/v1/planner/not-a-route');
        $request->set_header('content-type', 'application/json');
        $request->set_body($body);
        $response = $server->dispatch($request);
        $result[] = array('status' => $response->get_status(), 'largest_parser_input' => $request->parser_bytes ? max($request->parser_bytes) : 0);
    }
}
// A subrequest object can be reused by native integrations in one PHP request.
// Neither changing its route nor dispatching it again may revive a refusal.
$request = new LinkerPlannerMethodProbe('POST', '/linker/v1/planner/bootstrap');
$request->set_header('content-type', 'application/json');
$request->set_body(str_repeat('[', 100) . '1' . str_repeat(']', 100));
$server->dispatch($request);
$request->set_route('/wp/v2/types');
$request->set_method('GET');
$request->set_body('');
$response = $server->dispatch($request);
$result[] = array('status' => $response->get_status());
$request->set_route('/linker/v1/planner/bootstrap');
$request->set_method('POST');
$request->set_header('origin', home_url());
$request->set_body('{"schema_version":"invalid-but-bounded"}');
$request->parser_bytes = array();
$response = $server->dispatch($request);
$result[] = array('status' => $response->get_status(), 'largest_parser_input' => $request->parser_bytes ? max($request->parser_bytes) : 0);
echo wp_json_encode($result);
''')
    cases = json.loads(result)
    assert cases[:12] == [
        {"status": status, "largest_parser_input": 0}
        for _ in range(6)
        for status in (400, 413)
    ]
    assert cases[12] == {"status": 200}
    assert cases[13] == {"status": 400, "largest_parser_input": 40}


def test_native_journal_namespaces_owners_and_exact_engine_keys(local: tuple[Instance, WpCli]) -> None:
    instance, wp = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    key = str(uuid.uuid4())
    while key.upper() == key:
        key = str(uuid.uuid4())
    command = {"schema_version": 1, "title": "Synthetic key namespace", "inputs": {}, "key": key}
    preceding = native_operation_ids(wp)
    own = first.rpc("rpc/projects/create", command)
    foreign = second.rpc("rpc/projects/create", command)
    # The native public gateway requires its canonical lowercase UUID shape.
    # An uppercase variant is rejected before a new resource admission.
    changed_key = first.rpc("rpc/projects/create", {**command, "key": key.upper()})
    assert own.status == foreign.status == 200
    assert changed_key.status == 400
    assert own.object()["id"] != foreign.object()["id"]
    assert len(native_operation_ids(wp) - preceding) == 2
    assert first.read(foreign.object()).status == 404
    assert first.rpc("rpc/projects/create", command).object() == own.object()
    assert len(native_operation_ids(wp) - preceding) == 2


def native_operation_ids(wp: WpCli) -> set[str]:
    # Observe the actual native journal rather than recomputing its private ID.
    return set(json.loads(wp.run("eval", 'echo wp_json_encode(array_keys(json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true)["receipts"] ?? array()));')))


@pytest.mark.parametrize("committed", [False, True])
def test_legacy_native_receipt_retries_and_settles_without_new_quota(
    local: tuple[Instance, WpCli], committed: bool,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {"schema_version": 1, "title": "Synthetic legacy receipt", "inputs": {}, "key": str(uuid.uuid4())}
    preceding = native_operation_ids(wp)
    if committed:
        original = browser.rpc("rpc/projects/create", command)
        assert original.status == 200, original.body
    else:
        with failed_native_dispatch(instance) as token:
            assert browser.rpc("rpc/projects/create", command, **{"X-Linker-Planner-Fixture": token}).status == 503
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Reproduce the previous raw-UUID journal representation for this one
    # synthetic operation. Its native fingerprint, binding and debits survive.
    before = json.loads(wp.run("eval", '''
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
$key = getenv('LINKER_PLANNER_FIXTURE_KEY');
if (!isset($state['receipts'][$id]) || isset($state['receipts'][$key])) { throw new Exception('legacy fixture collision'); }
$state['receipts'][$key] = $state['receipts'][$id];
unset($state['receipts'][$id]);
$state['receipts'][$key]['status'] = 'unresolved';
update_option($name, wp_json_encode($state), false);
echo wp_json_encode(array('receipt' => $state['receipts'][$key], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id, "LINKER_PLANNER_FIXTURE_KEY": command["key"]}))
    if not committed:
        assert browser.rpc("rpc/projects/create", {**command, "title": "Changed legacy intent"}).status == 409
    reply = browser.rpc("rpc/projects/create", command)
    assert reply.status == 200, reply.body
    if committed:
        assert reply.object() == original.object()
    after = json.loads(wp.run("eval", '''
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_KEY');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_KEY": command["key"]}))
    assert before["count"] == after["count"]
    assert before["buckets"] == after["buckets"]
    assert after["receipt"]["status"] == "completed"
    assert before["receipt"]["fingerprint"] == after["receipt"]["fingerprint"]
    assert before["receipt"]["debits"] == after["receipt"]["debits"]
    assert native_id not in native_operation_ids(wp)


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("terminal", ["expired", "cancelled"])
def test_unused_native_attempts_can_continue_the_same_business_intent(
    local: tuple[Instance, WpCli], legacy: bool, terminal: str,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {"schema_version": 1, "title": "Synthetic unused reservation", "inputs": {}, "key": str(uuid.uuid4())}
    preceding = native_operation_ids(wp)
    with failed_native_dispatch(instance) as token:
        assert browser.rpc("rpc/projects/create", command, **{"X-Linker-Planner-Fixture": token}).status == 503
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Model the pre-dispatch crash in this one synthetic operation's journal.
    # Native Ledger.cancel/recover perform the refund, not this fixture.
    old_id = command["key"] if legacy else native_id
    before = json.loads(wp.run("eval", '''
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
$from = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
$id = getenv('LINKER_PLANNER_FIXTURE_OLD_ID');
$receipt = $state['receipts'][$from];
unset($state['receipts'][$from]);
$receipt['status'] = 'reserved';
if (getenv('LINKER_PLANNER_FIXTURE_TERMINAL') === 'expired') {
    $receipt['created_at'] = time() - 31;
    $receipt['lease_until'] = time() - 1;
}
$state['receipts'][$id] = $receipt;
update_option($name, wp_json_encode($state), false);
if (getenv('LINKER_PLANNER_FIXTURE_TERMINAL') === 'cancelled') {
    $cancelled = (new \\Linker\\Commerce\\Protection\\Ledger())->cancel($id, $receipt['fingerprint']);
    if (is_wp_error($cancelled)) { throw new Exception('fixture cancel failed'); }
}
echo wp_json_encode(array('receipt' => $receipt, 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id, "LINKER_PLANNER_FIXTURE_OLD_ID": old_id, "LINKER_PLANNER_FIXTURE_TERMINAL": terminal}))
    assert browser.rpc("rpc/projects/create", {**command, "title": "Changed unused intent"}).status == 409
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    after = json.loads(wp.run("eval", '''
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OLD_ID');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_OLD_ID": old_id}))
    assert after["receipt"]["status"] == terminal
    assert before["buckets"] == after["buckets"], "refund plus replacement consumes one attempt, not two"
    assert before["count"] + 1 == after["count"]
    before_receipt = {**before["receipt"], "status": terminal}
    assert before_receipt == after["receipt"], "the original terminal receipt is never rewritten"
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    assert len(native_operation_ids(wp)) == after["count"]
    projects = browser.rpc("rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}).object()
    assert len(projects["items"]) == 1


def test_permanent_engine_replay_uses_no_new_quota_after_native_receipt_forgetting(local: tuple[Instance, WpCli]) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    key = str(uuid.uuid4())
    command = {"schema_version": 1, "title": "Permanent replay evidence", "inputs": {"object": {}, "array": [], "one": 1.0}, "key": key}
    preceding = native_operation_ids(wp)
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Mimic the native journal's receipt-forgetting boundary for this fixture
    # UUID only; do not advance global time or delete other native receipts.
    before = wp.run("eval", '''
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
unset($state['receipts'][getenv('LINKER_PLANNER_FIXTURE_OPERATION')]);
update_option($name, wp_json_encode($state), false);
echo hash('sha256', wp_json_encode($state));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id})
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    after = wp.run("eval", 'echo hash("sha256", get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION));')
    assert before == after, "permanent replay must not reserve a new quota receipt"
    command["inputs"] = {"changed": True}
    assert browser.rpc("rpc/projects/create", command).status == 409


def test_profile_preview_and_csv_issue_cross_the_real_native_gateway(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    project = first.create("Synthetic native profile interpretation")
    mapping = {
        "timestamp_column": "time", "value_column": "power", "measurement": "gross_load",
        "value_kind": "interval_average_kw", "timestamp_role": "start", "timezone": "Europe/Oslo",
        "origin": "synthetic", "interval_seconds": 900, "delimiter": ";", "decimal": ",",
        "end_timestamp_column": None, "fold_column": None, "end_fold_column": None,
        "offset_rule": "explicit_offset_precedes_naive_timezone", "within_interval_assumption": "constant_mean_no_new_observations",
    }
    raw = b"time;power\n2024-01-01T00:00Z;4\n2024-01-01T00:30Z;8\n"
    command = {"schema_version": 1, "project_id": project["id"], "content_base64": base64.b64encode(raw).decode(), "mapping": mapping, "source_label": "Synthetic native fixture", "rights_note": "Generated in this local fixture", "key": str(uuid.uuid4())}
    imported = first.rpc("rpc/profiles/csv", command)
    assert imported.status == 200, imported.body
    asset = imported.object()
    request = {"schema_version": 1, "project_id": project["id"], "asset_id": asset["id"], "offset": 0, "page_size": 1}
    preview = first.rpc("rpc/profiles/preview", request)
    assert preview.status == 200, preview.body
    document = preview.object()
    assert document["content_sha256"] == asset["content_sha256"]
    assert document["summary"]["gap_count"] == 1
    assert document["summary"]["gap_seconds"] == 900
    assert document["summary"]["energy_kwh"] == 3
    assert document["summary"]["max_interval_mean_kw"] == 8
    assert document["rows"][0]["interval_mean_kw"] == 4 and document["next_offset"] == 1
    assert second.rpc("rpc/profiles/preview", request).status == 404
    failed = first.rpc("rpc/profiles/csv", {**command, "key": str(uuid.uuid4()), "content_base64": base64.b64encode(b"time;power\nPRIVATE-CELL;4\n").decode()})
    assert failed.status == 422
    assert failed.object() == {"error": {"code": "invalid_input", "profile_issue": {"issue": "timestamp_format", "line": 2, "field": "timestamp"}}}
    assert b"PRIVATE-CELL" not in failed.body


def test_equivalent_wire_replay_settles_the_same_canonical_native_receipt(local: tuple[Instance, WpCli]) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    key = str(uuid.uuid4())
    command = {"schema_version": 1, "title": "Canonical native receipt", "inputs": {"object": {}, "array": [], "one": 1.0}, "key": key}
    preceding = native_operation_ids(wp)
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    before = json.loads(wp.run("eval", '''
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
$state['receipts'][$id]['status'] = 'unresolved';
update_option($name, wp_json_encode($state), false);
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id}))
    reply = browser.http(ROOT + "rpc/projects/create", body=json.dumps(command, indent=2, sort_keys=True).encode(), headers={
        "Content-Type": "application/json", "Origin": instance.url,
        "X-Linker-Planner-Nonce": browser.context["nonce"],
    })
    assert reply.status == 200 and reply.object() == created.object()
    after = json.loads(wp.run("eval", '''
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
''', env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id}))
    assert after["receipt"]["status"] == "completed"
    assert before["count"] == after["count"] and before["buckets"] == after["buckets"]
    assert before["receipt"]["fingerprint"] == after["receipt"]["fingerprint"]
    assert before["receipt"]["debits"] == after["receipt"]["debits"]


def test_one_public_operation_key_cannot_meter_two_project_resources(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    first = browser.create("Receipt resource A")
    second = browser.create("Receipt resource B")
    csv = base64.b64encode(b"time,power\n2026-01-01T00:00:00Z,1\n2026-01-01T01:00:00Z,2\n").decode()
    commands: list[tuple[str, dict[str, Any]]] = [
        ("projects/revise", {"expected_revision": 1, "inputs": {"same": True}}),
        ("battery/scenario", {"parameters": {
            "schema_version": 1, "model": "constant_window_single_ac_bus_v1", "parameter_basis": "explicit_scenario",
            "usable_window_kwh": 10.0, "charge_ac_kw": 5.0, "discharge_ac_kw": 5.0,
            "eta_charge": 0.95, "eta_discharge": 0.95, "internal_aux_kw": 0.0, "standing_loss_rate_per_hour": 0.0,
        }, "source_note": "Synthetic native integration scenario"}),
        ("profiles/csv", {"content_base64": csv, "source_label": "Synthetic native integration profile", "rights_note": "Locally generated fixture", "mapping": {
            "timestamp_column": "time", "value_column": "power", "measurement": "gross_load",
            "value_kind": "interval_average_kw", "timestamp_role": "start", "timezone": "UTC", "origin": "synthetic",
            "interval_seconds": 3600.0, "delimiter": ",", "decimal": ".", "end_timestamp_column": None,
            "fold_column": None, "end_fold_column": None, "offset_rule": "explicit_offset_precedes_naive_timezone",
            "within_interval_assumption": "constant_mean_no_new_observations",
        }}),
    ]
    for path, fields in commands:
        command = {"schema_version": 1, **fields, "project_id": first["id"], "key": str(uuid.uuid4())}
        accepted = browser.rpc("rpc/" + path, command)
        assert accepted.status == 200, accepted.body
        changed_resource = {**command, "project_id": second["id"]}
        rejected = browser.rpc("rpc/" + path, changed_resource)
        assert rejected.status == 409, rejected.body
        assert browser.rpc("rpc/" + path, command).object() == accepted.object()
    assert browser.read(second).object()["revision"] == 1


def test_unrepresentable_numbers_are_rejected_without_changing_project_data(local: tuple[Instance, WpCli]) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    for number in (2**53, 9223372036854775809, 10**400, 1e100):
        reply = browser.rpc("rpc/projects/create", {
            "schema_version": 1, "title": "Unsupported numeric fixture",
            "inputs": {"nested": [{"number": number}]}, "key": str(uuid.uuid4()),
        })
        assert reply.status == 400, reply.body
    projects = browser.rpc("rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None})
    assert projects.object()["items"] == []
    command = {"schema_version": 1, "title": "Representable numeric fixture", "inputs": {"number": 2**53 - 1, "fraction": 0.125}, "key": str(uuid.uuid4())}
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200 and created.object()["inputs"] == command["inputs"]
    assert browser.read(created.object()).object() == created.object()
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
