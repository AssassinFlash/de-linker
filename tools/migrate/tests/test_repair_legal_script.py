"""The real lost-backslash pattern must restore scripts without rolling back copy."""

import importlib.util
from pathlib import Path
from typing import Any

import pytest

spec = importlib.util.spec_from_file_location(
    "repair", Path(__file__).parents[1] / "repair-legal-script.py"
)
assert spec and spec.loader
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)

GOOD = r"""<script id="tv-legal-js">var svg='\u003csvg>'; var text=/\s+/g; var fmt=/\{(\w+)\}/g;</script>"""
BAD = GOOD.replace("\\", "")


def test_restore_preserves_current_copy_and_every_other_byte() -> None:
    current = (
        "<p>Current inquiry summary and cookie policy. Grüße.</p>"
        + BAD
        + "<style>body{color:navy}</style>"
    )
    reference = "<p>Obsolete policy.</p>" + GOOD
    fixed = repair.restore_script(current, reference)
    assert fixed == current.replace(BAD, GOOD)
    assert repair.restore_script(fixed, reference) == fixed


@pytest.mark.parametrize(
    "script", [BAD.replace("var svg", "var changed"), "", BAD + BAD]
)
def test_refuses_unrelated_script_changes_or_ambiguous_blocks(script: str) -> None:
    with pytest.raises(ValueError):
        repair.restore_script(script, GOOD)


def test_no_shell_execution_in_remote_content(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        stdout = '@@legal-script@@{"ok": true}'
        stderr = ""
        returncode = 0

    seen: list[tuple[list[str], dict[str, Any]]] = []

    def run(command: list[str], **kwargs: Any) -> Result:
        seen.append((command, kwargs))
        return Result()

    monkeypatch.setattr(repair.subprocess, "run", run)
    assert repair.invoke(
        "ssh -o BatchMode=yes hostinger-de-linker /usr/local/bin/wp --path=/site",
        {"content": "`sensitive` $(bad)\n\\u003c"},
    ) == {"ok": True}
    assert seen[0][0][:4] == ["ssh", "-o", "BatchMode=yes", "hostinger-de-linker"]
    assert seen[0][0][-1] == "eval 'eval( stream_get_contents( STDIN ) );'"
    assert "$(bad)" not in seen[0][1]["input"]
