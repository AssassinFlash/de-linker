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
from types import SimpleNamespace

import pytest

from linker_cutover.target import (
    HOST,
    PLUGINS,
    CutoverError,
    Target,
    _local_entries,
    remote_entries_command,
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
                self.send_header("Location", "/solution-configurator/?step=roof")
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
    against answers `301 Location: /solution-configurator/?step=roof`, and `verify`
    asserts exactly that 301. What the probe followed is not what the address
    answered, and both facts matter: the chain is not requested at all here.
    """
    target, requested = site
    status, body = target.http("/design-canvas/", cache_buster="r1")
    assert status == 301
    assert requested == ["/design-canvas/?cbq=r1"], "the redirect must not be followed"
    assert "solution-configurator" not in body


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


def test_the_remote_shell_quotes_the_script_as_one_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ssh joins its arguments with spaces and the login shell splits again.

    Measured 2026-10-14 against the production host: an unquoted script arrived
    as `bash -c if [ -e ... ]` and died on the first `then`. The script element
    therefore travels through `shlex.quote`.
    """
    seen: list[list[str]] = []

    def capture(command: list[str], *, cwd: Path | None = None) -> str:
        seen.append(command)
        return ""

    monkeypatch.setattr("linker_cutover.target._run", capture)
    remote_target().shell("if [ -e x ]; then echo yes; else echo no; fi")

    assert seen == [
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            HOST,
            "bash -c",
            "'if [ -e x ]; then echo yes; else echo no; fi'",
        ]
    ]


def test_the_on_target_wp_command_drops_the_transport() -> None:
    """The dump scripts run on the machine they read; the ssh prefix is not it."""
    remote = remote_target().wp_on_target()
    assert remote[0] == "/usr/local/bin/wp"
    assert remote[1].startswith("--path=/home/u388076051")
    assert all("ssh" not in part for part in remote)


def test_the_chunk_listing_asks_for_files_and_second_level_directories() -> None:
    """One short connection per chunk: months under uploads, dirs under plugins.

    Four kinds, because two leave gaps: a file directly inside a first-level
    directory and a first-level directory without subdirectories are each
    covered by no other kind (195 files went missing that way, 2026-10-14).
    """
    command = remote_entries_command(HOST, "/srv/wp-content/uploads")
    assert command[:4] == ["ssh", "-o", "BatchMode=yes", HOST]
    script = command[4]
    assert "cd /srv/wp-content/uploads" in script
    assert "F %p" in script
    assert "D %p" in script
    assert "-maxdepth 1 -type d -printf 'd %p" in script


def test_copy_out_pulls_the_four_chunk_kinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The listing's four kinds decide what travels, so each must be pulled.

    A first-level directory with subdirectories is pulled by its
    subdirectories plus its own files; one without them travels whole —
    skipping it because "its children cover it" is how a whole single-file
    plugin can vanish from a backup.
    """
    listing = "\n".join(
        [
            "D ./assets/fonts",
            "F ./logo-direct.png",
            "F ./root.txt",
            "d ./templates",
            "d ./assets",
        ]
    )
    seen: list[list[str]] = []

    def capture(command: list[str], *args: object, **kwargs: object) -> object:
        del args, kwargs
        seen.append(command)
        if command[0] == "ssh":
            return SimpleNamespace(returncode=0, stdout=listing, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    target = remote_target()
    relative = f"{PLUGINS}/demo"
    target.copy_out(relative, tmp_path / "demo")

    base = target.path_of(relative)
    pulls = [command[-2] for command in seen if command[0] == "rsync"]
    assert pulls == [
        f"{HOST}:{base}/logo-direct.png",
        f"{HOST}:{base}/root.txt",
        f"{HOST}:{base}/assets/fonts/",
        f"{HOST}:{base}/templates/",
    ]
    assert f"{HOST}:{base}/assets/" not in pulls, "its children carry it"


def test_copy_out_links_each_remote_chunk_to_the_same_place_in_the_earlier_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#305's incremental full backup: every chunk names its own earlier copy.

    A directory chunk links against the same directory in the earlier backup;
    a file chunk is pulled into its parent, so it links against the parent. A
    chunk the earlier backup does not have gets no `--link-dest` (rsync would
    warn and copy anyway).
    """
    listing = "\n".join(
        ["D ./assets/fonts", "F ./root.txt", "d ./templates", "d ./assets", "d ./new"]
    )
    seen: list[list[str]] = []

    def capture(command: list[str], *args: object, **kwargs: object) -> object:
        del args, kwargs
        seen.append(command)
        if command[0] == "ssh":
            return SimpleNamespace(returncode=0, stdout=listing, stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    earlier = tmp_path / "earlier" / "demo"
    for kept in ("assets/fonts", "templates"):
        (earlier / kept).mkdir(parents=True)
    target = remote_target()
    target.copy_out(f"{PLUGINS}/demo", tmp_path / "demo", link_dest=earlier)

    links = {
        command[-2].rsplit("/demo/", 1)[1]: next(
            (part for part in command if part.startswith("--link-dest=")), None
        )
        for command in seen
        if command[0] == "rsync"
    }
    assert links == {
        "root.txt": f"--link-dest={earlier.resolve()}",
        "assets/fonts/": f"--link-dest={(earlier / 'assets' / 'fonts').resolve()}",
        "templates/": f"--link-dest={(earlier / 'templates').resolve()}",
        "new/": None,
    }


def test_copy_in_sends_each_chunk_to_one_host_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`address()` already carries `host:`; `_push_entry` adds it again.

    Measured on the production deploy 2026-10-14: every chunk went to
    `hostinger-de-linker:hostinger-de-linker:/…` and the deploy died on the
    first file. The remote branch hands `_push_entry` the bare path, so the
    host appears exactly once and exactly where the caller can see it.
    """
    source = tmp_path / "staged" / "linker-commerce"
    (source / "includes").mkdir(parents=True)
    (source / "vendor").mkdir()
    (source / "vendor" / "autoload").mkdir()
    (source / "linker-commerce.php").write_text("<?php", encoding="utf-8")

    seen: list[list[str]] = []

    def capture(command: list[str], *args: object, **kwargs: object) -> object:
        del args, kwargs
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    # Force the per-entry walk: the tree here is small and would take the
    # single-leg path a real deploy uses for it.
    monkeypatch.setattr("linker_cutover.target.SMALL_UPLOAD_BYTES", 0)
    target = remote_target()
    relative = f"{PLUGINS}/linker-commerce"
    target.copy_in(source, relative)

    base = target.path_of(relative)
    # The destination may not exist yet (the first deploy of a plugin), and
    # rsync's receiver creates the final path component only — so every
    # chunk's directory goes out first, in one shell.
    mkdir, *pushes = seen
    assert mkdir[:5] == ["ssh", "-o", "BatchMode=yes", HOST, "bash -c"]
    assert f"mkdir -p {base} {base}/includes {base}/vendor/autoload" in mkdir[-1]
    destinations = [command[-1] for command in pushes]
    assert destinations == [
        f"{HOST}:{base}/linker-commerce.php",
        f"{HOST}:{base}/includes",
        f"{HOST}:{base}/vendor/autoload",
    ]
    for destination in destinations:
        assert f"{HOST}:{HOST}:" not in destination


def test_a_small_tree_goes_in_one_leg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 23 MB tree took 22 minutes as one connection per file (2026-10-18).

    Under the cap the whole tree is one rsync to the same bare path, so the
    host appears once and the upload is seconds, not minutes.
    """
    source = tmp_path / "staged" / "linker-tools"
    (source / "includes").mkdir(parents=True)
    (source / "includes" / "Plugin.php").write_text("<?php", encoding="utf-8")
    (source / "linker-tools.php").write_text("<?php", encoding="utf-8")

    seen: list[list[str]] = []

    def capture(command: list[str], *args: object, **kwargs: object) -> object:
        del args, kwargs
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    target = remote_target()
    relative = f"{PLUGINS}/linker-tools"
    target.copy_in(source, relative)

    base = target.path_of(relative)
    mkdir, *rsyncs = seen
    assert mkdir[:5] == ["ssh", "-o", "BatchMode=yes", HOST, "bash -c"]
    assert f"mkdir -p {base}" in mkdir[-1]
    [push] = rsyncs
    assert push[0] == "rsync" and "--delete" in push
    assert push[-2:] == [f"{source}/", f"{HOST}:{base}/"]
    assert f"{HOST}:{HOST}:" not in push[-1]


def test_the_local_chunks_cover_every_file(tmp_path: Path) -> None:
    """No file may fall between two chunks.

    Measured 2026-10-14: the two-kind rule (root files, depth-2 directories)
    left every file that lives directly inside a first-level directory out of
    the deploy and the backup — `vendor/autoload.php` beside `vendor/composer/`
    is exactly that shape. The property is the whole rule: every file in the
    tree is inside exactly one chunk, and no chunk overlaps another.
    """
    source = tmp_path / "plugin"
    for relative in (
        "root.php",
        "assets/logo.svg",
        "assets/fonts/x.woff2",
        "assets/fonts/deep/y.bin",
        "includes/Bootstrap.php",
        "includes/Core/Thing.php",
        "templates/single.php",
        "flat/plugin.php",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")

    files = [path for path in source.rglob("*") if path.is_file()]
    chunks = _local_entries(source)
    for path in files:
        owners = [
            chunk
            for chunk in chunks
            if path == chunk or (chunk.is_dir() and path.is_relative_to(chunk))
        ]
        assert len(owners) == 1, f"{path} is in {len(owners)} chunks"

    # And the chunks are the expected shape, not one whole-tree copy.
    names = {str(chunk.relative_to(source)) for chunk in chunks}
    assert names == {
        "root.php",
        "assets/logo.svg",
        "assets/fonts",
        "includes/Bootstrap.php",
        "includes/Core",
        "templates",
        "flat",
    }


def test_the_remote_wp_quotes_an_argument_with_spaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`wp eval '<php>'` died remotely: ssh joins argv, the login shell splits.

    Measured 2026-10-14: the snippet export arrived as `wp eval $rows =
    $GLOBALS['wpdb']->get_results(` and the remote shell died on the
    parenthesis. Every remote argument travels quoted; plain words are
    unchanged.
    """
    import shlex

    seen: list[list[str]] = []

    def capture(command: list[str], **kwargs: object) -> object:
        del kwargs
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    code = "$rows = $GLOBALS['wpdb']->get_results(\"SELECT 1\");"
    remote_target().wp("eval", code)

    command = seen[0]
    assert command[:4] == ["ssh", "-o", "BatchMode=yes", HOST]
    remote = command[4]
    assert " eval " in remote
    assert shlex.quote(code) in remote


def test_a_plain_remote_wp_call_reads_the_same_after_quoting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quoting changed nothing for the words the other calls pass."""
    seen: list[list[str]] = []

    def capture(command: list[str], **kwargs: object) -> object:
        del kwargs
        seen.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("linker_cutover.target.subprocess.run", capture)
    remote_target().wp("plugin", "list", "--fields=name")

    plain = remote_target().prefix[-1]
    assert seen[0][4] == f"{plain} plugin list --fields=name"
