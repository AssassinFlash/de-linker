"""The seam: one local instance, one host, and the commands each produces.

No WordPress is started. What these tests can find is exactly what a drill
would otherwise find late: a command built for the wrong machine, a path
escaping the WordPress root, a cache-buster that is not appended, and a probe
whose answer is not the answer the caller asked for.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from linker_cutover.target import (
    HOST,
    PLUGINS,
    CutoverError,
    Target,
    remote_target,
    wp_prefix_for,
)


def _local(root: Path) -> Target:
    """A local target built by hand, so the tests need no instance registry."""
    return Target(
        label="local:test",
        root=str(root),
        base_url="http://127.0.0.1:9999",
        prefix=("php", "-c", "php.ini", "wp", f"--path={root}"),
        shell_prefix=None,
        rsync_remote=None,
    )


def test_the_remote_target_reaches_the_host_read_write() -> None:
    """A cutover writes; a read-only command builder would fail at the first write."""
    target = remote_target()
    assert target.label == HOST
    assert target.base_url == "https://de-linker.com"
    assert target.shell_prefix == ("ssh", "-o", "BatchMode=yes", HOST, "bash -c")
    assert (
        target.rsync_remote
        == f"{HOST}:/home/u388076051/domains/de-linker.com/public_html"
    )
    # WP-CLI runs on the host, from the WordPress root, at the path
    # tools/pull/src/linker_pull/live.py recorded.
    assert (
        target.prefix[-1]
        == "cd /home/u388076051/domains/de-linker.com/public_html && /usr/local/bin/wp"
    )
    # WP-CLI is the host's own binary, reached through the ssh command above;
    # the two are different seams and neither is the other's alias.
    assert "/usr/local/bin/wp" in target.prefix[-1]
    assert target.root in target.prefix[-1]


def test_a_relative_path_resolves_under_the_root_and_an_absolute_one_is_refused(
    tmp_path: Path,
) -> None:
    """A path outside the root would let a removal step delete something else."""
    target = _local(tmp_path)
    assert target.path_of(PLUGINS) == str(tmp_path / PLUGINS)
    for escaping in ("/etc/passwd", "../../etc", "wp-content/../.."):
        with pytest.raises(CutoverError):
            target.path_of(escaping)


def test_the_wp_prefix_is_quoted_for_a_caller_that_splits_it() -> None:
    """tools/migrate gets `--wp <prefix>` as one string and shlex-splits it back."""
    import shlex

    target = _local(Path("/tmp/a root with spaces"))
    parts = shlex.split(wp_prefix_for(target))
    assert parts == list(target.prefix)
    assert parts[-1].endswith("a root with spaces")


def test_the_cache_buster_is_appended_to_every_read(
    site: tuple[Target, list[str]],
) -> None:
    """Production serves through LiteSpeed's cache; an uncache-busted read is not evidence."""
    target, requested = site
    assert target.http("/de/produkte/", cache_buster="abc") == (
        200,
        '<html lang="de">ok</html>',
    )
    assert requested == ["/de/produkte/?cbq=abc"]
    target.http("/?s=x", cache_buster="abc")
    assert requested[-1] == "/?s=x&cbq=abc"


@pytest.fixture
def site(tmp_path: Path) -> Iterator[tuple[Target, list[str]]]:
    """A loopback site, and the paths it was asked for.

    The last test's stand-in replaced `urllib.request.urlopen` with a function
    that returned 200 whatever the site said — which is how the probe below
    went on reporting a 301 as a 200. The stand-in is a server because the
    chain is the thing under test.
    """
    requested: list[str] = []

    class Site(BaseHTTPRequestHandler):
        """`/design-canvas/` is the redirect; every other path is a page."""

        def do_GET(self) -> None:  # noqa: N802 - http.server's own protocol name
            requested.append(self.path)
            if self.path.startswith("/design-canvas/"):
                self.send_response(301)
                self.send_header("Location", "/linker-planner/?step=roof")
                self.end_headers()
                self.wfile.write(b"moved")
                return
            if self.path.startswith("/missing/"):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"not found")
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<html lang="de">ok</html>')

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            """Quiet: the server's access log is not what these tests read."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target = Target(
        label="local:test",
        root=str(tmp_path),
        base_url=f"http://127.0.0.1:{server.server_port}",
        prefix=("wp",),
        shell_prefix=None,
        rsync_remote=None,
    )
    try:
        yield target, requested
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_a_redirect_is_reported_as_the_redirect_it_is(
    site: tuple[Target, list[str]],
) -> None:
    """A probe that follows redirects can never fail a 301 assertion.

    The drill's record lists `/design-canvas/` at 200 while the instance it ran
    against answers `301 Location: /linker-planner/?step=roof`, and `verify`
    asserts exactly that 301. What the probe followed is not what the address
    answered, and both facts matter: the chain is not requested at all here.
    """
    target, requested = site
    status, body = target.http("/design-canvas/", cache_buster="r1")
    assert status == 301
    assert requested == ["/design-canvas/?cbq=r1"], "the redirect must not be followed"
    assert "linker-planner" not in body


def test_an_error_status_is_the_status_the_address_answered(
    site: tuple[Target, list[str]],
) -> None:
    """A 404 is a finding about the site, not an exception the caller has to catch."""
    target, _ = site
    assert target.http("/missing/", cache_buster="r1") == (404, "not found")


def test_a_single_file_copies_out_and_in_without_the_directory_form(
    tmp_path: Path,
) -> None:
    """`copy_out`'s trailing slash means "this directory's contents"; on a file rsync fails.

    That is how `.htaccess` was written into a backup as an empty file rather
    than taken: the copy that was supposed to protect it failed and the failure
    was read as "this site has no `.htaccess`".
    """
    root = tmp_path / "root"
    (root / PLUGINS).mkdir(parents=True)
    (root / PLUGINS / "a.php").write_text("<?php", encoding="utf-8")
    target = _local(root)

    out = tmp_path / "out" / "a.php"
    target.copy_file_out(f"{PLUGINS}/a.php", out)
    assert out.read_text(encoding="utf-8") == "<?php"

    (root / PLUGINS / "a.php").write_text("<?php // changed", encoding="utf-8")
    target.copy_file_in(out, f"{PLUGINS}/a.php")
    assert (root / PLUGINS / "a.php").read_text(encoding="utf-8") == "<?php"

    # A directory is the other shape, and saying so is the caller's job.
    with pytest.raises(CutoverError, match="is not a file"):
        target.copy_file_out(PLUGINS, tmp_path / "out" / "plugins")
    with pytest.raises(CutoverError, match="is not a file"):
        target.copy_file_in(tmp_path, f"{PLUGINS}/b.php")
