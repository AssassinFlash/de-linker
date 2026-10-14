"""Tests of 9-i18n.py's WP wrapper: how a command travels to a remote site.

The drill runs the migration against a local instance, where the prefix is an
argv list and nothing re-splits it. Against the production host the prefix is
an ssh command line, and an argument with spaces must survive the login shell
— measured 2026-10-14: the category SELECT died on "Too many positional
arguments" because it arrived unquoted.

The last tests bind the plugin's snapshot tables (Twins::POST_CATEGORIES and
Twins::POST_CATEGORY_SLUGS, the repair's authority) to what they must agree
with: the migration's slugs and the recorded snapshot rows.
"""

from __future__ import annotations

import importlib.util
import re
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
    assert i18n.POST_CATEGORY_NAMES == {
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
    for _name, (german_name, slug) in i18n.POST_CATEGORY_NAMES.items():
        assert slug
        assert " " not in slug
        assert german_name


def test_apply_repairs_post_categories_after_the_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The repair runs after the posts exist, and does not read the database.

    A lookup of the English term is empty on the live database, so the repair
    has to be its own step, after import, signed in as the administrator.
    """
    seen = _capture(monkeypatch)
    monkeypatch.setattr(
        i18n.WP,
        "json",
        lambda self, *args, **kwargs: [],
    )

    i18n.Migration(i18n.WP(LOCAL, user="local-admin")).apply([])

    commands = [call[1:] for call in seen]
    assert ["linker-i18n", "repair-post-categories", "--user=local-admin"] in commands
    repair = commands.index(
        ["linker-i18n", "repair-post-categories", "--user=local-admin"]
    )
    assert commands.index(["linker-i18n", "relink"]) > repair


def test_a_local_prefix_keeps_argv_semantics(monkeypatch: pytest.MonkeyPatch) -> None:
    """The drill's local instance is not a shell: quoting there would change the
    argument the program receives."""
    seen = _capture(monkeypatch)
    i18n.WP(LOCAL, user=None).run("db", "query", "SELECT 1")

    assert seen[0] == [LOCAL, "db", "query", "SELECT 1"]


def test_twins_post_category_slugs_match_the_migration_table() -> None:
    """The plugin's snapshot slug guard names the slugs the migration mints.

    Twins::POST_CATEGORY_SLUGS (the write guard) and POST_CATEGORY_NAMES here
    (what the migration mints/renames the German term to) must not drift: a
    slug changed in one table only mints the wrong German archive silently —
    the guard then refuses every write, or admits a term the archive never
    answers on, and /de/category/system-design/ 301s again (families 16/22;
    the slugs themselves are the 2026-10-13 live measurement,
    docs/debt/DE-PARITY-2026-10-13.md §4.1).
    """
    twins = (
        HERE.parent.parent.parent / "plugins/linker-i18n/includes/Twins.php"
    ).read_text(encoding="utf-8")
    block = twins.split("POST_CATEGORY_SLUGS = array(", 1)[1].split(");", 1)[0]
    php_slugs = {
        int(term_id): slug.strip("'")
        for term_id, slug in (
            line.strip().rstrip(",").split(" => ", 1)
            for line in block.splitlines()
            if " => " in line
        )
    }
    assert php_slugs == {
        10: "system-design",
        11: "battery-storage-blog",
        12: "installation-commissioning",
        13: "monitoring-energy-management",
        14: "applications-blog",
    }
    assert {slug for _de_name, slug in i18n.POST_CATEGORY_NAMES.values()} == set(
        php_slugs.values()
    )


def _twins_table(name: str) -> dict[int, str]:
    """One of Twins' id => value tables, parsed from the plugin source."""
    twins = (
        HERE.parent.parent.parent / "plugins/linker-i18n/includes/Twins.php"
    ).read_text(encoding="utf-8")
    block = twins.split(f"{name} = array(", 1)[1].split(");", 1)[0]
    return {
        int(key): value.strip("'")
        for key, value in (
            line.strip().rstrip(",").split(" => ", 1)
            for line in block.splitlines()
            if " => " in line
        )
    }


def test_twins_post_categories_are_the_snapshot_rows() -> None:
    """The plugin's post→term map is the snapshot's own relationship rows.

    Twins::POST_CATEGORIES is the repair's authority: posts 551–560 on terms
    10–14, two each. The rows are read back with the §2 commands of
    docs/debt/DE-PARITY-2026-10-13.md, which quotes the ten triples
    (object_id, term_taxonomy_id, term_order) of wp_term_relationships; the
    dumps themselves live outside the repository (~/de-linker-data), so the
    record is the side this test binds to. A row moved on either side means
    the repair writes onto the wrong objects; the post-type and slug guards
    are the second line, this is the first.
    """
    php_map = {
        post_id: int(term_id)
        for post_id, term_id in _twins_table("POST_CATEGORIES").items()
    }
    record = (
        HERE.parent.parent.parent / "docs/debt/DE-PARITY-2026-10-13.md"
    ).read_text(encoding="utf-8")
    snapshot_rows = {
        int(post_id): int(term_id)
        for post_id, term_id in re.findall(r"\((\d{3}),(\d{1,2}),0\)", record)
    }
    assert (
        php_map
        == snapshot_rows
        == {
            551: 10,
            552: 10,
            553: 11,
            554: 11,
            555: 12,
            556: 12,
            557: 13,
            558: 13,
            559: 14,
            560: 14,
        }
    )


def test_twins_snapshot_tables_cover_the_same_terms() -> None:
    """Every mapped term id carries a snapshot slug, so no id is silently skipped.

    snapshot_slug() answers '' for an id that is not in POST_CATEGORY_SLUGS,
    and both guards read '' as "not a snapshot term": a POST_CATEGORIES entry
    without a slug entry is skipped without a word and without a count. The
    two tables must name the same five terms.
    """
    categories = _twins_table("POST_CATEGORIES")
    slugs = _twins_table("POST_CATEGORY_SLUGS")

    assert {int(term_id) for term_id in categories.values()} == set(slugs)
