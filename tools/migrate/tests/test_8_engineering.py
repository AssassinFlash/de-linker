"""Tests of 8-engineering.py: what it reports and when it writes, against a
site kept in a JSON file by fake_wp.py. The WordPress side
(8-engineering.php) is checked by PHPStan and driven against a real local
WordPress by test_8_engineering_wordpress.py."""

from __future__ import annotations

import importlib.util
import json
import shlex
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent


def load_script() -> ModuleType:
    """8-engineering.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "eight_engineering", HERE.parent / "8-engineering.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


eight = load_script()
PLAN: dict[str, Any] = json.loads(eight.PLAN.read_text())
CHANGES = sum(len(PLAN[group]) for group in eight.GROUPS)
ORPHANS = sum(len(entry["slugs"]) for entry in PLAN["remove_terms"])
LOCAL = "http://127.0.0.1:8108"


def site_holding(side: str, siteurl: str = LOCAL) -> dict[str, Any]:
    """A site whose touched products hold the state before (from) or after
    (to) the plan's changes."""
    products: dict[str, Any] = {}
    for change in PLAN["attributes"]:
        product = products.setdefault(
            str(change["product"]),
            {
                "attributes": {},
                "figures": "{}",
                "documents": "",
                "protected": {
                    "sku": f"SKU-{change['product']}",
                    "stock_status": "instock",
                },
            },
        )
        if side == "from":
            product["attributes"][change["taxonomy"]] = {
                "terms": change["from"],
                "attached": None,
            }
        else:
            terms = change["to"]
            product["attributes"][change["taxonomy"]] = {
                "terms": terms,
                "attached": terms or None,
            }
    for change in [*PLAN["figures"], *PLAN["citations"]]:
        product = products.setdefault(
            str(change["product"]),
            {
                "attributes": {},
                "figures": "{}",
                "documents": "",
                "protected": {
                    "sku": f"SKU-{change['product']}",
                    "stock_status": "instock",
                },
            },
        )
        figures = json.loads(product["figures"])
        entry = figures.get(change["key"], {})
        if change in PLAN["figures"]:
            entry = change["to"] if side == "to" else None
            if entry is None:
                figures.pop(change["key"], None)
            else:
                figures[change["key"]] = entry
        else:  # a citation: the site entry exists both sides, the citation only after
            entry = dict(entry)
            entry["value"] = change["value"]
            if side == "to":
                entry["citation"] = change["citation"]
            figures[change["key"]] = entry
        product["figures"] = json.dumps(figures, ensure_ascii=False)
    for change in PLAN["documents"]:
        product = products.setdefault(
            str(change["product"]),
            {
                "attributes": {},
                "figures": "{}",
                "documents": "",
                "protected": {
                    "sku": f"SKU-{change['product']}",
                    "stock_status": "instock",
                },
            },
        )
        if side == "to":
            product["documents"] = json.dumps(change["to"], ensure_ascii=False)
    return {
        "siteurl": siteurl,
        "products": products,
        # The orphan terms exist before the plan runs; after it they are gone.
        **(
            {
                "term_counts": {
                    f"pa_series:{slug}": 0
                    for entry in PLAN["remove_terms"]
                    for slug in entry["slugs"]
                }
            }
            if side == "from"
            else {"term_counts": {}}
        ),
        "writes": [],
    }


class Site:
    """The JSON file fake_wp.py serves, and the --wp command that reaches it."""

    def __init__(self, path: Path, state: dict[str, Any]) -> None:
        self.path = path
        path.write_text(json.dumps(state))
        self.wp = shlex.join([sys.executable, str(HERE / "fake_wp.py"), str(path)])

    @property
    def state(self) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.path.read_text())
        return loaded


def make_site(tmp_path: Path, state: dict[str, Any]) -> Site:
    return Site(tmp_path / "site.json", state)


def test_dry_run_reports_every_change_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = make_site(tmp_path, site_holding("from"))

    assert eight.main(["--wp", site.wp]) == 0

    out = capsys.readouterr().out
    assert f"{CHANGES + ORPHANS} to apply, 0 done, 0 drifted." in out
    assert site.state["writes"] == []


def test_write_backs_up_writes_and_reads_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = site_holding("from")
    site = make_site(tmp_path, before)
    backups = tmp_path / "backups"
    backups.mkdir()

    assert eight.main(["--wp", site.wp, "--write", "--backup-dir", str(backups)]) == 0

    out = capsys.readouterr().out
    assert out.rstrip().endswith(f"0 to apply, {CHANGES} done, 0 drifted.")
    assert len(site.state["writes"]) == 1
    (backup,) = backups.iterdir()
    assert json.loads(backup.read_text())["products"] == before["products"]
    # The figures are JSON strings whose key order the write may reorder.
    assert {
        pid: {
            **product,
            "figures": json.loads(product["figures"]),
            "documents": json.loads(product["documents"] or "null"),
        }
        for pid, product in site.state["products"].items()
    } == {
        pid: {
            **product,
            "figures": json.loads(product["figures"]),
            "documents": json.loads(product["documents"] or "null"),
        }
        for pid, product in site_holding("to")["products"].items()
    }
    # The plan's orphan terms are gone.
    assert site.state["term_counts"] == {}


def test_write_needs_a_backup_directory(tmp_path: Path) -> None:
    site = make_site(tmp_path, site_holding("from"))

    with pytest.raises(SystemExit) as exit_info:
        eight.main(["--wp", site.wp, "--write"])

    assert exit_info.value.code == 2
    assert site.state["writes"] == []


def test_drift_refuses_to_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = site_holding("from")
    figure = PLAN["figures"][0]
    product = state["products"][str(figure["product"])]
    figures = json.loads(product["figures"])
    figures[figure["key"]] = {**figure["to"], "value": "30000"}
    product["figures"] = json.dumps(figures)
    site = make_site(tmp_path, state)

    assert eight.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 1

    captured = capsys.readouterr()
    assert "drift" in captured.out
    assert "Refusing to write: the site has drifted from the plan." in captured.err
    assert site.state["writes"] == []


def test_a_citation_for_a_changed_value_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The plan cites a value; a site holding another one is drift, not a
    write: the citation must never land beside a value it does not state."""
    state = site_holding("from")
    citation = PLAN["citations"][0]
    product = state["products"][str(citation["product"])]
    figures = json.loads(product["figures"])
    figures[citation["key"]]["value"] = "not-the-cited-value"
    product["figures"] = json.dumps(figures)
    site = make_site(tmp_path, state)

    assert eight.main(["--wp", site.wp]) == 1

    out = capsys.readouterr().out
    assert out.rstrip().endswith("1 drifted.")
    assert "drift  " in out


def test_an_in_use_orphan_term_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = site_holding("from")
    state["term_counts"] = {"pa_series:b": 2}
    site = make_site(tmp_path, state)

    assert eight.main(["--wp", site.wp]) == 1

    out = capsys.readouterr().out
    # The citation's row is the one drift; every other change still applies.
    assert out.rstrip().endswith("1 drifted.")
    assert "drift  " in out


def test_production_needs_the_production_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = make_site(tmp_path, site_holding("from", siteurl="https://de-linker.com"))
    write = ["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]

    assert eight.main(write) == 1
    assert "without --production" in capsys.readouterr().err
    assert site.state["writes"] == []

    assert eight.main([*write, "--production"]) == 0
    assert len(site.state["writes"]) == 1


def test_a_site_already_migrated_gets_no_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = make_site(tmp_path, site_holding("to"))

    assert eight.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 0

    assert "Nothing to write." in capsys.readouterr().out
    assert site.state["writes"] == []


@pytest.mark.parametrize(
    ("fault", "message"),
    [
        ("ignore-writes", "Not every change reads done."),
        ("touch-stock", "Fields the migration must not change changed"),
    ],
)
def test_a_write_that_does_not_read_back_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fault: str, message: str
) -> None:
    state = site_holding("from")
    state["faults"] = [fault]
    site = make_site(tmp_path, state)

    assert eight.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 1

    assert message in capsys.readouterr().err
