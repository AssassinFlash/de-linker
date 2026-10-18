"""The deploy's opcode-cache reset (#308), end to end against a real PHP server.

PHP's built-in server runs the actual must-use plugin; the deploy's own
after-switch script runs in bash with a home of the test's own. What is
proven: the site answers the reset, the one-time token is gone afterwards,
and a request without the token is served as any other request.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from linker_cutover import atomic, steps
from linker_cutover.target import Target

PLUGIN = Path(__file__).resolve().parents[3] / "mu-plugins" / "linker-deploy-reset.php"
PHP = os.environ.get("PHP") or shutil.which("php")


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def site(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """A PHP server whose every request first loads the must-use plugin."""
    if PHP is None:
        pytest.skip("php is not installed")
    home = tmp_path / "home"
    home.mkdir()
    docroot = tmp_path / "docroot"
    docroot.mkdir()
    (docroot / "index.php").write_text(
        f"<?php require {str(PLUGIN)!r}; echo 'the site';\n", encoding="utf-8"
    )
    port = _free_port()
    server = subprocess.Popen(
        [PHP, "-S", f"127.0.0.1:{port}", "-t", str(docroot)],
        env={**os.environ, "HOME": str(home)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url + "/", timeout=1).read()
            break
        except OSError:
            time.sleep(0.1)
    try:
        yield url, home
    finally:
        server.terminate()
        server.wait(timeout=5)


def test_the_site_answers_the_reset_and_the_token_is_gone(
    site: tuple[str, Path],
) -> None:
    url, home = site
    target = Target("local:test", "/srv", url, (), None, None)

    completed = subprocess.run(
        ["bash", "-c", steps.opcache_reset_script(target)],
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    lines = [
        line[len(atomic.AFTER_SWITCH_MARKER) :]
        for line in completed.stdout.splitlines()
        if line.startswith(atomic.AFTER_SWITCH_MARKER)
    ]
    # The built-in server may run without the opcode cache; the plugin then
    # answers "unavailable". Either answer proves the request reached it.
    assert lines in (
        ["opcache-reset=done attempts=1"],
        ["opcache-reset=unavailable attempts=1"],
    )
    folder = home / ".config" / "terravolt-builder"
    assert not (folder / "opcache-reset.token").exists()
    assert not (folder / "opcache-reset.header").exists()


def test_a_request_without_the_token_is_an_ordinary_request(
    site: tuple[str, Path],
) -> None:
    url, home = site
    folder = home / ".config" / "terravolt-builder"
    folder.mkdir(parents=True)
    (folder / "opcache-reset.token").write_text("the-real-token\n", encoding="utf-8")
    request = urllib.request.Request(
        url + "/", method="POST", headers={"X-Linker-Opcache-Reset": "a-guess"}
    )

    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read().decode()
        answered = response.headers.get("X-Linker-Opcache-Reset")

    assert answered is None
    assert body == "the site"
    assert (folder / "opcache-reset.token").exists()


def test_the_token_never_appears_on_a_command_line() -> None:
    """Other accounts on the shared host can list processes: header from a file."""
    script = steps.opcache_reset_script(
        Target("local:test", "/srv", "https://de-linker.com", (), None, None)
    )
    assert '-H @"$dir/opcache-reset.header"' in script
    assert '-H "X-Linker' not in script
    assert "umask 077" in script
