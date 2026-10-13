"""Tests of 12-site-chrome.py's WP wrapper: how a command travels to a remote site.

The drill runs against a local instance, where the prefix is an argv list and
nothing re-splits it. Against the production host the prefix is an ssh command
line: an argument with spaces (`--post_title=Genie - Linker's AI assistant`)
would break apart, and a temp file written here cannot be opened by a remote
WP-CLI — the PHP must travel on standard input.
"""

from __future__ import annotations

import importlib.util
import shlex
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def load_script() -> ModuleType:
    """12-site-chrome.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "twelve_site_chrome", HERE.parent / "12-site-chrome.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chrome = load_script()

REMOTE = (
    "ssh -o BatchMode=yes hostinger-de-linker "
    "'cd /home/u388076051/domains/de-linker.com/public_html && /usr/local/bin/wp'"
)
LOCAL = "/Users/x/de-linker-local/t12/wp.sh"


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    seen: list[dict[str, object]] = []

    def capture(command: list[str], **kwargs: object) -> object:
        seen.append({"command": list(command), **kwargs})
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr("subprocess.run", capture)
    return seen


def test_a_remote_title_with_spaces_travels_as_one_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _capture(monkeypatch)
    title = "Genie - Linker's AI assistant"
    chrome.WP(REMOTE, user="admin").run(
        "post", "update", "4083", f"--post_title={title}", as_user=True
    )

    command = seen[0]["command"]
    assert command[:4] == ["ssh", "-o", "BatchMode=yes", "hostinger-de-linker"]
    assert shlex.quote(f"--post_title={title}") in command[4]


def test_the_php_travels_on_standard_input_not_as_a_local_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A temp path exists on this machine; the remote WP-CLI cannot open it."""
    seen = _capture(monkeypatch)
    chrome.WP(REMOTE, user=None).eval_php("echo 1;", {"a": 1})

    command = seen[0]["command"]
    assert "eval-file" in command[4]
    assert command[4].endswith(" -") or " - " in command[4], "eval-file reads stdin"
    assert seen[0]["input"].startswith("<?php\n")
    assert "/var/folders" not in seen[0]["input"]


def test_a_local_prefix_keeps_argv_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _capture(monkeypatch)
    chrome.WP(LOCAL, user=None).run("post", "update", "4083", "--post_name=genie")

    assert seen[0]["command"] == [LOCAL, "post", "update", "4083", "--post_name=genie"]
