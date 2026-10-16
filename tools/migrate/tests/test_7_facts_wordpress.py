"""7-facts.py with its real WordPress side (7-facts.php) on a local instance.

The instance is the one whose WP-CLI command is LINKER_MIGRATE_TEST_WP, e.g.
~/de-linker-local/t7/wp, seeded with
plugins/linker-commerce/tests/fixtures/load-live-products.php; without it the
tests are skipped (CI has no WordPress). The test writes, undoes and redoes
the plan there and leaves the instance as it found it (fixture or migrated).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
FIXTURE = (
    HERE.parents[2]
    / "plugins/linker-commerce/tests/fixtures/live-products-2026-10-09.json"
)
WP = os.environ.get("LINKER_MIGRATE_TEST_WP", "")

pytestmark = pytest.mark.skipif(
    not WP,
    reason="Set LINKER_MIGRATE_TEST_WP to the WP-CLI command of a local instance "
    "seeded with plugins/linker-commerce/tests/fixtures/load-live-products.php.",
)


def load_script() -> ModuleType:
    """7-facts.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "seven_facts_wp", HERE.parent / "7-facts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


facts = load_script()
PLAN: dict[str, Any] = json.loads(facts.PLAN.read_text())


def statuses(plan: dict[str, Any]) -> set[str]:
    """The statuses the instance gives the plan's changes now."""
    site = facts.read_site(shlex.split(WP), plan)
    return {
        facts.status(site, g, c)
        for g in facts.GROUPS
        for c in facts.plan_changes(plan, g)
    }


def fixture_figures() -> dict[str, str]:
    """The stored figures of the plan's products, as the fixture has them."""
    products = json.loads(FIXTURE.read_text())["products"]
    ids = {str(c["product"]) for c in PLAN["figures"]}
    return {
        str(p["id"]): p["meta"]["_tv_b2b_figures"]
        for p in products
        if str(p["id"]) in ids
    }


def run(*args: str, backups: Path) -> int:
    code: int = facts.main(["--wp", WP, *args, "--backup-dir", str(backups)])
    return code


@pytest.fixture
def at_fixture(tmp_path: Path) -> Iterator[Path]:
    """Brings the instance to the fixture's state, and back afterwards."""
    migrated = statuses(PLAN) == {"done"}
    if migrated:
        assert run("--reverse", "--write", backups=tmp_path) == 0
    assert statuses(facts.reversed_plan(PLAN)) == {"done"}
    yield tmp_path
    if migrated:
        assert run("--write", backups=tmp_path) == 0
    else:
        assert run("--reverse", "--write", backups=tmp_path) == 0


def test_write_reads_back_and_reverse_restores_the_bytes(at_fixture: Path) -> None:
    assert facts.main(["--wp", WP]) == 0
    assert run("--write", backups=at_fixture) == 0
    assert statuses(PLAN) == {"done"}
    assert run("--write", backups=at_fixture) == 0  # nothing left to write

    assert run("--reverse", "--write", backups=at_fixture) == 0
    site = facts.read_site(shlex.split(WP), PLAN)
    stored = {
        pid: p["figures"]
        for pid, p in site["products"].items()
        if pid in fixture_figures()
    }
    assert stored == fixture_figures()


def test_a_save_that_would_change_stock_writes_nothing(at_fixture: Path) -> None:
    wp = shlex.split(WP)
    subprocess.run(
        [*wp, "post", "meta", "update", "1179", "_stock", "5"],
        check=True,
        capture_output=True,
    )
    try:
        with pytest.raises(SystemExit) as refused:
            run("--write", backups=at_fixture)
        assert "Saving product 1179 would change stock_quantity" in str(
            refused.value.code
        )
        assert statuses(facts.reversed_plan(PLAN)) == {"done"}
    finally:
        subprocess.run(
            [*wp, "post", "meta", "delete", "1179", "_stock"],
            check=True,
            capture_output=True,
        )


def wp_cli(*args: str) -> str:
    """One WP-CLI command on the instance, output stripped."""
    result = subprocess.run(
        [*shlex.split(WP), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.rstrip("\n")


def test_the_group_rule_on_the_real_wordpress() -> None:
    """The empty-group rule with the real 7-facts.php — what the fake covers, on WordPress.

    A scratch product (created and deleted here; the plan's own products stay
    untouched) carries a synthetic legacy table: a two-row group, a group that
    is already empty, and a one-row group. One drop per outcome the rule
    states: an unnamed drop that empties a group is refused with nothing
    written; the same drop naming the group takes it with its last row; a
    partial drop keeps the group's other row; a group that was already empty
    stays unless the drop names it, and leaves when it does.
    """
    product = int(
        wp_cli(
            "post",
            "create",
            "--post_type=product",
            "--post_status=draft",
            "--post_title=scratch group rule",
            "--porcelain",
        )
    )
    figures = json.dumps({"scratch": {"value": "1", "unit": "kW"}})
    try:
        wp_cli("post", "meta", "update", str(product), facts.FIGURES_META_KEY, figures)
        # The German twin is not this case's subject; an empty table makes the
        # refusal walk skip it (it needs spec_groups).
        wp_cli("post", "meta", "update", str(product), "_linker_de_acf_json", "{}")

        def table() -> list[tuple[str, int]]:
            raw = wp_cli("post", "meta", "get", str(product), "_tv_legacy_acf_json")
            decoded = json.loads(raw)
            return [
                (
                    str(group.get("spec_group_title", "")),
                    len(group.get("spec_rows") or []),
                )
                for group in decoded["spec_groups"]
            ]

        def set_table(groups: list[dict[str, Any]]) -> None:
            wp_cli(
                "post",
                "meta",
                "update",
                str(product),
                "_tv_legacy_acf_json",
                json.dumps({"spec_groups": groups}, ensure_ascii=False),
            )

        def drop(titles: list[str], labels: list[str], remove: list[str] | None) -> str:
            change: dict[str, Any] = {
                "product": product,
                "group": "figures",
                "key": "scratch",
                "from": {"value": "1", "unit": "kW"},
                "to": None,
                "drop_legacy": {"titles": titles, "labels": labels},
                "basis": "unverifiable",
            }
            if remove is not None:
                change["drop_legacy"]["remove_groups"] = remove
            try:
                facts.wp_eval(
                    shlex.split(WP),
                    {
                        "action": "write",
                        "new_attribute": {},
                        "attributes": [],
                        "figures": [change],
                        "legacy_copy": [],
                    },
                )
            except SystemExit as refused:  # wp_eval exits with the WP-CLI failure
                return str(refused.code)
            return "ok"

        base: list[dict[str, Any]] = [
            {
                "spec_group_title": "Inverter side",
                "spec_rows": [
                    {"spec_label": "Rated power"},
                    {"spec_label": "Rated current"},
                ],
            },
            {"spec_group_title": "Emptied earlier", "spec_rows": []},
            {"spec_group_title": "Grid", "spec_rows": [{"spec_label": "Rated power"}]},
        ]

        set_table(base)
        refused = drop(["Inverter side"], ["Rated power", "Rated current"], None)
        assert "would remove the spec group" in refused
        assert table() == [
            ("Inverter side", 2),
            ("Emptied earlier", 0),
            ("Grid", 1),
        ], "a refusal writes nothing"

        set_table(base)
        assert (
            drop(["Inverter side"], ["Rated power", "Rated current"], ["Inverter side"])
            == "ok"
        )
        assert table() == [("Emptied earlier", 0), ("Grid", 1)], (
            "the named group leaves"
        )

        set_table(base)
        assert drop(["Inverter side"], ["Rated current"], None) == "ok"
        assert table() == [
            ("Inverter side", 1),
            ("Emptied earlier", 0),
            ("Grid", 1),
        ], "a partial drop keeps the other row"

        set_table(base)
        assert drop(["Grid"], ["Rated power"], ["Emptied earlier", "Grid"]) == "ok"
        assert table() == [("Inverter side", 2)], "naming an empty group removes it"
    finally:
        wp_cli("post", "delete", str(product), "--force")
