"""The local stack end to end: real MySQL, Redis, PHP 8.3, WP-CLI and two WordPress instances.

The tests drive `linker-local` as `just` does, with a data root of their own
and two instance names of their own run (pytesta_<run>, pytestb_<run>). They
need this Mac's tools
(docs/local-stack.md): CI, which has none of them, skips the module; anywhere
else a missing tool fails it.
"""

from __future__ import annotations

import email
import email.policy
import fcntl
import http.client
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import pytest

from linker_local import objectcache, server
from linker_local.cli import require_php
from linker_local.instance import DATABASE_PREFIX, SHARED, Instance, database_of
from linker_local.mysql import CREDENTIALS, MySQL
from linker_local.processes import port_is_free
from linker_local.registry import Registry

# Every run names its own instances (process id and a random suffix), so its
# databases and Redis keys are its own: a test name can never be a real
# instance's or another run's (#252 review). The names pass check_name.
RUN = f"{os.getpid()}_{secrets.token_hex(3)}"
A = f"pytesta_{RUN}"
B = f"pytestb_{RUN}"
NAMES = (A, B)
# What every run's instance databases look like, aborted runs' included.
LEFTOVER_DATABASES = DATABASE_PREFIX + "pytest_\\_%"
CLI = Path(sys.executable).with_name("linker-local")


def missing_tools() -> list[str]:
    """What this Mac lacks for the stack: linker-local's own checks, and MySQL."""
    missing = []
    try:
        require_php()  # PHP 8.3 in $PHP (`just test` sets it) and WP-CLI 2.12
    except RuntimeError as error:
        missing.append(str(error))
    try:
        MySQL(CREDENTIALS).query("SELECT 1")
    except (OSError, RuntimeError) as error:
        missing.append(f"a MySQL server that `mysql -u root` reaches ({error})")
    try:
        objectcache.require_redis()
    except RuntimeError as error:
        missing.append(str(error))
    return missing


@dataclass
class Response:
    status: int
    headers: http.client.HTTPMessage
    body: str


@dataclass
class Stack:
    home: Path
    env: dict[str, str]

    def cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(CLI), *args], capture_output=True, text=True, env=self.env, check=False
        )
        if check and result.returncode != 0:
            pytest.fail(
                f"linker-local {' '.join(args)} failed:\n{result.stdout}{result.stderr}"
            )
        return result

    def wp(self, name: str, *args: str) -> str:
        return self.cli("wp", name, *args).stdout.strip()

    def instance(self, name: str) -> Instance:
        instance = Registry(self.home).get(name)
        assert instance is not None
        return instance


def request(
    port: int,
    target: str,
    method: str = "GET",
    form: dict[str, str] | None = None,
    cookie: str = "",
) -> Response:
    """One HTTP request to 127.0.0.1, redirects not followed, no proxy."""
    # No answer can come later than the server's own max_execution_time.
    timeout = int(server.PRODUCTION_LIMITS["max_execution_time"])
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        headers = {"Cookie": cookie} if cookie else {}
        body = None
        if form is not None:
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        connection.request(method, target, body=body, headers=headers)
        response = connection.getresponse()
        return Response(response.status, response.headers, response.read().decode())
    finally:
        connection.close()


def path_of(url: str) -> str:
    parts = urlsplit(url)
    return parts.path + (f"?{parts.query}" if parts.query else "")


def drop_databases() -> None:
    for name in NAMES:
        MySQL(CREDENTIALS).drop_database(database_of(name))


def drop_leftover_databases() -> None:
    """The databases of runs that ended without their cleanup (a killed run).

    Called under one_run_per_machine(): no other run's instances exist then,
    so every database with a test instance's name is a leftover.
    """
    mysql = MySQL(CREDENTIALS)
    found = mysql.query(f"SHOW DATABASES LIKE '{LEFTOVER_DATABASES}'")
    for database in found.split():
        mysql.drop_database(database)


@contextmanager
def one_run_per_machine() -> Iterator[None]:
    """Hold a lock for the whole run: every checkout's `just test` uses the same
    MySQL server and the same ports, and a run allocates its instances' ports
    from the ones free at that moment, before its servers bind them — two runs
    at once could take the same ones. The lock ends with the process."""
    SHARED.mkdir(parents=True, exist_ok=True)
    with (SHARED / "stack-test.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


@pytest.fixture(scope="module")
def stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    missing = missing_tools()
    if missing:
        message = "the local stack needs " + "; ".join(missing)
        if os.environ.get("CI"):
            pytest.skip(message)
        pytest.fail(message)
    taken = [name for name in NAMES if Registry(SHARED).get(name) is not None]
    if taken:
        pytest.fail(
            f"real instances use the test names {taken}; their databases would go"
        )
    home = tmp_path_factory.mktemp("linker-local-home")
    built = Stack(home, {**os.environ, "LINKER_LOCAL_HOME": str(home)})
    with one_run_per_machine():
        drop_leftover_databases()
        try:
            for name in NAMES:
                built.cli("up", name)
            yield built
        finally:
            for name in NAMES:
                built.cli("down", name, check=False)
                if (instance := Registry(home).get(name)) is not None:
                    objectcache.forget(instance)  # their Redis keys
            drop_databases()
            # Two WordPress installs; pytest would otherwise keep them with its last runs.
            shutil.rmtree(home, ignore_errors=True)


def test_two_instances_run_side_by_side(stack: Stack) -> None:
    a, b = (stack.instance(name) for name in NAMES)

    assert {a.port, a.engine_port, a.genie_port}.isdisjoint(
        {b.port, b.engine_port, b.genie_port}
    )
    status = stack.cli("status").stdout
    for instance in (a, b):
        row = rf"^{instance.name}\s+{re.escape(instance.url)}\s+{instance.database}\s+running\s"
        assert re.search(row, status, re.MULTILINE), status
        assert request(instance.port, "/").status == 200
    stack.wp(a.name, "option", "update", "linker_probe", "a")
    assert (
        stack.cli("wp", b.name, "option", "get", "linker_probe", check=False).returncode
        == 1
    )


def test_both_run_the_production_versions(stack: Stack) -> None:
    for name in NAMES:
        assert stack.wp(name, "core", "version") == "7.1.3"
        assert (
            stack.wp(name, "plugin", "get", "woocommerce", "--field=version")
            == "11.2.0"
        )
        assert (
            stack.wp(name, "plugin", "get", "polylang", "--field=version") == "3.8.10"
        )
        statuses = stack.wp(
            name, "plugin", "list", "--status=active", "--field=name"
        ).split()
        assert {
            "woocommerce",
            "polylang",
            "linker-commerce",
            "linker-i18n",
            "linker-tools",
        } <= set(statuses)


def test_each_instance_has_its_own_redis_object_cache(stack: Stack) -> None:
    a, b = (stack.instance(name) for name in NAMES)

    for instance in (a, b):
        assert "Status: Connected" in stack.wp(instance.name, "redis", "status")
        persistent = "var_export( wp_using_ext_object_cache() );"
        assert stack.wp(instance.name, "eval", persistent) == "true"
    # A value outlives the WP-CLI process that set it, and stays in its instance.
    stack.wp(a.name, "cache", "set", "linker_probe", "from a")
    assert stack.wp(a.name, "cache", "get", "linker_probe") == "from a"
    assert (
        stack.cli("wp", b.name, "cache", "get", "linker_probe", check=False).returncode
        == 1
    )


def test_pretty_permalinks_and_files_are_served(stack: Stack) -> None:
    a = stack.instance(A)
    shop = path_of(stack.wp(a.name, "eval", "echo wc_get_page_permalink( 'shop' );"))
    for target in ("/", shop, "/sample-page/", "/wp-json/", "/wp-login.php"):
        assert request(a.port, target).status == 200, target
    # Our plugins are links into the checkout; their files are served through them.
    assert (
        request(a.port, "/wp-content/plugins/linker-tools/build/genie.js").status == 200
    )
    # WordPress knows the server rewrites URLs, as production's does; otherwise
    # Settings > Permalinks would put /index.php/ in front of every structure.
    assert stack.wp(a.name, "eval", "var_export( got_url_rewrite() );") == "true"
    # A directory is addressed with a trailing slash.
    admin = request(a.port, "/wp-admin")
    assert (admin.status, admin.headers["Location"]) == (301, "/wp-admin/")
    # The login gate keeps an empty checkout on its page in every language
    # (#54): WooCommerce's redirect to the cart is gated off for the checkout
    # page and its translations.
    checkout = request(
        a.port, path_of(stack.wp(a.name, "eval", "echo wc_get_checkout_url();"))
    )
    assert checkout.status == 200


def test_the_checkout_endpoints_stay_where_the_checkout_page_is(
    stack: Stack,
) -> None:
    """A site that never renamed its checkout page keeps its endpoints.

    This instance's checkout page answers /checkout/ (it was never renamed),
    and WooCommerce's endpoints live under it. The rule that sends the retired
    /checkout/ slug to the renamed page's address must leave them alone: a
    redirect there would 404 the shop's order links on such a site (#80).
    """
    a = stack.instance(A)
    assert (
        path_of(stack.wp(a.name, "eval", "echo wc_get_checkout_url();")) == "/checkout/"
    )
    endpoint = "/checkout/order-received/4711/"
    response = request(a.port, endpoint)
    assert response.headers.get("Location", "") == "", (
        f"{endpoint} redirects to {response.headers.get('Location')}"
    )


def test_a_form_mails_into_the_instance_instead_of_sending(
    stack: Stack,
) -> None:
    a = stack.instance(A)
    before = set(a.mail_dir.glob("*.eml"))

    sent = request(
        a.port,
        "/wp-login.php?action=lostpassword",
        method="POST",
        form={
            "user_login": "local-admin",
            "redirect_to": "",
            "wp-submit": "Get New Password",
        },
    )

    assert sent.status == 302
    assert "checkemail=confirm" in sent.headers["Location"]
    new = set(a.mail_dir.glob("*.eml")) - before
    assert len(new) == 1
    # Parsed, not matched as text: a header longer than 78 characters is
    # folded onto a second line (RFC 5322 §2.2.3), as the run's longer
    # instance name makes this Subject.
    message = email.message_from_string(
        new.pop().read_text(), policy=email.policy.default
    )
    assert message["To"] == "local-admin@example.test"
    assert message["Subject"] == f"[Linker (local {A})] Password Reset"
    # Mail that skips wp_mail() fails instead of reaching this Mac's sendmail.
    direct = "var_export( mail( 'sales@example.test', 'Direct', 'Body' ) );"
    assert stack.wp(a.name, "eval", direct) == "false"


def test_mail_that_cannot_be_written_is_reported_as_failed(stack: Stack) -> None:
    a = stack.instance(A)
    # The isolation layer's own failure reporting; the mail queue of
    # plugins/linker-commerce (#11) deliberately answers wp_mail() true for a
    # send it has queued for retry, so it steps aside for this check.
    stack.wp(a.name, "plugin", "deactivate", "linker-commerce")
    a.mail_dir.chmod(0o500)
    try:
        sent = stack.wp(
            a.name, "eval", "var_export( wp_mail( 'sales@example.test', 'S', 'B' ) );"
        )
    finally:
        a.mail_dir.chmod(0o755)
        stack.wp(a.name, "plugin", "activate", "linker-commerce")

    assert sent == "false"


def test_a_captured_message_keeps_its_bcc(stack: Stack) -> None:
    a = stack.instance(A)
    before = set(a.mail_dir.glob("*.eml"))

    sent = stack.wp(
        a.name,
        "eval",
        "var_export( wp_mail( 'sales@example.test', 'Inquiry', 'Body',"
        " array( 'Bcc: archive@example.test' ) ) );",
    )

    assert sent == "true"
    (captured,) = set(a.mail_dir.glob("*.eml")) - before
    assert "Bcc: archive@example.test" in captured.read_text()


def test_wordpress_requests_reach_this_machine_only(stack: Stack) -> None:
    b = stack.instance(B)

    outcome = stack.wp(
        b.name,
        "eval",
        "$r = wp_remote_get( 'https://de-linker.com/' );"
        " echo is_wp_error( $r ) ? $r->get_error_code() : 'sent';"
        " echo ' ', wp_remote_retrieve_response_code( wp_remote_get( home_url( '/' ) ) );",
    )

    assert outcome == "linker_local_blocked 200"
    log = b.isolation_log.read_text()
    assert "\tGET\thttps://de-linker.com/\n" in log


@contextmanager
def serving(respond: type[BaseHTTPRequestHandler]) -> Iterator[int]:
    """Run a handler on a free port of 127.0.0.1; yield the port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), respond)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_a_redirect_cannot_lead_wordpress_off_this_machine(stack: Stack) -> None:
    b = stack.instance(B)
    reached: list[str] = []

    class Elsewhere(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            reached.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    with serving(Elsewhere) as elsewhere:
        # localhost is this machine too, but not the one address the isolation allows.
        target = f"http://localhost:{elsewhere}/escaped"

        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                pass

        with serving(Redirect) as redirect:
            outcome = stack.wp(
                b.name,
                "eval",
                f"$r = wp_remote_get( 'http://127.0.0.1:{redirect}/' );"
                " echo is_wp_error( $r ) ? 'refused' : wp_remote_retrieve_response_code( $r );",
            )

    assert outcome == "refused"
    assert reached == []
    assert f"\tREDIRECT\t{target}\n" in b.isolation_log.read_text()


IMAGERY = json.loads(
    (
        Path(__file__).resolve().parents[3]
        / "services"
        / "engine"
        / "data"
        / "imagery.json"
    ).read_text()
)
# The WMS hosts the roof step loads, from the engine's own list of them: the
# mu-plugin's allowlist and this assertion read the same source of truth.
IMAGERY_WMS = " ".join(
    sorted(
        {
            f"https://{urlsplit(state['wms']).hostname}"
            for state in IMAGERY["states"].values()
        }
    )
)
LOCAL_SOURCES = "'self' http://127.0.0.1:* data: blob: 'unsafe-inline' 'unsafe-eval'"


def test_pages_may_load_from_this_machine_only_and_are_not_indexed(
    stack: Stack,
) -> None:
    home = request(stack.instance(A).port, "/")

    # Outside the machine, a page reaches only what the site itself puts on it:
    # the theme's template scripts (CDNs the snapshot's pages enqueue) and the
    # states' official aerial-image WMS the roof step shows, by fetch and as
    # images (services/engine/data/imagery.json).
    assert home.headers["Content-Security-Policy"] == (
        f"default-src {LOCAL_SOURCES}; "
        f"script-src {LOCAL_SOURCES} https://cdn.jsdelivr.net https://esm.sh https://unpkg.com https://challenges.cloudflare.com; "
        f"img-src {LOCAL_SOURCES} {IMAGERY_WMS} https://secure.gravatar.com; "
        f"connect-src {LOCAL_SOURCES} {IMAGERY_WMS} https://challenges.cloudflare.com; "
        "frame-src 'self' http://127.0.0.1:* https://challenges.cloudflare.com; "
        "form-action 'self'"
    )
    assert home.headers["X-Robots-Tag"] == "noindex, nofollow"


def cookies_of(response: Response) -> str:
    """The WordPress cookies a response sets, as a Cookie header."""
    return "; ".join(
        value.split(";", 1)[0]
        for value in response.headers.get_all("Set-Cookie", [])
        if value.startswith("wordpress_")
    )


def test_a_login_link_signs_in_once(stack: Stack) -> None:
    a = stack.instance(A)
    link = path_of(stack.cli("login", a.name).stdout.strip())

    first = request(a.port, link)

    assert (first.status, first.headers["Location"]) == (302, f"{a.url}/wp-admin/")
    cookies = cookies_of(first)
    assert "wordpress_logged_in_" in cookies
    # Signed out, wp-admin sends a visitor to wp-login.php; signed in, the page
    # answers, or on a fresh install WooCommerce's one-time welcome redirect.
    signed_out = request(a.port, "/wp-admin/profile.php")
    assert "/wp-login.php" in signed_out.headers["Location"]
    signed_in = request(a.port, "/wp-admin/profile.php", cookie=cookies)
    assert "/wp-login.php" not in (signed_in.headers["Location"] or "")
    assert request(a.port, link).status == 403


def test_a_login_link_lives_ten_minutes(stack: Stack) -> None:
    lifetime = stack.wp(
        A,
        "eval",
        "add_action( 'setted_transient', function ( $name, $value, $expiration ) {"
        " if ( str_starts_with( $name, 'linker_local_login_' ) ) { echo $expiration; } }, 10, 3 );"
        " linker_local_login_url( 'local-admin' );",
    )

    assert lifetime == "600"


def test_the_server_runs_with_productions_php_limits(stack: Stack) -> None:
    a = stack.instance(A)
    cookies = cookies_of(
        request(a.port, path_of(stack.cli("login", a.name).stdout.strip()))
    )
    request(
        a.port, "/wp-admin/profile.php", cookie=cookies
    )  # past WooCommerce's welcome redirect

    upload = request(a.port, "/wp-admin/media-new.php", cookie=cookies)

    # WordPress reports the smaller of upload_max_filesize and post_max_size;
    # without the instance's php.ini it would be PHP's default, 2 MB.
    assert "Maximum upload file size: 2 GB." in upload.body


def test_serve_starts_the_services_and_down_stops_everything(stack: Stack) -> None:
    a = stack.instance(A)

    stack.cli("serve", a.name)

    for port, option in (
        (a.engine_port, "linker_engine_url"),
        (a.genie_port, "linker_genie_url"),
    ):
        health = request(port, "/health")
        assert (health.status, json.loads(health.body)) == (200, {"status": "ok"})
        assert stack.wp(a.name, "option", "get", option) == f"http://127.0.0.1:{port}"
    assert re.search(
        rf"^{A}\s.*\srunning\s+engine, genie\s", stack.cli("status").stdout, re.M
    )

    stack.cli("down", a.name)

    assert all(port_is_free(port) for port in (a.port, a.engine_port, a.genie_port))
    stack.cli("up", a.name)
    assert request(a.port, "/").status == 200


def test_a_snapshot_brings_its_plugins_themes_and_uploads(
    stack: Stack, tmp_path: Path
) -> None:
    b = stack.instance(B)
    taken = tmp_path / "20261010-0900"
    plugin = taken / "plugins" / "snapshot-fixture" / "snapshot-fixture.php"
    theme = taken / "themes" / "snapshot-theme"
    upload = taken / "uploads" / "2026" / "10" / "datasheet.txt"
    for path in (plugin.parent, theme, upload.parent):
        path.mkdir(parents=True)
    plugin.write_text("<?php\n/**\n * Plugin Name: Snapshot fixture\n */\n")
    (theme / "style.css").write_text("/*\nTheme Name: Snapshot theme\n*/\n")
    (theme / "index.php").write_text("<?php\n")
    upload.write_text("datasheet")

    stack.cli("up", b.name, "--snapshot", str(taken))

    assert (
        stack.wp(b.name, "plugin", "get", "snapshot-fixture", "--field=status")
        == "active"
    )
    themes = stack.wp(b.name, "theme", "list", "--field=name").split()
    assert "snapshot-theme" in themes
    assert (
        stack.wp(b.name, "theme", "list", "--status=active", "--field=name")
        != "snapshot-theme"
    )
    served = request(b.port, "/wp-content/uploads/2026/10/datasheet.txt")
    assert (served.status, served.body) == (200, "datasheet")


def test_a_snapshot_activates_only_the_plugins_the_site_ran_active(
    stack: Stack, tmp_path: Path
) -> None:
    b = stack.instance(B)
    taken = tmp_path / "20261010-0033"
    liveplugin = taken / "plugins" / "fixture-live" / "fixture-live.php"
    gone = taken / "plugins" / "fixture-retired" / "fixture-retired.php"
    for path in (liveplugin.parent, gone.parent):
        path.mkdir(parents=True)
    liveplugin.write_text("<?php\n/**\n * Plugin Name: Fixture live\n */\n")
    gone.write_text("<?php\n/**\n * Plugin Name: Fixture retired\n */\n")
    (taken / "site").mkdir()
    (taken / "site" / "plugins.json").write_text(
        '[{"name": "fixture-live", "status": "active", "file": "fixture-live/fixture-live.php"},'
        ' {"name": "fixture-retired", "status": "inactive", "file": "fixture-retired/fixture-retired.php"}]'
    )

    stack.cli("up", b.name, "--snapshot", str(taken))

    # The local instance runs the live site's parity set: files of both
    # plugins, active only what the live site ran active (W1, 2026-10-10).
    assert (
        stack.wp(b.name, "plugin", "get", "fixture-live", "--field=status") == "active"
    )
    assert (
        stack.wp(b.name, "plugin", "get", "fixture-retired", "--field=status")
        == "inactive"
    )


def test_a_wrong_snapshot_path_is_refused_before_anything_changes(
    stack: Stack, tmp_path: Path
) -> None:
    a = stack.instance(A)

    refused = stack.cli(
        "reset", a.name, "--snapshot", str(tmp_path / "missing"), check=False
    )

    assert refused.returncode == 1
    assert "has none of plugins/, themes/, uploads/" in refused.stderr
    assert request(a.port, "/").status == 200  # not reset: still built and running


def test_reset_rebuilds_one_instance_repeatedly_and_leaves_the_other_alone(
    stack: Stack,
) -> None:
    a, b = (stack.instance(name) for name in NAMES)
    stack.wp(b.name, "option", "update", "linker_probe", "b")
    stack.wp(b.name, "cache", "set", "linker_probe", "b")

    for _ in range(2):
        stack.wp(a.name, "option", "update", "linker_probe", "before reset")
        stack.wp(a.name, "cache", "set", "linker_probe", "before reset")
        stack.cli("reset", a.name)
        assert (
            stack.cli(
                "wp", a.name, "cache", "get", "linker_probe", check=False
            ).returncode
            == 1
        )
        assert (
            stack.cli(
                "wp", a.name, "option", "get", "linker_probe", check=False
            ).returncode
            == 1
        )
        assert stack.instance(a.name) == a
        assert request(a.port, "/").status == 200

    assert stack.wp(b.name, "option", "get", "linker_probe") == "b"
    # Building a never empties the shared Redis database: b's cached key survives.
    assert stack.wp(b.name, "cache", "get", "linker_probe") == "b"
    assert request(b.port, "/").status == 200
