"""8-engineering.py with its real WordPress side (8-engineering.php) on a
local instance.

The instance is the one whose WP-CLI command is LINKER_MIGRATE_TEST_WP, e.g.
~/de-linker-local/t8/wp, loaded with a live snapshot (docs/specs/
6-live-pull.md). Without it the tests are skipped (CI has no WordPress).
Unlike 7-facts there is no --reverse: the write adds keys, citations, terms
and meta and removes the plan's orphan pa_series terms, so the rehearsal
state is the end state. The tests drive the PHP write path for real (the
unit tests cover the state machine; these prove the WordPress side writes
what the plan says) and leave the instance migrated, which it already is
after the rehearsal.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
WP = os.environ.get("LINKER_MIGRATE_TEST_WP", "")

pytestmark = pytest.mark.skipif(
    not WP,
    reason="Set LINKER_MIGRATE_TEST_WP to the WP-CLI command of a local "
    "instance loaded with a live snapshot (docs/specs/6-live-pull.md).",
)


def load_script() -> ModuleType:
    """8-engineering.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "eight_engineering_wp", HERE.parent / "8-engineering.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


eight = load_script()
PLAN: dict[str, Any] = json.loads(eight.PLAN.read_text())


def statuses() -> dict[str, int]:
    """How many changes of each group the instance holds as done."""
    site = eight.read_site(shlex.split(WP), PLAN)
    counts = {"apply": 0, "done": 0, "drift": 0}
    for group in eight.GROUPS:
        for change in PLAN[group]:
            counts[eight.status(site, group, change)] += 1
    return counts


def test_the_wordpress_side_reads_every_change():  # type: ignore[no-untyped-def]
    """The PHP read answers every product the plan touches with the fields
    the state machine reads: a dry run ends 0 drifted."""
    assert eight.main(["--wp", WP]) == 0


def test_the_write_path_has_already_run_and_reads_done():  # type: ignore[no-untyped-def]
    """The rehearsal wrote the plan on this instance; the state machine and
    the PHP read agree that every change is done, which is what the cutover
    (#17) will see after it runs the write."""
    assert statuses()["done"] == sum(len(PLAN[g]) for g in eight.GROUPS)
    assert statuses()["drift"] == 0
    assert statuses()["apply"] == 0


def test_a_citation_write_lands_beside_its_value():  # type: ignore[no-untyped-def]
    """The PHP citation writer sets exactly the citation and touches nothing
    else of the entry: re-applying one plan citation onto the migrated
    instance leaves the stored figures byte-identical."""
    wp = shlex.split(WP)
    citation = next(c for c in PLAN["citations"] if c["product"] == 4107)
    site = eight.read_site(wp, PLAN)
    before = site["products"]["4107"]["figures"]

    eight.wp_eval(
        wp,
        {
            "action": "write",
            "new_attribute": PLAN["new_attribute"],
            "remove_terms": [],
            "attributes": [],
            "figures": [],
            "citations": [citation],
            "documents": [],
        },
    )

    after = eight.read_site(wp, PLAN)["products"]["4107"]["figures"]
    assert after == before
