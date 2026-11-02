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
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from typing import Any

import pytest

from linker_local import retirement, server, services
from linker_local.checkout import Checkout
from linker_local.cli import require_php
from linker_local.engine_release import engine_project
from linker_local.instance import Instance, home
from linker_local.planner_worker import PlannerWorker
from linker_local.processes import port_is_free
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
    claim_events: set[int] = field(default_factory=set, repr=False)
    guest_sessions: set[str] = field(default_factory=set, repr=False)


class Browser:
    def __init__(self, site: str, fixture_token: str = "") -> None:
        self.fixture_token = fixture_token
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
            self.site + path,
            data=body,
            headers={
                **(headers or {}),
                **(
                    {"X-Linker-Native-Claim": self.fixture_token}
                    if self.fixture_token
                    else {}
                ),
            },
            method=method,
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

    def rpc(self, path: str, command: dict[str, Any], **overrides: str) -> Reply:
        headers = {"Content-Type": "application/json", "Origin": self.site}
        if self.rest_nonce:
            headers["X-WP-Nonce"] = self.rest_nonce
        if self.context.get("kind") == "guest":
            headers["X-Linker-Planner-Nonce"] = self.context["nonce"]
        headers.update(overrides)
        reply = self.http(
            ROOT + path,
            body=json.dumps(command, separators=(",", ":")).encode(),
            headers=headers,
        )
        directives = {
            part.strip() for part in reply.headers.get("cache-control", "").split(",")
        }
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
        reply = self.rpc(
            "rpc/projects/create",
            {
                "schema_version": 1,
                "title": title,
                "inputs": {},
                "key": str(uuid.uuid4()),
            },
        )
        assert reply.status == 200, reply.body
        return reply.object()

    def read(self, project: dict[str, Any]) -> Reply:
        return self.rpc(
            "rpc/projects/read",
            {
                "schema_version": 1,
                "project_id": project["id"],
                "revision": None,
            },
        )

    def native_cookie(self) -> Cookie:
        return next(
            c for c in self.cookies if c.name.startswith("wp_woocommerce_session_")
        )

    def login(self, login: str, password: str) -> None:
        self.http("/wp-login.php")
        reply = self.http(
            "/wp-login.php",
            body=urllib.parse.urlencode(
                {
                    "log": login,
                    "pwd": password,
                    "wp-submit": "Log In",
                    "testcookie": "1",
                    "redirect_to": self.site + "/my-account/",
                }
            ).encode(),
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.site,
            },
        )
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


def claim_recovery_file(workspace: Path) -> Path:
    return workspace.with_name(workspace.name + ".recovery.json")


def write_claim_recovery(workspace: Path, owner: str, values: dict[str, Any]) -> None:
    """One private, owner-bound recovery record, only on incomplete cleanup."""
    path = claim_recovery_file(workspace)
    prior = json.loads(path.read_bytes()) if path.exists() else {}
    if prior:
        assert prior.get("owner") == owner and prior.get("workspace") == str(workspace)
    payload = {**prior, **values, "owner": owner, "workspace": str(workspace)}
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())


def cleanup_claim_runtime(
    instance: Instance,
    wp: WpCli,
    owner: str,
    workspace: Path,
    probe: Path,
    originals: dict[Path, tuple[bytes, int] | None],
    options: str,
    evidence: Callable[[], dict[str, tuple[int, str]]],
    original_evidence: dict[str, tuple[int, str]],
) -> None:
    """Stop independently, restore only after stop proof, and retain failed recovery."""
    failures: list[BaseException] = []
    phases: list[str] = []

    def attempt(phase: str, operation: Callable[[], object]) -> None:
        try:
            operation()
        except BaseException as error:
            phases.append(phase)
            failures.append(error)

    attempt("services_stop", lambda: services.stop(instance))
    attempt("server_stop", lambda: server.stop(instance))
    stopped = False
    try:
        assert (
            services.running(instance) == [] and server.process(instance).pid() is None
        )
        assert port_is_free(instance.port) and port_is_free(instance.engine_port)
        runtime = instance.dir / "planner/runtime.json"
        original = originals[runtime]
        assert original is not None
        assert (
            json.loads(runtime.read_bytes())["directory"] == str(workspace)
            or runtime.read_bytes() == original[0]
        )
        stopped = True
    except BaseException as error:
        phases.append("stopped_owner_proof")
        failures.append(error)
    if stopped:
        for key, entry in json.loads(options).items():

            def restore_option(key: str = key, entry: Any = entry) -> None:
                wp.run(
                    "eval",
                    'global $wpdb;foreach(json_decode(getenv("LINKER_FIXTURE_OPTIONS"),true) as $key=>$entry){if($entry["exists"]){$wpdb->update($wpdb->options,array("option_value"=>base64_decode($entry["raw"]),"autoload"=>$entry["autoload"]),array("option_name"=>$key));$row=$wpdb->get_row($wpdb->prepare("SELECT option_value,autoload FROM %i WHERE option_name=%s",$wpdb->options,$key),ARRAY_A);if(null===$row||base64_encode($row["option_value"])!==$entry["raw"]||$row["autoload"]!==$entry["autoload"]){throw new Exception("fixture option restore failed");}wp_cache_delete($key,"options");}else{delete_option($key);if(null!==$wpdb->get_var($wpdb->prepare("SELECT option_id FROM %i WHERE option_name=%s",$wpdb->options,$key))){throw new Exception("fixture option deletion failed");}}}wp_cache_delete("alloptions","options");wp_cache_delete("notoptions","options");',
                    env={"LINKER_FIXTURE_OPTIONS": json.dumps({key: entry})},
                )

            attempt("option:" + key, restore_option)
        for path, original in originals.items():

            def restore(
                path: Path = path, original: tuple[bytes, int] | None = original
            ) -> None:
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(original[0])
                    path.chmod(original[1])
                    assert path.read_bytes() == original[0]

            attempt("file:" + path.name, restore)
        attempt("probe_remove", lambda: probe.unlink(missing_ok=True))

        def unchanged() -> None:
            assert evidence() == original_evidence

        attempt("original_workspace", unchanged)

        def no_readers() -> None:
            checked = subprocess.run(
                ["/usr/sbin/lsof", "+D", str(workspace)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert (
                checked.returncode == 1
                and not checked.stdout.strip()
                and not checked.stderr.strip()
            )

        attempt("workspace_readers", no_readers)
    recovery = claim_recovery_file(workspace)

    def account_cleanup_complete() -> None:
        if recovery.exists():
            prior = json.loads(recovery.read_bytes())
            assert prior.get("owner") == owner and prior.get("workspace") == str(
                workspace
            )
            if prior.get("account_cleanup"):
                raise RuntimeError("owned account cleanup remains incomplete")

    attempt("account_cleanup", account_cleanup_complete)
    if not failures:
        attempt("workspace_remove", lambda: shutil.rmtree(workspace))
    if failures:
        write_claim_recovery(
            workspace,
            owner,
            {
                "files": {
                    str(path): None
                    if original is None
                    else {
                        "base64": base64.b64encode(original[0]).decode(),
                        "mode": original[1],
                    }
                    for path, original in originals.items()
                },
                "options": json.loads(options),
                "probe": str(probe),
                "stopped": stopped,
                "failed_phases": phases,
            },
        )
        raise BaseExceptionGroup(
            "native claim cleanup incomplete; recovery at " + str(recovery), failures
        )
    recovery.unlink(missing_ok=True)
    print(
        "native_claim_cleanup",
        json.dumps(
            {
                "workspace_absent": not workspace.exists(),
                "probe_absent": not probe.exists(),
                "original_files_unchanged": len(original_evidence),
                "services": services.running(instance),
                "ports_free": port_is_free(instance.port)
                and port_is_free(instance.engine_port),
            }
        ),
    )


@pytest.fixture
def claim_runtime(local: tuple[Instance, WpCli]) -> Iterator[None]:
    """One contained workspace; native processes stop before original restoration."""
    instance, wp = local
    owner = os.environ.get("LINKER_NATIVE_CLAIM_OWNER", uuid.uuid4().hex)
    assert re.fullmatch(r"[a-f0-9]+", owner)
    workspace = instance.dir / "planner" / ("native-claim-" + owner)
    probe = (
        instance.wp_content / "mu-plugins" / ("linker-native-claim-" + owner + ".php")
    )
    with retirement.available(home(), instance.name):
        assert (
            server.process(instance).pid() is None and services.running(instance) == []
        )
        assert port_is_free(instance.port) and port_is_free(instance.engine_port)
        assert (
            not workspace.exists()
            and not probe.exists()
            and not claim_recovery_file(workspace).exists()
        )
        assert not list(
            (instance.dir / "planner").glob("native-claim-*.recovery.json")
        ), "finish the existing owned fixture recovery before another run"
        runtime = instance.dir / "planner/runtime.json"
        original_runtime = runtime.read_bytes()
        original_workspace = Path(json.loads(original_runtime)["directory"])

        def evidence() -> dict[str, tuple[int, str]]:
            return {
                str(p.relative_to(original_workspace)): (
                    p.stat().st_mtime_ns,
                    hashlib.sha256(p.read_bytes()).hexdigest(),
                )
                for p in original_workspace.rglob("*")
                if p.is_file()
            }

        original_evidence = evidence()
        paths = [
            runtime,
            instance.docroot / "wp-config.php",
            instance.dir / "planner/worker.json",
            instance.run_dir / "planner-worker.ready.json",
        ]
        feed = instance.dir / "engine/feed.json"
        if not feed.is_symlink():
            paths.append(feed)
        originals = {
            p: (p.read_bytes(), p.stat().st_mode) if p.is_file() else None
            for p in paths
        }
        keys = [
            "linker_planner_url",
            "linker_engine_url",
            "linker_public_admission_ledger",
            "linker_planner_claim_cursor",
        ]
        options = wp.run(
            "eval",
            'global $wpdb;$out=array(); foreach(json_decode(getenv("LINKER_FIXTURE_OPTIONS"),true) as $key){$row=$wpdb->get_row($wpdb->prepare("SELECT option_value,autoload FROM %i WHERE option_name=%s",$wpdb->options,$key),ARRAY_A);if($wpdb->last_error!==""){throw new Exception("fixture option snapshot failed");}$out[$key]=array("exists"=>null!==$row,"raw"=>null===$row?null:base64_encode($row["option_value"]),"autoload"=>$row["autoload"]??null);} echo wp_json_encode($out);',
            env={"LINKER_FIXTURE_OPTIONS": json.dumps(keys)},
        )
        old_env = {
            key: os.environ.get(key)
            for key in ("LINKER_NATIVE_CLAIM_TOKEN", "LINKER_NATIVE_CLAIM_TRACE")
        }
        token = uuid.uuid4().hex
        trace = workspace / "claim-attempts"
        workspace.mkdir(mode=0o700)
        try:
            policy = json.loads(original_runtime)
            policy["directory"] = str(workspace)
            runtime.write_text(json.dumps(policy))
            source = """<?php
add_filter('action_scheduler_allow_async_request_runner', '__return_false');
$proof = $_SERVER['HTTP_X_LINKER_NATIVE_CLAIM'] ?? getenv('LINKER_NATIVE_CLAIM_TOKEN');
if (!is_string($proof) || !hash_equals('__FIXTURE_SECRET__', $proof)) { return; }
add_filter('pre_http_request', static function($pre, $args, $url) {
 if (str_ends_with($url, '/identity/claim-session')) { file_put_contents('TRACE', "claim\\n", FILE_APPEND | LOCK_EX); }
 return $pre;
}, 1, 3);
"""
            probe.write_text(
                source.replace("__FIXTURE_SECRET__", token).replace("TRACE", str(trace))
            )
            probe.chmod(0o600)
            os.environ["LINKER_NATIVE_CLAIM_TOKEN"] = token
            os.environ["LINKER_NATIVE_CLAIM_TRACE"] = str(trace)
            checkout = Checkout.here()
            uv = shutil.which("uv")
            assert uv is not None
            # Initialise only the new contained store through the selected
            # native executable, so the retained-input guard has a real DB.
            worker = PlannerWorker(
                instance,
                engine_project(instance, checkout.service("engine")),
                Path(uv),
                checkout=checkout,
            )
            worker.control("status")
            server.start(instance, wp.php)
            services.serve(instance, checkout, wp, only="engine")
            print(
                "native_claim_started",
                json.dumps(
                    {
                        "server_pid": server.process(instance).pid(),
                        "services": services.running(instance),
                        "workspace": str(workspace),
                    }
                ),
            )
            yield
        finally:
            try:
                cleanup_claim_runtime(
                    instance,
                    wp,
                    owner,
                    workspace,
                    probe,
                    originals,
                    options,
                    evidence,
                    original_evidence,
                )
            finally:
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value


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
    mail_before = set(local[0].mail_dir.glob("*.eml"))
    result = wp.run(
        "eval",
        '$login = getenv("LINKER_PLANNER_FIXTURE_LOGIN"); '
        '$id = wp_insert_user(array("user_login" => $login, '
        '"user_pass" => getenv("LINKER_PLANNER_FIXTURE_PASSWORD"), '
        '"user_email" => $login . "@example.invalid", "role" => "customer")); '
        'if (is_wp_error($id)) { throw new Exception("fixture user failed"); } echo $id;',
        env={
            "LINKER_PLANNER_FIXTURE_LOGIN": login,
            "LINKER_PLANNER_FIXTURE_PASSWORD": password,
        },
    )
    user = int(result)
    created = Account(user, login, password)
    try:
        yield created
    finally:
        try:
            wp.run(
                "eval",
                '$user=(int)getenv("LINKER_PLANNER_FIXTURE_USER"); '
                '$events=array_unique(array_merge(json_decode(getenv("LINKER_PLANNER_FIXTURE_EVENTS"),true), '
                'get_posts(array("post_type"=>"linker_planner_claim","post_status"=>"private","author"=>$user,"numberposts"=>-1,"fields"=>"ids")))); '
                'foreach($events as $id){ foreach(as_get_scheduled_actions(array("hook"=>"linker_tools_planner_claim","group"=>"linker-planner","search"=>"[".$id.",","per_page"=>-1),"ids") as $action){ '
                'if(ActionScheduler::store()->get_status($action)==="in-progress"){throw new Exception("fixture action still active");} '
                "ActionScheduler::store()->delete_action($action); } "
                "if(get_post($id)){wp_delete_post($id,true);} } "
                'foreach(json_decode(getenv("LINKER_PLANNER_FIXTURE_SESSIONS"),true) as $guest){(new WC_Session_Handler())->delete_session($guest);} '
                "(new WC_Session_Handler())->delete_session((string)$user);",
                env={
                    "LINKER_PLANNER_FIXTURE_USER": str(user),
                    "LINKER_PLANNER_FIXTURE_EVENTS": json.dumps(
                        sorted(created.claim_events)
                    ),
                    "LINKER_PLANNER_FIXTURE_SESSIONS": json.dumps(
                        sorted(created.guest_sessions)
                    ),
                },
            )
            wp.run("user", "delete", str(user), "--yes")
            remaining = json.loads(
                wp.run(
                    "eval",
                    '$events=json_decode(getenv("LINKER_PLANNER_FIXTURE_EVENTS"),true);$posts=0;$actions=0;foreach($events as $id){$posts+=null!==get_post($id)?1:0;$actions+=count(as_get_scheduled_actions(array("hook"=>"linker_tools_planner_claim","group"=>"linker-planner","search"=>"[".$id.",","per_page"=>-1),"ids"));} '
                    'global $wpdb;$sessions=array_merge(json_decode(getenv("LINKER_PLANNER_FIXTURE_SESSIONS"),true),array(getenv("LINKER_PLANNER_FIXTURE_USER"))); '
                    '$count=(int)$wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM %i WHERE session_key IN (".implode(",",array_fill(0,count($sessions),"%s")).")",$wpdb->prefix."woocommerce_sessions",...$sessions)); '
                    'echo wp_json_encode(array("user_deleted"=>false===get_userdata((int)getenv("LINKER_PLANNER_FIXTURE_USER")),"posts"=>$posts,"actions"=>$actions,"sessions"=>$count));',
                    env={
                        "LINKER_PLANNER_FIXTURE_USER": str(user),
                        "LINKER_PLANNER_FIXTURE_EVENTS": json.dumps(
                            sorted(created.claim_events)
                        ),
                        "LINKER_PLANNER_FIXTURE_SESSIONS": json.dumps(
                            sorted(created.guest_sessions)
                        ),
                    },
                )
            )
            assert remaining == {
                "user_deleted": True,
                "posts": 0,
                "actions": 0,
                "sessions": 0,
            }
            for mail in set(local[0].mail_dir.glob("*.eml")) - mail_before:
                if login.encode() in mail.read_bytes():
                    mail.unlink()
            assert set(local[0].mail_dir.glob("*.eml")) == mail_before
            print("native_claim_account_cleanup", json.dumps(remaining))
        except BaseException as error:
            trace = os.environ.get("LINKER_NATIVE_CLAIM_TRACE")
            if trace:
                workspace = Path(trace).parent
                owner = workspace.name.removeprefix("native-claim-")
                assert workspace.parent == local[0].dir / "planner"
                write_claim_recovery(
                    workspace,
                    owner,
                    {
                        "account_cleanup": {
                            "user": user,
                            "login": login,
                            "events": sorted(created.claim_events),
                            "sessions": sorted(created.guest_sessions),
                        }
                    },
                )
            error.add_note(
                "Synthetic native account cleanup incomplete for user " + str(user)
            )
            raise


def test_native_bootstrap_exposes_only_the_browser_runtime_contract(
    local: tuple[Instance, WpCli],
    account: Account,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    context = browser.bootstrap()
    cookie = browser.native_cookie()
    assert isinstance(cookie.value, str)
    account.guest_sessions.add(urllib.parse.unquote(cookie.value).split("|")[0])
    assert set(context["runtime"]) == {
        "schema_version",
        "runtime_sha256",
        "models",
        "limits",
    }
    required_limits = {
        "max_body_bytes",
        "max_csv_bytes",
        "max_page_size",
        "max_json_depth",
    }
    assert (
        required_limits
        <= set(context["runtime"]["limits"])
        <= required_limits
        | {
            "direct_beam_visibility",
            "geometric_pv_generation",
            "geometric_pv_clear_flat_roof",
            "geometric_pv_clear_pitched_roof",
        }
    )
    # Exercise the same native classes with Woo's own signed-cookie reader
    # and nonce filter, without another HTTP probe or private-service task.
    result = wp.run(
        "eval",
        r"""
use Linker\Tools\Planner\ClaimOutbox;
use Linker\Tools\Planner\Gateway;
use Linker\Tools\Planner\NativeIdentity;
use Linker\Tools\Planner\TransitionTicket;
use Linker\Tools\Planner\Transport;

global $wpdb;
$table = $wpdb->prefix . 'woocommerce_sessions';
$original_cookies = $_COOKIE;
$original_session = WC()->session;
$original_user = get_current_user_id();
$handler = new WC_Session_Handler();
$guest = $handler->generate_customer_id();
$expiry = time() + 3600;
$cookie_name = apply_filters('woocommerce_cookie', 'wp_woocommerce_session_' . COOKIEHASH);
$hash = new ReflectionMethod($handler, 'hash');
$signed = static fn($expires) => $guest . '|' . $expires . '|' . ($expires - 7200) . '|' . $hash->invoke($handler, $guest . '|' . $expires);
$cookie = $signed($expiry);
$wpdb->insert($table, array('session_key' => $guest, 'session_value' => maybe_serialize(array('fixture' => 'existing-owner')), 'session_expiry' => $expiry));
$status = 'active';
$calls = array();
$runtime_override = null;
$transport = new Transport(static function ($url, $args) use (&$status, &$calls, &$runtime_override) {
    $path = str_ends_with($url, '/identity/status') ? 'identity/status' : (str_ends_with($url, '/version') ? 'version' : 'unexpected');
    $calls[] = $path;
    $data = 'identity/status' === $path ? array('schema_version' => 1, 'status' => $status) : array('schema_version' => 1, 'runtime_sha256' => str_repeat('a', 64), 'models' => array(), 'limits' => array('max_body_bytes' => 1000000, 'max_csv_bytes' => 100000, 'max_page_size' => 20, 'max_json_depth' => 32));
    if ('version' === $path && null !== $runtime_override) { $data = $runtime_override; }
    return array('response' => array('code' => 200), 'headers' => array('content-type' => 'application/json'), 'body' => wp_json_encode($data));
});
$gateway = new Gateway(new NativeIdentity(), $transport, new ClaimOutbox($transport));
$request = static function (array $body) {
    $request = new WP_REST_Request('POST', '/linker/v1/planner/bootstrap');
    $request->set_header('content-type', 'application/json');
    $request->set_header('origin', home_url());
    $request->set_body(wp_json_encode($body));
    return $request;
};
$writes = 0;
$cookie_writes = 0;
$migrations = 0;
$query_guard = static function ($sql) use (&$writes) {
    if (preg_match('/^\s*(INSERT|UPDATE|DELETE|REPLACE)\b/i', $sql)) { ++$writes; }
    return $sql;
};
$cookie_guard = static function ($enabled) use (&$cookie_writes) { ++$cookie_writes; return $enabled; };
$migration_guard = static function () use (&$migrations) { ++$migrations; };
$run = static function (array $body, string $nonce = '') use ($gateway, $request, &$writes, &$cookie_writes, &$migrations, &$calls) {
    $request = $request($body);
    if ('' !== $nonce) { $request->set_header('x-wp-nonce', $nonce); }
    $before = array($writes, $cookie_writes, $migrations, $_COOKIE, WC()->session);
    $permission = $gateway->bootstrap_permission($request);
    $reply = is_wp_error($permission) ? $permission : $gateway->bootstrap($request);
    return array(
        'status' => is_wp_error($reply) ? $reply->get_error_data()['status'] : $reply->get_status(),
        'unchanged' => $before === array($writes, $cookie_writes, $migrations, $_COOKIE, WC()->session),
        'data' => is_wp_error($reply) ? null : $reply->get_data(),
    );
};
$mode = array('schema_version' => 1, 'existing_owner_only' => true);
$user = (int) getenv('LINKER_PLANNER_FIXTURE_USER');
$token = '';
try {
    wp_set_current_user(0);
    WC()->session = null;
    $_COOKIE = array();
    add_filter('query', $query_guard);
    add_filter('woocommerce_set_cookie_enabled', $cookie_guard);
    add_action('woocommerce_guest_session_to_user_id', $migration_guard);
    $cases = array();
    $cases['absent'] = $run($mode);
    $_COOKIE[$cookie_name] = substr($cookie, 0, -1) . ('a' === substr($cookie, -1) ? 'b' : 'a');
    $cases['forged'] = $run($mode);
    $_COOKIE[$cookie_name] = $signed(time() - 60);
    $cases['expired'] = $run($mode);
    $_COOKIE[$cookie_name] = $cookie;
    $cases['valid'] = $run(array('existing_owner_only' => true, 'schema_version' => 1));
    // The service's optional expanded budget is forwarded only as a strict
    // five-field extension to an otherwise valid ordinary geometry capability.
    $original_calls = $calls;
    $runtime_override = array('schema_version' => 1, 'runtime_sha256' => str_repeat('a', 64), 'models' => array('geometric_pv_generation' => 'prepare_geometric_pv_reference_v1'), 'limits' => array('max_body_bytes' => 1000000, 'max_csv_bytes' => 100000, 'max_page_size' => 20, 'max_json_depth' => 32, 'geometric_pv_generation' => array('index_leaf_size' => 8, 'max_bounds_checks' => 50000000, 'max_module_steps' => 220000, 'max_ray_face_checks' => 20000000, 'max_samples' => 2000000)));
    $expanded = array('max_module_steps' => 841000, 'max_samples' => 4300000, 'max_modules' => 96, 'max_strings' => 6, 'max_weather_rows' => 8760);
    $runtime_override['limits']['geometric_pv_clear_flat_roof'] = $expanded;
    $expanded_ok = $run($mode);
    unset($expanded_ok['data']['nonce'], $expanded_ok['data']['query_scope']);
    $runtime_override['limits']['geometric_pv_clear_pitched_roof'] = $expanded;
    $pitched_ok = $run($mode);
    unset($pitched_ok['data']['nonce'], $pitched_ok['data']['query_scope']);
    $runtime_override['limits']['geometric_pv_clear_pitched_roof']['max_modules'] = 97;
    $pitched_invalid = $run($mode);
    unset($runtime_override['limits']['geometric_pv_clear_pitched_roof']);
    $expanded_invalid = array();
    foreach (array(array('max_modules', 0), array('max_modules', true), array('max_strings', 7), array('extra', 1)) as $bad) {
        $runtime_override['limits']['geometric_pv_clear_flat_roof'] = $expanded;
        $runtime_override['limits']['geometric_pv_clear_flat_roof'][$bad[0]] = $bad[1];
        $expanded_invalid[] = $run($mode);
    }
    $runtime_override['limits']['geometric_pv_clear_flat_roof'] = $expanded;
    unset($runtime_override['limits']['geometric_pv_clear_flat_roof']['max_samples']);
    $expanded_invalid[] = $run($mode);
    $runtime_override['limits']['geometric_pv_clear_flat_roof'] = $expanded;
    unset($runtime_override['models']['geometric_pv_generation'], $runtime_override['limits']['geometric_pv_generation']);
    $expanded_invalid[] = $run($mode);
    $runtime_override = null;
    $calls = $original_calls;
    $nonce = $cases['valid']['data']['nonce'] ?? '';
    // Only the fixture sets an in-memory native customer ID. Verification
    // uses Woo's real public nonce filter, not the new binding's closure.
    $native = new WC_Session_Handler();
    $customer = new ReflectionProperty(WC_Session::class, '_customer_id');
    $customer->setValue($native, $guest);
    add_filter('nonce_user_logged_out', array($native, 'maybe_update_nonce_user_logged_out'), 10, 2);
    $native_nonce = false !== wp_verify_nonce($nonce, NativeIdentity::NONCE_ACTION);
    $wrong_action = false === wp_verify_nonce($nonce, 'wp_rest');
    remove_filter('nonce_user_logged_out', array($native, 'maybe_update_nonce_user_logged_out'), 10);
    $customer->setValue($native, 't_' . str_repeat('z', 30));
    WC()->session = $native;
    $cases['mismatched_handler'] = $run($mode);
    WC()->session = null;
    $status = 'retired';
    $cases['retired'] = $run($mode);
    $status = 'active';
    $malformed = array();
    foreach (array(false, 0, 'true', null) as $flag) {
        $malformed[] = $run(array('schema_version' => 1, 'existing_owner_only' => $flag));
    }
    $malformed[] = $run($mode + array('extra' => true));
    $legacy_allowed = true === $gateway->bootstrap_permission($request(array('schema_version' => 1)));
    // A valid native transition remains visible but is neither enqueued nor
    // cleared. The same mode never performs foreground claim delivery.
    remove_filter('query', $query_guard);
    $ticket = new TransitionTicket();
    $ticket->issue(NativeIdentity::guest_subject($guest), $expiry, $user);
    add_filter('query', $query_guard);
    $cases['pending_ticket'] = $run($mode);
    $row_before = $wpdb->get_row($wpdb->prepare('SELECT * FROM %i WHERE session_key=%s', $table, $guest), ARRAY_A);
    $cases['valid_again'] = $run($mode);
    $row_unchanged = $row_before === $wpdb->get_row($wpdb->prepare('SELECT * FROM %i WHERE session_key=%s', $table, $guest), ARRAY_A);
    remove_filter('query', $query_guard);
    $wpdb->delete($table, array('session_key' => $guest));
    add_filter('query', $query_guard);
    $cases['revoked'] = $run($mode);
    // Authenticated REST proof is independent of Woo migration/session state.
    remove_filter('query', $query_guard);
    wp_set_current_user($user);
    $token = WP_Session_Tokens::get_instance($user)->create(time() + 3600);
    $_COOKIE[LOGGED_IN_COOKIE] = wp_generate_auth_cookie($user, time() + 3600, 'logged_in', $token);
    $rest_nonce = wp_create_nonce('wp_rest');
    add_filter('query', $query_guard);
    $cases['account'] = $run($mode, $rest_nonce);
    $cases['account_without_nonce'] = $run($mode);
    $output = array('cases' => array_map(static function ($case) {
        unset($case['data']['nonce'], $case['data']['query_scope']);
        return $case;
    }, $cases), 'malformed' => $malformed, 'legacy_allowed' => $legacy_allowed, 'native_nonce' => $native_nonce, 'wrong_action_refused' => $wrong_action, 'row_unchanged' => $row_unchanged, 'writes' => $writes, 'cookie_writes' => $cookie_writes, 'migrations' => $migrations, 'transport_paths' => $calls, 'expanded_ok' => $expanded_ok, 'expanded_invalid' => $expanded_invalid, 'pitched_ok' => $pitched_ok, 'pitched_invalid' => $pitched_invalid);
} finally {
    remove_filter('query', $query_guard);
    remove_filter('woocommerce_set_cookie_enabled', $cookie_guard);
    remove_action('woocommerce_guest_session_to_user_id', $migration_guard);
    $wpdb->delete($table, array('session_key' => $guest));
    if ('' !== $token) { WP_Session_Tokens::get_instance($user)->destroy($token); }
    WC()->session = $original_session;
    $_COOKIE = $original_cookies;
    wp_set_current_user($original_user);
}
echo wp_json_encode($output);
""",
        env={"LINKER_PLANNER_FIXTURE_USER": str(account.user)},
    )
    evidence = json.loads(result)
    cases = evidence["cases"]
    for name in (
        "absent",
        "forged",
        "expired",
        "mismatched_handler",
        "revoked",
        "account_without_nonce",
    ):
        assert cases[name]["status"] == 401, name
    assert cases["retired"]["status"] == 403
    for name in ("valid", "valid_again", "pending_ticket", "account"):
        assert cases[name]["status"] == 200, name
        assert cases[name]["data"]["cookie_confirmed"] is True
        assert set(cases[name]["data"]["runtime"]) == set(context["runtime"])
    assert cases["valid"]["data"]["kind"] == "guest"
    assert cases["account"]["data"]["kind"] == "user"
    assert cases["pending_ticket"]["data"]["claim_pending"] is True
    assert all(case["status"] == 400 for case in evidence["malformed"])
    assert all(case["unchanged"] for case in [*cases.values(), *evidence["malformed"]])
    assert evidence["expanded_ok"]["status"] == 200
    assert evidence["expanded_ok"]["data"]["runtime"]["limits"][
        "geometric_pv_clear_flat_roof"
    ] == {
        "max_module_steps": 841000,
        "max_samples": 4300000,
        "max_modules": 96,
        "max_strings": 6,
        "max_weather_rows": 8760,
    }
    assert all(case["status"] == 502 for case in evidence["expanded_invalid"])
    assert evidence["pitched_ok"]["status"] == 200
    assert (
        evidence["pitched_ok"]["data"]["runtime"]["limits"][
            "geometric_pv_clear_pitched_roof"
        ]
        == evidence["expanded_ok"]["data"]["runtime"]["limits"][
            "geometric_pv_clear_flat_roof"
        ]
    )
    assert evidence["pitched_invalid"]["status"] == 502
    assert (
        evidence["pitched_ok"]["unchanged"] and evidence["pitched_invalid"]["unchanged"]
    )
    assert evidence["expanded_ok"]["unchanged"]
    assert all(case["unchanged"] for case in evidence["expanded_invalid"])
    assert evidence["legacy_allowed"] and evidence["native_nonce"]
    assert evidence["wrong_action_refused"] and evidence["row_unchanged"]
    assert (
        evidence["writes"] == evidence["cookie_writes"] == evidence["migrations"] == 0
    )
    assert evidence["transport_paths"] == [
        "identity/status",
        "version",
        "identity/status",  # Retired: no version request and no identity reset.
        "identity/status",
        "version",
        "identity/status",
        "version",
        "identity/status",
        "version",
    ]


def test_native_guest_save_replay_conflict_and_private_ownership(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    scope = first.context["query_scope"]
    command = {
        "schema_version": 1,
        "title": "Native save evidence",
        "inputs": {},
        "key": str(uuid.uuid4()),
    }
    created = first.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    project = created.object()
    assert first.rpc("rpc/projects/create", command).object() == project
    assert first.read(project).object() == project
    assert second.read(project).status == 404
    assert (
        second.rpc(
            "rpc/projects/read",
            {"schema_version": 1, "project_id": project["id"], "revision": None},
            **{
                "X-Linker-Planner-Principal-Kind": "user",
                "X-Linker-Planner-Principal-Subject": "wp:1:user:1",
            },
        ).status
        == 404
    )
    changed = {
        "schema_version": 1,
        "project_id": project["id"],
        "expected_revision": 1,
        "inputs": {"site": {"country": "FR"}},
        "key": str(uuid.uuid4()),
    }
    revision = first.rpc("rpc/projects/revise", changed)
    assert revision.status == 200, revision.body
    assert revision.object()["revision"] == 2
    assert first.rpc("rpc/projects/revise", changed).object() == revision.object()
    changed["key"] = str(uuid.uuid4())
    assert first.rpc("rpc/projects/revise", changed).status == 409
    assert (
        first.rpc(
            "rpc/projects/read",
            {"schema_version": 1, "project_id": project["id"], "revision": 1},
        ).object()
        == project
    )
    assert first.bootstrap()["query_scope"] == scope
    assert first.read(project).object()["inputs"] == {"site": {"country": "FR"}}


def test_geometry_import_source_manifest_and_save_use_the_actual_native_gateway(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    owner, foreign = Browser(instance.url), Browser(instance.url)
    owner.bootstrap()
    foreign.bootstrap()
    project = owner.create("Synthetic native geographic import; not surveyed")
    root = Path(__file__).resolve().parents[4]
    source = (root / "fixtures/planning/source-roof-wgs84.geojson").read_bytes()
    options = json.loads(
        (root / "fixtures/planning/geometry-import-options.json").read_text()
    )
    command = {
        "schema_version": 1,
        "project_id": project["id"],
        "content_base64": base64.b64encode(source).decode(),
        "options": options,
        "key": str(uuid.uuid4()),
    }
    imported = owner.rpc("rpc/geometry/import", command)
    assert imported.status == 200, imported.body
    asset = imported.object()
    assert owner.rpc("rpc/geometry/import", command).object() == asset
    assert asset["purpose"] == "geometry_import_v1"
    prepared = asset["metadata"]["geometry_import"]
    geometry = prepared["geometry"]
    assert (
        geometry["roofs"][0]["holes_uv"] and geometry["roofs"][0]["origin_enu"][2] == 5
    )
    assert owner.read(project).object()["revision"] == 1
    assert owner.read(project).object()["inputs"] == {}
    assert (
        foreign.rpc("rpc/geometry/import", {**command, "content_base64": "!"}).status
        == 404
    )
    invalid_id = json.loads(source)
    invalid_id["id"] = 2**54
    refused = owner.rpc(
        "rpc/geometry/import",
        {
            **command,
            "key": str(uuid.uuid4()),
            "content_base64": base64.b64encode(
                json.dumps(invalid_id).encode()
            ).decode(),
        },
    )
    assert refused.status == 422
    assert owner.read(project).object()["revision"] == 1
    assert (
        owner.rpc(
            "rpc/assets/content",
            {"schema_version": 1, "project_id": project["id"], "asset_id": asset["id"]},
        ).body
        == source
    )
    source_id = geometry["sources"][0]["id"]
    inputs = {
        "geometry": geometry,
        "geometry_imports": {"schema_version": 1, "selected": {source_id: asset["id"]}},
    }
    change = {
        "schema_version": 1,
        "project_id": project["id"],
        "expected_revision": 1,
        "inputs": inputs,
        "key": str(uuid.uuid4()),
    }
    saved = owner.rpc("rpc/projects/revise", change)
    assert saved.status == 200, saved.body
    assert saved.object()["revision"] == 2
    assert owner.rpc("rpc/projects/revise", change).object() == saved.object()
    assert owner.read(project).object()["inputs"] == inputs
    tampered = json.loads(json.dumps(inputs))
    tampered["geometry"]["sources"][0]["reference_sha256"] = "0" * 64
    assert (
        owner.rpc(
            "rpc/projects/revise",
            {
                "schema_version": 1,
                "project_id": project["id"],
                "expected_revision": 2,
                "inputs": tampered,
                "key": str(uuid.uuid4()),
            },
        ).status
        == 422
    )
    assert owner.read(project).object()["revision"] == 2
    report = owner.rpc(
        "rpc/geometry/review",
        {"schema_version": 1, "project_id": project["id"], "geometry": geometry},
    )
    assert report.status == 200 and report.object()["module_count"] == 0
    assert report.object()["engineering_status"] == "not_evaluated"


def test_geometry_review_and_saved_source_use_the_actual_native_gateway(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    owner, foreign = Browser(instance.url), Browser(instance.url)
    owner.bootstrap()
    foreign.bootstrap()
    project = owner.create("Synthetic native geometry review")
    path = Path(__file__).resolve().parents[4] / "fixtures/planning/geometry-flat.json"
    geometry = json.loads(path.read_text())
    review_body = {
        "schema_version": 1,
        "project_id": project["id"],
        "geometry": geometry,
    }
    report = owner.rpc("rpc/geometry/review", review_body)
    assert report.status == 200, report.body
    assert report.object()["module_count"] == 5
    assert report.object()["declared_stc_kwp"] == 2.5
    assert report.object()["checker"] == "roof_plane_layout_v4"
    assert report.object()["engineering_status"] == "not_evaluated"
    assert owner.read(project).object()["inputs"] == {}
    assert (
        foreign.rpc("rpc/geometry/review", {**review_body, "geometry": {}}).status
        == 404
    )
    geometry["arrays"][0]["source_id"] = "missing"
    command = {
        "schema_version": 1,
        "project_id": project["id"],
        "expected_revision": 1,
        "inputs": {"geometry": geometry},
        "key": str(uuid.uuid4()),
    }
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
    assert (
        owner.rpc("rpc/geometry/review", review_body).object()["geometry_sha256"]
        == report.object()["geometry_sha256"]
    )


def test_nonce_origin_body_and_unknown_route_are_private(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {"schema_version": 1, "page_size": 10, "after": None}
    assert (
        browser.rpc(
            "rpc/projects/list", command, **{"X-Linker-Planner-Nonce": ""}
        ).status
        == 403
    )
    assert (
        browser.rpc(
            "rpc/projects/list", command, **{"X-Linker-Planner-Nonce": "bad"}
        ).status
        == 403
    )
    assert (
        browser.rpc(
            "rpc/projects/list", command, Origin="https://foreign.invalid"
        ).status
        == 403
    )
    assert (
        browser.rpc(
            "rpc/projects/list", command, **{"Content-Type": "text/plain"}
        ).status
        == 415
    )
    assert Browser(instance.url).rpc("rpc/projects/list", command).status == 401
    assert (
        browser.rpc("rpc/identity/claim-session", {"schema_version": 1}).status == 404
    )
    assert browser.rpc("bootstrap", {"schema_version": True}).status == 400
    for method in ("GET", "HEAD", "OPTIONS"):
        reply = browser.http(
            ROOT + "unknown",
            headers={"Origin": "https://foreign.invalid"},
            method=method,
        )
        assert reply.status in (200, 404, 405)
        directives = {
            part.strip() for part in reply.headers.get("cache-control", "").split(",")
        }
        assert {"no-store", "private"} <= directives and "public" not in directives
        assert "access-control-allow-origin" not in reply.headers


def test_native_revoked_tampered_and_expired_cookies_cannot_read(
    local: tuple[Instance, WpCli],
) -> None:
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
    expired = wp.run(
        "eval",
        '$id = getenv("LINKER_PLANNER_FIXTURE_GUEST"); '
        "$expiry = time() - 60; $session = new WC_Session_Handler(); "
        '$hash = (new ReflectionMethod($session, "hash"))->invoke($session, $id . "|" . $expiry); '
        'echo $id . "|" . $expiry . "|" . ($expiry - 60) . "|" . $hash;',
        env={"LINKER_PLANNER_FIXTURE_GUEST": guest},
    )
    cookie.value = urllib.parse.quote(expired)
    assert browser.read(project).status == 401
    cookie.value = original
    wp.run(
        "eval",
        '(new WC_Session_Handler())->delete_session(getenv("LINKER_PLANNER_FIXTURE_GUEST"));',
        env={"LINKER_PLANNER_FIXTURE_GUEST": guest},
    )
    assert browser.read(project).status == 401
    old_scope = browser.context["query_scope"]
    assert browser.bootstrap()["query_scope"] != old_scope
    assert browser.read(project).status == 404


def test_cart_token_clone_never_inherits_project_ownership(
    local: tuple[Instance, WpCli],
) -> None:
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
    local: tuple[Instance, WpCli], claim_runtime: None, account: Account
) -> None:
    instance, wp = local
    user, login, password = account.user, account.login, account.password
    token = os.environ["LINKER_NATIVE_CLAIM_TOKEN"]
    owner = Browser(instance.url, token)
    owner.bootstrap()
    account.guest_sessions.add(
        urllib.parse.unquote(str(owner.native_cookie().value)).split("|")[0]
    )
    project = owner.create("Native login recovery evidence")
    previous = Browser(instance.url, token)
    for cookie in owner.cookies:
        previous.cookies.set_cookie(copy.copy(cookie))
    previous.context = dict(owner.context)
    env = {"LINKER_PLANNER_FIXTURE_USER": str(user), "LINKER_NATIVE_CLAIM_TOKEN": token}
    url = wp.run("option", "get", "linker_planner_url")
    try:
        wp.run("option", "update", "linker_planner_url", "http://127.0.0.1:1/planning")
        owner.login(login, password)
        event = json.loads(
            wp.run(
                "eval",
                '$posts=get_posts(array("post_type"=>"linker_planner_claim","post_status"=>"private","author"=>(int)getenv("LINKER_PLANNER_FIXTURE_USER"),"numberposts"=>-1)); '
                'if(count($posts)!==1){throw new Exception("expected one fixture event");} '
                '$post=$posts[0]; echo wp_json_encode(array("id"=>$post->ID,"payload"=>$post->post_content));',
                env=env,
            )
        )
        account.claim_events.add(event["id"])
        env["LINKER_PLANNER_FIXTURE_EVENT"] = str(event["id"])
        # First foreground recovery uses the unavailable route and establishes
        # the real native backoff; subsequent bootstrap must respect it.
        assert owner.rpc("bootstrap", {"schema_version": 1}).status == 503
        action = json.loads(
            wp.run(
                "eval",
                '$id=(int)getenv("LINKER_PLANNER_FIXTURE_EVENT"); '
                '$due=as_get_scheduled_actions(array("hook"=>"linker_tools_planner_claim","group"=>"linker-planner","search"=>"[".$id.",","status"=>"pending","date"=>time(),"date_compare"=>"<=","per_page"=>-1),"ids"); '
                'if(count($due)>1){fwrite(STDERR,"duplicate initial fixture action");exit(1);} '
                'if($due){ActionScheduler::runner()->process_action($due[0],"native-claim-fixture");} '
                '$retry=as_get_scheduled_actions(array("hook"=>"linker_tools_planner_claim","group"=>"linker-planner","search"=>"[".$id.",","status"=>"pending","date"=>time(),"date_compare"=>">","per_page"=>-1),"ids"); '
                'if(count($retry)!==1){fwrite(STDERR,"expected future fixture retry");exit(1);} '
                'echo wp_json_encode(array("id"=>$retry[0],"args"=>ActionScheduler::store()->fetch_action($retry[0])->get_args(),"initial_action_processed"=>(bool)$due));',
                env=env,
            )
        )
        trace = Path(os.environ["LINKER_NATIVE_CLAIM_TRACE"])
        attempts = trace.read_text().splitlines()
        assert len(attempts) == 1 + int(action["initial_action_processed"])
        assert owner.rpc("bootstrap", {"schema_version": 1}).status == 503
        assert trace.read_text().splitlines() == attempts
    finally:
        wp.run("option", "update", "linker_planner_url", url)
    assert owner.bootstrap()["kind"] == "user"
    assert owner.context["claim_pending"] is True
    assert trace.read_text().splitlines() == attempts
    assert owner.read(project).status == 404
    env["LINKER_PLANNER_FIXTURE_ACTION"] = str(action["id"])
    actual = json.loads(
        wp.run(
            "eval",
            '$event=(int)getenv("LINKER_PLANNER_FIXTURE_EVENT"); $old=(int)getenv("LINKER_PLANNER_FIXTURE_ACTION"); '
            "$payload=get_post($event)->post_content; $args=ActionScheduler::store()->fetch_action($old)->get_args(); "
            "ActionScheduler::store()->cancel_action($old); "
            '$due=as_schedule_single_action(time()-1,"linker_tools_planner_claim",$args,"linker-planner",true); '
            'ActionScheduler::runner()->process_action($due,"native-claim-fixture"); '
            'echo wp_json_encode(array("payload"=>$payload,"args"=>$args,"status"=>ActionScheduler::store()->get_status($due),"event_deleted"=>null===get_post($event)));',
            env=env,
        )
    )
    # Deterministic due scheduling, not a claim of naturally waiting 60 seconds.
    assert actual == {
        "payload": event["payload"],
        "args": action["args"],
        "status": "complete",
        "event_deleted": True,
    }
    assert len(trace.read_text().splitlines()) == len(attempts) + 1
    assert owner.bootstrap()["claim_pending"] is False
    assert owner.read(project).object() == project
    assert previous.read(project).status in (401, 404)
    old_scope = previous.context["query_scope"]
    assert previous.bootstrap()["query_scope"] != old_scope
    account.guest_sessions.add(
        urllib.parse.unquote(str(previous.native_cookie().value)).split("|")[0]
    )
    assert previous.read(project).status == 404
    nonce = owner.rest_nonce
    owner.rest_nonce = ""
    assert owner.rpc("bootstrap", {"schema_version": 1}).status == 403
    owner.rest_nonce = nonce
    owner.logout()
    assert owner.bootstrap()["kind"] == "guest"
    account.guest_sessions.add(
        urllib.parse.unquote(str(owner.native_cookie().value)).split("|")[0]
    )
    assert owner.read(project).status == 404


def test_native_recovery_grants_and_original_create_receipt_cross_login(
    local: tuple[Instance, WpCli], account: Account, second_account: Account
) -> None:
    instance, _ = local
    owner = Browser(instance.url)
    guest = owner.bootstrap()
    assert (
        owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()[
            "scopes"
        ]
        == []
    )
    command = {
        "schema_version": 1,
        "title": "Synthetic lost acknowledgement",
        "inputs": {},
        "key": str(uuid.uuid4()),
    }
    original = owner.rpc("rpc/projects/create", command).object()
    owner.login(account.login, account.password)
    signed_in = owner.bootstrap()
    page = owner.rpc("rpc/recovery/scopes", {"after": None, "schema_version": 1})
    assert page.status == 200
    assert set(page.object()["scopes"]) == {
        guest["query_scope"],
        signed_in["query_scope"],
    }
    assert owner.rpc("rpc/projects/create", command).object() == original
    assert (
        owner.rpc(
            "rpc/projects/list", {"schema_version": 1, "page_size": 20, "after": None}
        ).object()["items"][0]["id"]
        == original["id"]
    )
    assert (
        owner.rpc(
            "rpc/recovery/scopes", {"schema_version": 1, "after": "invalid"}
        ).status
        == 422
    )
    assert (
        owner.rpc(
            "rpc/recovery/scopes",
            {"schema_version": 1, "after": None, "user": account.user},
        ).status
        == 422
    )
    owner.logout()
    owner.bootstrap()
    assert (
        owner.rpc("rpc/recovery/scopes", {"schema_version": 1, "after": None}).object()[
            "scopes"
        ]
        == []
    )
    assert owner.read(original).status == 404
    owner.login(second_account.login, second_account.password)
    second = owner.bootstrap()
    scopes = owner.rpc(
        "rpc/recovery/scopes", {"schema_version": 1, "after": None}
    ).object()["scopes"]
    assert signed_in["query_scope"] not in scopes and guest["query_scope"] not in scopes
    assert second["query_scope"] in scopes and owner.read(original).status == 404
    owner.logout()
    owner.login(account.login, account.password)
    renewed = owner.bootstrap()
    scopes = owner.rpc(
        "rpc/recovery/scopes", {"schema_version": 1, "after": None}
    ).object()["scopes"]
    assert {
        guest["query_scope"],
        signed_in["query_scope"],
        renewed["query_scope"],
    } <= set(scopes)
    assert second["query_scope"] not in scopes
    assert owner.rpc("rpc/projects/create", command).object() == original


def test_native_recovery_grants_paginate_without_omission_or_other_account_data(
    local: tuple[Instance, WpCli], account: Account
) -> None:
    instance, wp = local
    synthetic = sorted(uuid.uuid4().hex + uuid.uuid4().hex for _ in range(67))
    result = wp.run(
        "eval",
        '$registry = new \\Linker\\Tools\\Planner\\RecoveryScopes(); foreach (json_decode(getenv("LINKER_PLANNER_FIXTURE_SCOPES"), true) as $scope) { if (!$registry->remember((int) getenv("LINKER_PLANNER_FIXTURE_USER"), $scope)) { throw new Exception("scope fixture failed"); } } echo "ok";',
        env={
            "LINKER_PLANNER_FIXTURE_USER": str(account.user),
            "LINKER_PLANNER_FIXTURE_SCOPES": json.dumps(synthetic),
        },
    )
    assert result == "ok"
    owner = Browser(instance.url)
    owner.login(account.login, account.password)
    owner.bootstrap()
    scopes: list[str] = []
    after = None
    while True:
        page = owner.rpc(
            "rpc/recovery/scopes", {"schema_version": 1, "after": after}
        ).object()
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
    source = """<?php
if (PHP_SAPI !== 'cli-server' || !hash_equals('TOKEN', $_SERVER['HTTP_X_LINKER_PLANNER_FIXTURE'] ?? '')) { return; }
add_filter('pre_http_request', static function ($pre, $args, $url) {
    if (str_ends_with($url, '/projects/create') && !str_contains($url, '/operations/replay/')) { return new WP_Error('synthetic_dispatch_timeout', 'Synthetic local dispatch refusal'); }
    return $pre;
}, 10, 3);
"""
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
    command = {
        "schema_version": 1,
        "title": "Synthetic admitted but uncommitted request",
        "inputs": {},
        "key": str(uuid.uuid4()),
    }
    with failed_native_dispatch(instance) as token:
        reply = browser.rpc(
            "rpc/projects/create", command, **{"X-Linker-Planner-Fixture": token}
        )
        assert reply.status == 503
    assert (
        browser.rpc(
            "rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}
        ).object()["items"]
        == []
    )
    browser.login(account.login, account.password)
    browser.bootstrap()
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    assert (
        len(
            browser.rpc(
                "rpc/projects/list",
                {"schema_version": 1, "page_size": 10, "after": None},
            ).object()["items"]
        )
        == 1
    )


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
    source = """<?php
if (PHP_SAPI !== 'cli-server' || !hash_equals('TOKEN', $_SERVER['HTTP_X_LINKER_PLANNER_FIXTURE'] ?? '')) { return; }
add_filter('wp_insert_post_empty_content', static function ($empty, $post) {
    return ($post['post_type'] ?? '') === 'linker_planner_claim' ? true : $empty;
}, 10, 2);
"""
    path.write_text(source.replace("TOKEN", token))
    path.chmod(0o600)
    try:
        yield token
    finally:
        path.unlink()


def test_native_insert_failure_tickets_stay_bound_across_shared_browser_accounts(
    local: tuple[Instance, WpCli],
    account: Account,
    second_account: Account,
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
        assert any(
            c.name.startswith("linker_planner_transition_") for c in browser.cookies
        )
        browser.logout()
        browser.bootstrap()
        second_project = browser.create("Account B insert recovery evidence")
        browser.login(second_account.login, second_account.password)
        assert browser.bootstrap()["claim_pending"] is True
        tickets = [
            c
            for c in browser.cookies
            if c.name.startswith("linker_planner_transition_")
        ]
        assert len(tickets) == 2
        assert all(c.has_nonstandard_attr("HttpOnly") for c in tickets)
    browser.client.addheaders = []
    assert browser.bootstrap()["claim_pending"] is False
    assert browser.read(second_project).status == 200
    assert browser.read(first_project).status == 404
    assert not any(
        c.name.startswith("linker_planner_transition_") for c in browser.cookies
    )
    # Execute the actual native background dispatcher for account A's event.
    wp.run(
        "action-scheduler",
        "run",
        "--group=linker-planner",
        "--batch-size=25",
        "--force",
    )
    first = Browser(instance.url)
    first.login(account.login, account.password)
    assert first.bootstrap()["kind"] == "user"
    assert first.read(first_project).status == 200
    assert first.read(second_project).status == 404


def test_actual_native_dispatch_refuses_before_its_json_parser(
    local: tuple[Instance, WpCli],
) -> None:
    _, wp = local
    result = wp.run(
        "eval",
        """
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
""",
    )
    cases = json.loads(result)
    assert cases[:3] == [
        {"status": 413, "largest_parser_input": 0},
        {"status": 400, "largest_parser_input": 0},
        {"status": 400, "largest_parser_input": 0},
    ]
    # Literal quote/bracket/backslash data is not container nesting. Native
    # parsing executes, then the bootstrap schema rejects the wrong value.
    assert cases[3]["status"] == 400 and cases[3]["largest_parser_input"] > 1000


def test_native_parser_limits_cover_unsupported_methods_and_reused_requests(
    local: tuple[Instance, WpCli],
) -> None:
    _, wp = local
    result = wp.run(
        "eval",
        """
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
""",
    )
    cases = json.loads(result)
    assert cases[:12] == [
        {"status": status, "largest_parser_input": 0}
        for _ in range(6)
        for status in (400, 413)
    ]
    assert cases[12] == {"status": 200}
    assert cases[13] == {"status": 400, "largest_parser_input": 40}


def test_native_journal_namespaces_owners_and_exact_engine_keys(
    local: tuple[Instance, WpCli],
) -> None:
    instance, wp = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    key = str(uuid.uuid4())
    while key.upper() == key:
        key = str(uuid.uuid4())
    command = {
        "schema_version": 1,
        "title": "Synthetic key namespace",
        "inputs": {},
        "key": key,
    }
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
    return set(
        json.loads(
            wp.run(
                "eval",
                'echo wp_json_encode(array_keys(json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true)["receipts"] ?? array()));',
            )
        )
    )


@pytest.mark.parametrize("committed", [False, True])
def test_legacy_native_receipt_retries_and_settles_without_new_quota(
    local: tuple[Instance, WpCli],
    committed: bool,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {
        "schema_version": 1,
        "title": "Synthetic legacy receipt",
        "inputs": {},
        "key": str(uuid.uuid4()),
    }
    preceding = native_operation_ids(wp)
    if committed:
        original = browser.rpc("rpc/projects/create", command)
        assert original.status == 200, original.body
    else:
        with failed_native_dispatch(instance) as token:
            assert (
                browser.rpc(
                    "rpc/projects/create",
                    command,
                    **{"X-Linker-Planner-Fixture": token},
                ).status
                == 503
            )
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Reproduce the previous raw-UUID journal representation for this one
    # synthetic operation. Its native fingerprint, binding and debits survive.
    operation_key = command["key"]
    assert isinstance(operation_key, str)
    before = json.loads(
        wp.run(
            "eval",
            """
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
""",
            env={
                "LINKER_PLANNER_FIXTURE_OPERATION": native_id,
                "LINKER_PLANNER_FIXTURE_KEY": operation_key,
            },
        )
    )
    if not committed:
        assert (
            browser.rpc(
                "rpc/projects/create", {**command, "title": "Changed legacy intent"}
            ).status
            == 409
        )
    reply = browser.rpc("rpc/projects/create", command)
    assert reply.status == 200, reply.body
    if committed:
        assert reply.object() == original.object()
    after = json.loads(
        wp.run(
            "eval",
            """
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_KEY');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
""",
            env={"LINKER_PLANNER_FIXTURE_KEY": operation_key},
        )
    )
    assert before["count"] == after["count"]
    assert before["buckets"] == after["buckets"]
    assert after["receipt"]["status"] == "completed"
    assert before["receipt"]["fingerprint"] == after["receipt"]["fingerprint"]
    assert before["receipt"]["debits"] == after["receipt"]["debits"]
    assert native_id not in native_operation_ids(wp)


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("terminal", ["expired", "cancelled"])
def test_unused_native_attempts_can_continue_the_same_business_intent(
    local: tuple[Instance, WpCli],
    legacy: bool,
    terminal: str,
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    command = {
        "schema_version": 1,
        "title": "Synthetic unused reservation",
        "inputs": {},
        "key": str(uuid.uuid4()),
    }
    preceding = native_operation_ids(wp)
    with failed_native_dispatch(instance) as token:
        assert (
            browser.rpc(
                "rpc/projects/create", command, **{"X-Linker-Planner-Fixture": token}
            ).status
            == 503
        )
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Model the pre-dispatch crash in this one synthetic operation's journal.
    # Native Ledger.cancel/recover perform the refund, not this fixture.
    operation_key = command["key"]
    assert isinstance(operation_key, str)
    old_id = operation_key if legacy else native_id
    before = json.loads(
        wp.run(
            "eval",
            """
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
""",
            env={
                "LINKER_PLANNER_FIXTURE_OPERATION": native_id,
                "LINKER_PLANNER_FIXTURE_OLD_ID": old_id,
                "LINKER_PLANNER_FIXTURE_TERMINAL": terminal,
            },
        )
    )
    assert (
        browser.rpc(
            "rpc/projects/create", {**command, "title": "Changed unused intent"}
        ).status
        == 409
    )
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    after = json.loads(
        wp.run(
            "eval",
            """
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OLD_ID');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
""",
            env={"LINKER_PLANNER_FIXTURE_OLD_ID": old_id},
        )
    )
    assert after["receipt"]["status"] == terminal
    assert before["buckets"] == after["buckets"], (
        "refund plus replacement consumes one attempt, not two"
    )
    assert before["count"] + 1 == after["count"]
    before_receipt = {**before["receipt"], "status": terminal}
    assert before_receipt == after["receipt"], (
        "the original terminal receipt is never rewritten"
    )
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    assert len(native_operation_ids(wp)) == after["count"]
    projects = browser.rpc(
        "rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}
    ).object()
    assert len(projects["items"]) == 1


def test_permanent_engine_replay_uses_no_new_quota_after_native_receipt_forgetting(
    local: tuple[Instance, WpCli],
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    key = str(uuid.uuid4())
    command = {
        "schema_version": 1,
        "title": "Permanent replay evidence",
        "inputs": {"object": {}, "array": [], "one": 1.0},
        "key": key,
    }
    preceding = native_operation_ids(wp)
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    # Mimic the native journal's receipt-forgetting boundary for this fixture
    # UUID only; do not advance global time or delete other native receipts.
    before = wp.run(
        "eval",
        """
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
unset($state['receipts'][getenv('LINKER_PLANNER_FIXTURE_OPERATION')]);
update_option($name, wp_json_encode($state), false);
echo hash('sha256', wp_json_encode($state));
""",
        env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id},
    )
    assert browser.rpc("rpc/projects/create", command).object() == created.object()
    after = wp.run(
        "eval",
        'echo hash("sha256", get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION));',
    )
    assert before == after, "permanent replay must not reserve a new quota receipt"
    command["inputs"] = {"changed": True}
    assert browser.rpc("rpc/projects/create", command).status == 409


def test_profile_preview_and_csv_issue_cross_the_real_native_gateway(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    first, second = Browser(instance.url), Browser(instance.url)
    first.bootstrap()
    second.bootstrap()
    project = first.create("Synthetic native profile interpretation")
    mapping = {
        "timestamp_column": "time",
        "value_column": "power",
        "measurement": "gross_load",
        "value_kind": "interval_average_kw",
        "timestamp_role": "start",
        "timezone": "Europe/Oslo",
        "origin": "synthetic",
        "interval_seconds": 900,
        "delimiter": ";",
        "decimal": ",",
        "end_timestamp_column": None,
        "fold_column": None,
        "end_fold_column": None,
        "offset_rule": "explicit_offset_precedes_naive_timezone",
        "within_interval_assumption": "constant_mean_no_new_observations",
    }
    raw = b"time;power\n2024-01-01T00:00Z;4\n2024-01-01T00:30Z;8\n"
    command = {
        "schema_version": 1,
        "project_id": project["id"],
        "content_base64": base64.b64encode(raw).decode(),
        "mapping": mapping,
        "source_label": "Synthetic native fixture",
        "rights_note": "Generated in this local fixture",
        "key": str(uuid.uuid4()),
    }
    imported = first.rpc("rpc/profiles/csv", command)
    assert imported.status == 200, imported.body
    asset = imported.object()
    request = {
        "schema_version": 1,
        "project_id": project["id"],
        "asset_id": asset["id"],
        "offset": 0,
        "page_size": 1,
    }
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
    failed = first.rpc(
        "rpc/profiles/csv",
        {
            **command,
            "key": str(uuid.uuid4()),
            "content_base64": base64.b64encode(
                b"time;power\nPRIVATE-CELL;4\n"
            ).decode(),
        },
    )
    assert failed.status == 422
    assert failed.object() == {
        "error": {
            "code": "invalid_input",
            "profile_issue": {
                "issue": "timestamp_format",
                "line": 2,
                "field": "timestamp",
            },
        }
    }
    assert b"PRIVATE-CELL" not in failed.body


def test_equivalent_wire_replay_settles_the_same_canonical_native_receipt(
    local: tuple[Instance, WpCli],
) -> None:
    instance, wp = local
    browser = Browser(instance.url)
    browser.bootstrap()
    key = str(uuid.uuid4())
    command = {
        "schema_version": 1,
        "title": "Canonical native receipt",
        "inputs": {"object": {}, "array": [], "one": 1.0},
        "key": key,
    }
    preceding = native_operation_ids(wp)
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200, created.body
    inserted = native_operation_ids(wp) - preceding
    assert len(inserted) == 1
    native_id = inserted.pop()
    before = json.loads(
        wp.run(
            "eval",
            """
$name = \\Linker\\Commerce\\Protection\\Ledger::OPTION;
$state = json_decode(get_option($name), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
$state['receipts'][$id]['status'] = 'unresolved';
update_option($name, wp_json_encode($state), false);
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
""",
            env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id},
        )
    )
    reply = browser.http(
        ROOT + "rpc/projects/create",
        body=json.dumps(command, indent=2, sort_keys=True).encode(),
        headers={
            "Content-Type": "application/json",
            "Origin": instance.url,
            "X-Linker-Planner-Nonce": browser.context["nonce"],
        },
    )
    assert reply.status == 200 and reply.object() == created.object()
    after = json.loads(
        wp.run(
            "eval",
            """
$state = json_decode(get_option(\\Linker\\Commerce\\Protection\\Ledger::OPTION), true);
$id = getenv('LINKER_PLANNER_FIXTURE_OPERATION');
echo wp_json_encode(array('receipt' => $state['receipts'][$id], 'count' => count($state['receipts']), 'buckets' => $state['buckets']));
""",
            env={"LINKER_PLANNER_FIXTURE_OPERATION": native_id},
        )
    )
    assert after["receipt"]["status"] == "completed"
    assert before["count"] == after["count"] and before["buckets"] == after["buckets"]
    assert before["receipt"]["fingerprint"] == after["receipt"]["fingerprint"]
    assert before["receipt"]["debits"] == after["receipt"]["debits"]


def test_one_public_operation_key_cannot_meter_two_project_resources(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    first = browser.create("Receipt resource A")
    second = browser.create("Receipt resource B")
    csv = base64.b64encode(
        b"time,power\n2026-01-01T00:00:00Z,1\n2026-01-01T01:00:00Z,2\n"
    ).decode()
    commands: list[tuple[str, dict[str, Any]]] = [
        ("projects/revise", {"expected_revision": 1, "inputs": {"same": True}}),
        (
            "battery/scenario",
            {
                "parameters": {
                    "schema_version": 1,
                    "model": "constant_window_single_ac_bus_v1",
                    "parameter_basis": "explicit_scenario",
                    "usable_window_kwh": 10.0,
                    "charge_ac_kw": 5.0,
                    "discharge_ac_kw": 5.0,
                    "eta_charge": 0.95,
                    "eta_discharge": 0.95,
                    "internal_aux_kw": 0.0,
                    "standing_loss_rate_per_hour": 0.0,
                },
                "source_note": "Synthetic native integration scenario",
            },
        ),
        (
            "profiles/csv",
            {
                "content_base64": csv,
                "source_label": "Synthetic native integration profile",
                "rights_note": "Locally generated fixture",
                "mapping": {
                    "timestamp_column": "time",
                    "value_column": "power",
                    "measurement": "gross_load",
                    "value_kind": "interval_average_kw",
                    "timestamp_role": "start",
                    "timezone": "UTC",
                    "origin": "synthetic",
                    "interval_seconds": 3600.0,
                    "delimiter": ",",
                    "decimal": ".",
                    "end_timestamp_column": None,
                    "fold_column": None,
                    "end_fold_column": None,
                    "offset_rule": "explicit_offset_precedes_naive_timezone",
                    "within_interval_assumption": "constant_mean_no_new_observations",
                },
            },
        ),
    ]
    for path, fields in commands:
        command = {
            "schema_version": 1,
            **fields,
            "project_id": first["id"],
            "key": str(uuid.uuid4()),
        }
        accepted = browser.rpc("rpc/" + path, command)
        assert accepted.status == 200, accepted.body
        changed_resource = {**command, "project_id": second["id"]}
        rejected = browser.rpc("rpc/" + path, changed_resource)
        assert rejected.status == 409, rejected.body
        assert browser.rpc("rpc/" + path, command).object() == accepted.object()
    assert browser.read(second).object()["revision"] == 1


def test_unrepresentable_numbers_are_rejected_without_changing_project_data(
    local: tuple[Instance, WpCli],
) -> None:
    instance, _ = local
    browser = Browser(instance.url)
    browser.bootstrap()
    for number in (2**53, 9223372036854775809, 10**400, 1e100):
        reply = browser.rpc(
            "rpc/projects/create",
            {
                "schema_version": 1,
                "title": "Unsupported numeric fixture",
                "inputs": {"nested": [{"number": number}]},
                "key": str(uuid.uuid4()),
            },
        )
        assert reply.status == 400, reply.body
    projects = browser.rpc(
        "rpc/projects/list", {"schema_version": 1, "page_size": 10, "after": None}
    )
    assert projects.object()["items"] == []
    command = {
        "schema_version": 1,
        "title": "Representable numeric fixture",
        "inputs": {"number": 2**53 - 1, "fraction": 0.125},
        "key": str(uuid.uuid4()),
    }
    created = browser.rpc("rpc/projects/create", command)
    assert created.status == 200 and created.object()["inputs"] == command["inputs"]
    assert browser.read(created.object()).object() == created.object()
    assert browser.rpc("rpc/projects/create", command).object() == created.object()


def test_series_csv_download_uses_frontend_wordpress_file_api(
    local: tuple[Instance, WpCli],
) -> None:
    """A frontend REST request does not inherit WP-CLI's loaded admin helpers."""
    instance, wp = local
    owner = Browser(instance.url)
    probe_created = False
    try:
        owner.bootstrap()
        marker = uuid.uuid4().hex
        probe = instance.wp_content / "mu-plugins/linker-series-file-api-acceptance.php"
        assert not probe.exists()
        payload = b"timestamp,power\n2023-01-01,1\n"
        sha = hashlib.sha256(payload).hexdigest()
        source = r"""<?php
    if (PHP_SAPI !== 'cli-server' || !hash_equals('MARKER', $_SERVER['HTTP_X_LINKER_SERIES_FIXTURE'] ?? '')) { return; }
    add_filter('pre_http_request', static function ($pre, $args, $url) {
        $body = json_decode($args['body'] ?? '', true);
        if (($body['project_id'] ?? null) !== 'fixture-project' || ($body['asset_id'] ?? null) !== 'fixture-asset') { return $pre; }
        if (str_ends_with($url, '/assets/read')) {
            $asset = array('id' => 'fixture-asset', 'project_id' => 'fixture-project', 'purpose' => 'planning_pv_series_csv_v1', 'media_type' => 'text/csv', 'content_sha256' => 'SHA');
            return array('response' => array('code' => 200), 'headers' => array('content-type' => 'application/json'), 'body' => wp_json_encode($asset));
        }
        if (str_ends_with($url, '/assets/content') && true === ($args['stream'] ?? false) && is_string($args['filename'] ?? null)) {
            file_put_contents($args['filename'], base64_decode('PAYLOAD', true));
            return array('response' => array('code' => 200), 'headers' => array('content-type' => 'application/octet-stream'), 'body' => '');
        }
        return $pre;
    }, 10, 3);
    """
        with probe.open("x") as stream:
            probe_created = True
            stream.write(
                source.replace("MARKER", marker)
                .replace("SHA", sha)
                .replace("PAYLOAD", base64.b64encode(payload).decode())
            )
        probe.chmod(0o600)
        reply = owner.rpc(
            "rpc/assets/content",
            {
                "schema_version": 1,
                "project_id": "fixture-project",
                "asset_id": "fixture-asset",
                "series_csv": True,
            },
            **{"X-Linker-Series-Fixture": marker},
        )
        assert reply.status == 200
        assert reply.body == payload
    finally:
        try:
            if probe_created:
                probe.unlink()
        finally:
            for cookie in owner.cookies:
                if not cookie.name.startswith("wp_woocommerce_session_"):
                    continue
                assert isinstance(cookie.value, str)
                guest = urllib.parse.unquote(cookie.value).split("|")[0]
                assert re.fullmatch(r"t_[a-f0-9]{30}", guest)
                wp.run(
                    "eval",
                    '$id = getenv("LINKER_PLANNER_FIXTURE_GUEST"); '
                    "(new WC_Session_Handler())->delete_session($id); "
                    'global $wpdb; $table=$wpdb->prefix . "woocommerce_sessions"; '
                    "if (null !== $wpdb->get_var($wpdb->prepare("
                    '"SELECT session_key FROM %i WHERE session_key=%s", $table, $id))) '
                    '{throw new Exception("fixture guest cleanup failed");}',
                    env={"LINKER_PLANNER_FIXTURE_GUEST": guest},
                )
