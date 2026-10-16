"""Tests of 12-site-chrome.py's WP wrapper: how a command travels to a remote site.

The drill runs against a local instance, where the prefix is an argv list and
nothing re-splits it. Against the production host the prefix is an ssh command
line: an argument with spaces (`--post_title=Genie - Linker's AI assistant`)
would break apart, and a temp file written here cannot be opened by a remote
WP-CLI — the PHP must travel on standard input.
"""

from __future__ import annotations

import base64
import importlib.util
import json
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


def _capture(monkeypatch: pytest.MonkeyPatch) -> tuple[list[list[str]], list[str]]:
    """The commands run and the stdin each carried, in order."""
    commands: list[list[str]] = []
    inputs: list[str] = []

    def capture(command: list[str], **kwargs: object) -> object:
        commands.append(list(command))
        stdin = kwargs.get("input")
        if isinstance(stdin, str):
            inputs.append(stdin)
        else:
            handle = kwargs.get("stdin")
            if hasattr(handle, "read"):
                data = handle.read()
                inputs.append(data.decode() if isinstance(data, bytes) else data)
            else:
                inputs.append("")
        return SimpleNamespace(returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr("subprocess.run", capture)
    return commands, inputs


def test_a_remote_title_with_spaces_travels_as_one_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands, _ = _capture(monkeypatch)
    title = "Genie - Linker's AI assistant"
    chrome.WP(REMOTE, user="admin").run(
        "post", "update", "4083", f"--post_title={title}", as_user=True
    )

    command = commands[0]
    assert command[:4] == ["ssh", "-o", "BatchMode=yes", "hostinger-de-linker"]
    assert shlex.quote(f"--post_title={title}") in command[4]


def test_the_php_travels_on_standard_input_not_as_a_local_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A temp path exists on this machine; the remote WP-CLI cannot open it."""
    commands, inputs = _capture(monkeypatch)
    chrome.WP(REMOTE, user=None).eval_php("echo 1;", {"a": 1})

    command = commands[0]
    assert "eval-file" in command[4]
    assert command[4].endswith(" -") or " - " in command[4], "eval-file reads stdin"
    assert inputs[0].startswith("<?php\n")
    assert "/var/folders" not in inputs[0]


def test_a_local_prefix_keeps_argv_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    commands, _ = _capture(monkeypatch)
    chrome.WP(LOCAL, user=None).run("post", "update", "4083", "--post_name=genie")

    assert commands[0] == [LOCAL, "post", "update", "4083", "--post_name=genie"]


def test_a_large_payload_rides_the_stdin_php_not_one_argument(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The German source metas carry whole page bodies (the header partial
    is 125 KB). Base64 in one argv died in `/bin/bash: Argument list too
    long` on the 2026-10-16 apply; the payload boards the PHP source
    itself, which travels on stdin."""
    commands, inputs = _capture(monkeypatch)
    body = "x" * 200_000
    chrome.WP(REMOTE, user=None).eval_php_embedded(
        "echo 1;", {"17": {"_linker_de_content": body}}
    )

    (command,) = commands
    assert "eval-file" in command[4]
    assert " - " in command[4] or command[4].endswith(" -"), "eval-file reads stdin"
    assert inputs[0].startswith("<?php\n$args = array(0 => '")
    # The payload text is in the PHP, not the command line.
    assert json.loads(base64.b64decode(_blob_of(inputs[0]))) == {
        "17": {"_linker_de_content": body}
    }
    assert body not in command[4]


def _blob_of(php: str) -> str:
    """The base64 blob the embedded channel set as $args[0]."""
    start = php.index("'") + 1
    return php[start : php.index("'", start)]


def test_the_meta_writer_still_decodes_args0() -> None:
    """One snippet form for both channels: the embedded channel sets
    $args[0] itself, the snippet keeps decoding it."""
    assert "base64_decode($args[0])" in chrome.META_WRITE_PHP
