"""Tests of 7-facts.py: what it reports and when it writes, against a site kept
in a JSON file by fake_wp.py. The WordPress side (7-facts.php) is checked by
PHPStan and driven against a real local WordPress by
test_7_facts_wordpress.py."""

from __future__ import annotations

import copy
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
    """7-facts.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "seven_facts", HERE.parent / "7-facts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


facts = load_script()
PLAN: dict[str, Any] = json.loads(facts.PLAN.read_text())
CHANGES = len(PLAN["attributes"]) + len(PLAN["figures"])
UNCHANGED = sum(c["from"] == c["to"] for group in facts.GROUPS for c in PLAN[group])
LOCAL = "http://127.0.0.1:8107"


def site_holding(side: str, siteurl: str = LOCAL) -> dict[str, Any]:
    """A site whose touched products hold the plan's "from" or "to" side."""
    taxonomies = sorted({c["taxonomy"] for c in PLAN["attributes"]})
    products: dict[str, Any] = {}
    for change in [*PLAN["attributes"], *PLAN["figures"]]:
        products.setdefault(
            str(change["product"]),
            {
                "attributes": {t: {"terms": [], "attached": None} for t in taxonomies},
                "figures": "{}",
                "protected": {
                    "sku": f"SKU-{change['product']}",
                    "stock_status": "instock",
                },
            },
        )
    for change in PLAN["attributes"]:
        terms = change[side]
        products[str(change["product"])]["attributes"][change["taxonomy"]] = {
            "terms": terms,
            "attached": terms or None,
        }
    for change in PLAN["figures"]:
        product = products[str(change["product"])]
        figures = json.loads(product["figures"])
        figures[change["key"]] = change[side]
        # fake_wp.py stores figures the way 7-facts.php does: unescaped
        # Unicode (a value may hold "×").
        product["figures"] = json.dumps(figures, ensure_ascii=False)
    return {"siteurl": siteurl, "products": products, "writes": []}


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

    assert facts.main(["--wp", site.wp]) == 0

    out = capsys.readouterr().out
    assert f"{CHANGES - UNCHANGED} to apply, {UNCHANGED} done, 0 drifted." in out
    assert site.state["writes"] == []


def test_write_backs_up_writes_and_reads_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = site_holding("from")
    site = make_site(tmp_path, before)
    backups = tmp_path / "backups"
    backups.mkdir()

    assert facts.main(["--wp", site.wp, "--write", "--backup-dir", str(backups)]) == 0

    out = capsys.readouterr().out
    assert out.rstrip().endswith(f"0 to apply, {CHANGES} done, 0 drifted.")
    assert len(site.state["writes"]) == 1
    (backup,) = backups.iterdir()
    assert json.loads(backup.read_text())["products"] == before["products"]
    assert site.state["products"] == site_holding("to")["products"]


def test_write_needs_a_backup_directory(tmp_path: Path) -> None:
    site = make_site(tmp_path, site_holding("from"))

    with pytest.raises(SystemExit) as exit_info:
        facts.main(["--wp", site.wp, "--write"])

    assert exit_info.value.code == 2
    assert site.state["writes"] == []


def test_drift_refuses_to_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = site_holding("from")
    figure = PLAN["figures"][0]
    product = state["products"][str(figure["product"])]
    figures = json.loads(product["figures"])
    figures[figure["key"]] = {**figure["from"], "value": "30000"}
    product["figures"] = json.dumps(figures)
    site = make_site(tmp_path, state)

    assert facts.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 1

    captured = capsys.readouterr()
    assert "drift" in captured.out
    assert "Refusing to write: the site has drifted from the plan." in captured.err
    assert site.state["writes"] == []


def test_production_needs_the_production_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = make_site(tmp_path, site_holding("from", siteurl="https://de-linker.com"))
    write = ["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]

    assert facts.main(write) == 1
    assert "without --production" in capsys.readouterr().err
    assert site.state["writes"] == []

    assert facts.main([*write, "--production"]) == 0
    assert len(site.state["writes"]) == 1


def test_reverse_undoes_a_write(tmp_path: Path) -> None:
    before = site_holding("from")
    site = make_site(tmp_path, before)
    write = ["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]

    assert facts.main(write) == 0
    assert facts.main([*write, "--reverse"]) == 0

    assert site.state["products"] == before["products"]


def test_a_site_already_migrated_gets_no_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    site = make_site(tmp_path, site_holding("to"))

    assert facts.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 0

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
    state = copy.deepcopy(site_holding("from"))
    state["faults"] = [fault]
    site = make_site(tmp_path, state)

    assert facts.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)]) == 1

    assert message in capsys.readouterr().err


def test_every_change_names_its_basis() -> None:
    for group in facts.GROUPS:
        for change in PLAN[group]:
            assert change["basis"] in PLAN["basis"], change


def test_a_failed_write_stops_before_the_read_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    state = site_holding("from")
    state["faults"] = ["fail-write"]
    site = make_site(tmp_path, state)

    with pytest.raises(SystemExit) as exit_info:
        facts.main(["--wp", site.wp, "--write", "--backup-dir", str(tmp_path)])

    assert str(exit_info.value.code).startswith("WP-CLI failed (255)")
    assert "Uncaught RuntimeException" in str(exit_info.value.code)
    assert "Read back:" not in capsys.readouterr().out
