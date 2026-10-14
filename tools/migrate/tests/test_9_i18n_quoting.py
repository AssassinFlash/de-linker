"""Tests of 9-i18n.py's WP wrapper: how a command travels to a remote site.

The drill runs the migration against a local instance, where the prefix is an
argv list and nothing re-splits it. Against the production host the prefix is
an ssh command line, and an argument with spaces must survive the login shell
— measured 2026-10-14: the category SELECT died on "Too many positional
arguments" because it arrived unquoted.
"""

from __future__ import annotations

import importlib.util
import shlex
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent


def load_script() -> ModuleType:
    """9-i18n.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "nine_i18n", HERE.parent / "9-i18n.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


i18n = load_script()

REMOTE = (
    "ssh -o BatchMode=yes hostinger-de-linker "
    "'cd /home/u388076051/domains/de-linker.com/public_html && /usr/local/bin/wp'"
)
LOCAL = "/Users/x/de-linker-local/t9/wp.sh"


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    seen: list[list[str]] = []

    def capture(command: list[str], **kwargs: object) -> object:
        del kwargs
        seen.append(list(command))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", capture)
    return seen


def test_a_remote_query_travels_as_one_quoted_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _capture(monkeypatch)
    sql = "SELECT term_id FROM wp_term_taxonomy WHERE taxonomy = 'product_cat' LIMIT 1"
    i18n.WP(REMOTE, user=None).run("db", "query", sql, "--skip-column-names")

    command = seen[0]
    assert command[:4] == ["ssh", "-o", "BatchMode=yes", "hostinger-de-linker"]
    remote = command[4]
    assert remote.startswith(
        "cd /home/u388076051/domains/de-linker.com/public_html && /usr/local/bin/wp "
    )
    assert shlex.quote(sql) in remote
    assert shlex.quote("--skip-column-names") in remote


def test_a_remote_admin_call_signs_in_after_quoting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _capture(monkeypatch)
    i18n.WP(REMOTE, user="857558227@qq.com").run(
        "linker-i18n", "setup", "--assign", as_user=True
    )

    remote = seen[0][4]
    assert remote.endswith("--user=857558227@qq.com")
    assert " setup " in remote


def test_post_category_slugs_are_the_live_german_archive_slugs() -> None:
    """The live German archives answer on the English slugs.

    Measured 2026-10-13 (docs/debt/DE-PARITY-2026-10-13.md §4.1):
    /de/category/system-design/ is 200 de-DE; /de/category/systemauslegung/
    is 404. A slug minted from the German name is what Polylang 301s back to
    English.
    """
    assert i18n.POST_CATEGORIES == {
        "System Design": ("Systemauslegung", "system-design"),
        "Battery Storage": ("Batteriespeicher", "battery-storage-blog"),
        "Installation & Commissioning": (
            "Installation & Inbetriebnahme",
            "installation-commissioning",
        ),
        "Monitoring & Energy Management": (
            "Überwachung & Energiemanagement",
            "monitoring-energy-management",
        ),
        "Applications": ("Anwendungen", "applications-blog"),
    }
    for _name, (german_name, slug) in i18n.POST_CATEGORIES.items():
        assert slug
        assert " " not in slug
        assert german_name


def test_a_local_prefix_keeps_argv_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    """The drill's local instance is not a shell: quoting there would change the
    argument the program receives."""
    seen = _capture(monkeypatch)
    i18n.WP(LOCAL, user=None).run("db", "query", "SELECT 1")

    assert seen[0] == [LOCAL, "db", "query", "SELECT 1"]
