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


def plan_group(plan: dict[str, Any], group: str) -> list[dict[str, Any]]:
    """The changes of one group; a plan may carry only some of the groups."""
    return list(plan.get(group) or [])


CHANGES = sum(len(plan_group(PLAN, group)) for group in facts.GROUPS)
UNCHANGED = sum(
    c["from"] == c["to"] for group in facts.GROUPS for c in plan_group(PLAN, group)
)
LOCAL = "http://127.0.0.1:8107"


def site_holding(side: str, siteurl: str = LOCAL) -> dict[str, Any]:
    """A site whose touched products hold the default plan's "from" or "to" side."""
    return site_holding_plan(PLAN, side, siteurl)


def plant_legacy(
    state_product: dict[str, Any], change: dict[str, Any], value: Any
) -> None:
    """Puts one string of a copy change at its path in the product's legacy JSON."""
    side = {"_tv_legacy_acf_json": "en", "_linker_de_acf_json": "de"}[
        change["meta_key"]
    ]
    legacy = state_product.setdefault("legacy", {})
    decoded = json.loads(legacy.get(side) or "{}")
    node = decoded
    *parents, last = change["path"]
    for step in parents:
        node = node.setdefault(step, {})
    node[last] = value
    legacy[side] = json.dumps(decoded, ensure_ascii=False)


def site_holding_plan(
    plan: dict[str, Any], side: str, siteurl: str = LOCAL
) -> dict[str, Any]:
    """A site whose touched products hold one side of a facts plan."""
    taxonomies = sorted({c["taxonomy"] for c in plan_group(plan, "attributes")})
    products: dict[str, Any] = {}
    for change in [
        *plan_group(plan, "attributes"),
        *plan_group(plan, "figures"),
        *plan_group(plan, "legacy_copy"),
    ]:
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
    for change in plan_group(plan, "attributes"):
        terms = change[side]
        products[str(change["product"])]["attributes"][change["taxonomy"]] = {
            "terms": terms,
            "attached": terms or None,
        }
    for change in plan_group(plan, "figures"):
        product = products[str(change["product"])]
        figures = json.loads(product["figures"])
        side_value = change[side]
        # A list of recorded "from" values is not one stored entry. The first
        # is the one this helper plants; a test that needs another plants it.
        if (
            side == "from"
            and isinstance(side_value, list)
            and side_value
            and isinstance(side_value[0], dict)
        ):
            side_value = side_value[0]
        figures[change["key"]] = side_value
        # fake_wp.py stores figures the way 7-facts.php does: unescaped
        # Unicode (a value may hold "×").
        product["figures"] = json.dumps(figures, ensure_ascii=False)
    for change in plan_group(plan, "legacy_copy"):
        product = products[str(change["product"])]
        side_value = change[side]
        # Like a figure, a list of recorded "from" values plants its first
        # entry; the tests that need another recorded state plant it themselves.
        if isinstance(side_value, list):
            side_value = side_value[0]
        plant_legacy(product, change, side_value)
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
        for change in plan_group(PLAN, group):
            assert change["basis"] in PLAN["basis"], change


def test_plan_selects_another_facts_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--plan` is how c15-facts.json reaches a site. The default file must stay untouched."""
    plan: dict[str, Any] = {
        "new_attribute": PLAN["new_attribute"],
        "attributes": [],
        "figures": [
            {
                "product": 6530,
                "key": "inverter_side_rated_power_kw",
                "from": [{"value": "60", "unit": "kW"}, {"value": "30", "unit": "kW"}],
                "to": None,
                "basis": "unverifiable",
            }
        ],
        "basis": {"unverifiable": "p.2 does not name this column"},
    }
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(plan))
    state = {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": json.dumps(
                    {"inverter_side_rated_power_kw": {"value": "60", "unit": "kW"}}
                ),
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }
    site = make_site(tmp_path, state)

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 0

    out = capsys.readouterr().out
    assert "1 to apply, 0 done, 0 drifted." in out
    assert site.state["writes"] == []


def test_a_deleted_figure_also_drops_the_legacy_row(tmp_path: Path) -> None:
    """The product page reads the legacy table. Deleting the figure and leaving the cited row is not done."""
    plan = {
        "new_attribute": {},
        "attributes": [],
        "figures": [
            {
                "product": 6530,
                "key": "inverter_side_rated_power_kw",
                "from": {"value": "30", "unit": "kW"},
                "to": None,
                "drop_legacy": {
                    "titles": ["Inverter side", "Wechselrichterseite"],
                    "labels": ["Rated power", "Nennleistung"],
                },
                "basis": "unverifiable",
            }
        ],
        "basis": {"unverifiable": "not in the column"},
    }
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(plan))
    legacy = {
        "spec_groups": [
            {
                "spec_group_title": "Inverter side",
                "spec_rows": [
                    {
                        "spec_label": "Rated power",
                        "spec_value": "30",
                        "spec_note": "Printed for this Model on the datasheet.",
                    }
                ],
            },
            {
                "spec_group_title": "Grid",
                "spec_rows": [{"spec_label": "Rated power", "spec_value": "60"}],
            },
        ]
    }
    state = {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": json.dumps(
                    {"inverter_side_rated_power_kw": {"value": "30", "unit": "kW"}}
                ),
                "legacy": {"en": json.dumps(legacy), "de": "{}"},
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }
    site = make_site(tmp_path, state)

    assert (
        facts.main(
            [
                "--plan",
                str(plan_path),
                "--wp",
                site.wp,
                "--write",
                "--backup-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    stored = json.loads(site.state["products"]["6530"]["legacy"]["en"])
    titles = [group["spec_group_title"] for group in stored["spec_groups"]]
    assert "Inverter side" not in titles
    assert "Grid" in titles


def test_a_null_figure_is_deleted(tmp_path: Path) -> None:
    """A cited 60 kW that the datasheet does not support has to leave the meta, not stay as null."""
    plan: dict[str, Any] = {
        "new_attribute": {},
        "attributes": [],
        "figures": [
            {
                "product": 6530,
                "key": "inverter_side_rated_power_kw",
                "from": {
                    "value": "60",
                    "unit": "kW",
                    "citation": {"url": "https://de-linker.com/x.pdf", "page": 2},
                },
                "to": None,
                "basis": "unverifiable",
            }
        ],
        "basis": {"unverifiable": "not in the column"},
    }
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(plan))
    state = {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": json.dumps(
                    {
                        "rated_power_kw": {"value": "60", "unit": "kW"},
                        "inverter_side_rated_power_kw": plan["figures"][0]["from"],
                    }
                ),
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }
    site = make_site(tmp_path, state)

    assert (
        facts.main(
            [
                "--plan",
                str(plan_path),
                "--wp",
                site.wp,
                "--write",
                "--backup-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    stored = json.loads(site.state["products"]["6530"]["figures"])
    assert "inverter_side_rated_power_kw" not in stored
    assert stored["rated_power_kw"]["value"] == "60"


def test_the_uncited_30_kw_is_apply_not_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A stored entry matching any recorded "from" is apply, not drift.

    A site that never saw a write still holds a value without a citation; a
    plan whose "from" lists it (and lists the key absent) applies there."""
    plan = {
        "new_attribute": {},
        "attributes": [],
        "figures": [
            {
                "product": 6530,
                "key": "inverter_side_rated_power_kw",
                "from": [
                    {
                        "value": "60",
                        "unit": "kW",
                        "citation": {"url": "https://de-linker.com/x.pdf", "page": 2},
                    },
                    {"value": "30", "unit": "kW"},
                ],
                "to": None,
                "basis": "unverifiable",
            }
        ],
        "basis": {"unverifiable": "not in the column"},
    }
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(plan))
    state = {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": json.dumps(
                    {"inverter_side_rated_power_kw": {"value": "30", "unit": "kW"}}
                ),
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }
    site = make_site(tmp_path, state)

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 0

    line = next(
        row
        for row in capsys.readouterr().out.splitlines()
        if "inverter_side_rated_power_kw" in row
    )
    assert line.startswith("apply")


def test_a_gone_figure_with_the_legacy_row_still_applies(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """t110 already lost the 60 kW key. The cited legacy row is still apply, not drift."""
    plan = {
        "new_attribute": {},
        "attributes": [],
        "figures": [
            {
                "product": 6530,
                "key": "inverter_side_rated_power_kw",
                "from": [{"value": "60"}, {"value": "30"}],
                "to": None,
                "drop_legacy": {
                    "titles": ["Inverter side"],
                    "labels": ["Rated power"],
                },
                "basis": "unverifiable",
            }
        ],
        "basis": {"unverifiable": "not in the column"},
    }
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(plan))
    state = {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": "{}",
                "legacy": {
                    "en": json.dumps(
                        {
                            "spec_groups": [
                                {
                                    "spec_group_title": "Inverter side",
                                    "spec_rows": [
                                        {
                                            "spec_label": "Rated power",
                                            "spec_value": "30",
                                        }
                                    ],
                                }
                            ]
                        }
                    )
                },
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }
    site = make_site(tmp_path, state)

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 0

    assert "1 to apply, 0 done, 0 drifted." in capsys.readouterr().out


def test_the_c15_plan_restores_the_inverter_side_key_with_both_documents() -> None:
    """The ESA 5–30 kW manual prints this switch's inverter side at 30 kW.

    The first pass deleted the key because the STS datasheet prints 30 kW in
    one cell merged across the table (pdftotext -bbox: word center x=396.9,
    GW30K column center x=318.9, GW60K column center x=474.8). The ESA 5–30 kW
    user manual §9.3 prints Rated Power 30 kW in the GW60K-STS-G10 column of
    the Inverter side block (p.340, value xMin=388.220, the column's own
    x-origin), so the merged cell is this model's value and the key is
    restored with a hosted citation and both documents recorded.
    """
    plan = json.loads((HERE.parent / "c15-facts.json").read_text())
    change = next(
        item
        for item in plan["figures"]
        if item["product"] == 6530 and item["key"] == "inverter_side_rated_power_kw"
    )
    assert change["to"]["value"] == "30"
    assert change["to"]["citation"]["url"].startswith("https://de-linker.com/")
    refs = " ".join(change["to"]["evidence_refs"])
    assert "GW_STS-30-60kW_Datasheet_EMEA-EN_V1.1.pdf:p2" in refs
    assert "GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf:p339-340" in refs
    assert "drop_legacy" not in change
    # A site that never saw the C15 write (production) still holds the uncited
    # 30 kW; t110 holds no key at all. Both are "apply", not drift.
    assert None in change["from"]
    assert {"value": "30", "unit": "kW"} in [
        {k: v for k, v in item.items() if k in ("value", "unit")}
        for item in change["from"]
        if isinstance(item, dict)
    ]
    basis = plan["basis"][change["basis"]]
    documents = [entry["document"] for entry in basis]
    assert any("GW_STS-30-60kW" in url for url in documents)
    assert any("GW_ESA-5-30kW_User-Manual-EN_V1.5" in url for url in documents)
    assert any("GW_ESA-5-30kW_User-Manual-DE_V1.4" in url for url in documents)
    assert "unverifiable" not in plan["basis"]


def test_the_c15_plan_restores_the_product_page_copy() -> None:
    """The rendered EN/DE copy must state the 30 kW with its two documents.

    The second correction edited the four strings on t110 to "not stated";
    the plan restores them. Each change records the edited text and the
    original (production's state before the cutover) as acceptable "from".
    """
    plan = json.loads((HERE.parent / "c15-facts.json").read_text())
    changes = plan_group(plan, "legacy_copy")
    assert len(changes) == 4
    keys = {(c["meta_key"], tuple(str(s) for s in c["path"])) for c in changes}
    assert keys == {
        ("_tv_legacy_acf_json", ("value_prop", "benefit_bullets", "0")),
        ("_tv_legacy_acf_json", ("feature_cards", "0", "feature_body")),
        ("_linker_de_acf_json", ("value_prop", "benefit_bullets", "0")),
        ("_linker_de_acf_json", ("feature_cards", "0", "feature_body")),
    }
    for change in changes:
        assert change["basis"] in plan["basis"], change
        assert isinstance(change["from"], list) and len(change["from"]) == 2
        assert change["to"] not in change["from"]
        assert "30 kW" in change["to"]
        if change["meta_key"] == "_tv_legacy_acf_json":
            assert "STS datasheet" in change["to"]
            assert "ESA 5–30 kW" in change["to"]
        else:
            assert "STS-Datenblatt" in change["to"]
            assert "ESA-Handbuch 5–30 kW" in change["to"]


def test_the_gw60k_faq_names_both_documents_for_the_30_kw() -> None:
    """The published FAQ must say the inverter side is 30 kW and where that is.

    tools/faq/import.py writes docs/faq/<slug>.json items with status pass.
    The first pass of goodwe-gw60k-sts-g10 said the inverter side was 60 kW
    at 91.0/87.0/83.4 A, maximum 100 A (those values sit in the GW60K column
    of Grid, Back-up and Smart Port). The second correction said the merged
    30 kW was "not under GW60K-STS-G10". pdftotext -bbox on the ESA 5–30 kW
    user manual p.340 puts 30 kW in the GW60K-STS-G10 column of the Inverter
    side block, so the answer names both documents.
    """
    record = json.loads(
        (HERE.parents[2] / "docs/faq/goodwe-gw60k-sts-g10.json").read_text()
    )
    passed = [item for item in record["items"] if item.get("status") == "pass"]
    assert passed
    armed = (
        "inverter side section of the datasheet, the GW60K-STS-G10 column lists a rated power of 60 kW",
        "Abschnitt „Inverter side“ des Datenblatts nennt die Spalte des GW60K-STS-G10 eine Nennleistung von 60 kW",
        "not under GW60K-STS-G10",
        "nicht unter GW60K-STS-G10",
    )
    for item in passed:
        text = f"{item['answer']}\n{item['answer_de']}"
        assert not any(sentence in text for sentence in armed)
        assert "30 kW" in item["answer"] and "30 kW" in item["answer_de"]
        assert (
            "ESA 5–30 kW" in item["answer"]
            and "ESA-Handbuch 5–30 kW" in item["answer_de"]
        )
        assert "GW60K-STS-G10 column" in item["answer"]
        assert "Spalte GW60K-STS-G10" in item["answer_de"]
        assert item["citation"]["page"] == 2


def sample_copy_plan() -> dict[str, Any]:
    """One copy change in the shape c15-facts.json uses."""
    return {
        "new_attribute": {},
        "attributes": [],
        "figures": [],
        "legacy_copy": [
            {
                "product": 6530,
                "meta_key": "_tv_legacy_acf_json",
                "path": ["value_prop", "benefit_bullets", 0],
                "from": ["the original text", "the edited text"],
                "to": "the corrected text",
                "basis": "sample",
            }
        ],
        "basis": {"sample": "the manual"},
    }


def copy_site(value: str) -> dict[str, Any]:
    """A site whose 6530 holds one benefit bullet on the English table."""
    return {
        "siteurl": LOCAL,
        "products": {
            "6530": {
                "attributes": {},
                "figures": "{}",
                "legacy": {
                    "en": json.dumps(
                        {"value_prop": {"benefit_bullets": [value]}},
                        ensure_ascii=False,
                    )
                },
                "protected": {"sku": "SKU-6530"},
            }
        },
        "writes": [],
    }


def test_a_copy_change_writes_and_reads_back(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(sample_copy_plan()))
    site = make_site(tmp_path, copy_site("the edited text"))

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 0
    out = capsys.readouterr().out
    change_line = next(row for row in out.splitlines() if "benefit_bullets" in row)
    assert change_line.startswith("apply")
    assert "1 to apply, 0 done, 0 drifted." in out

    assert (
        facts.main(
            [
                "--plan",
                str(plan_path),
                "--wp",
                site.wp,
                "--write",
                "--backup-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert out.rstrip().endswith("0 to apply, 1 done, 0 drifted.")
    stored = json.loads(site.state["products"]["6530"]["legacy"]["en"])
    assert stored["value_prop"]["benefit_bullets"][0] == "the corrected text"


def test_a_copy_change_applies_on_either_recorded_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """t110 holds the edited text, production the original; both are apply."""
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(sample_copy_plan()))
    site = make_site(tmp_path, copy_site("the original text"))

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 0
    assert "1 to apply, 0 done, 0 drifted." in capsys.readouterr().out


def test_a_copy_change_on_another_string_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(sample_copy_plan()))
    site = make_site(tmp_path, copy_site("something else entirely"))

    assert (
        facts.main(
            [
                "--plan",
                str(plan_path),
                "--wp",
                site.wp,
                "--write",
                "--backup-dir",
                str(tmp_path),
            ]
        )
        == 1
    )
    assert "drift" in capsys.readouterr().out
    assert site.state["writes"] == []


def test_a_copy_change_whose_path_is_gone_is_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The path must exist: a plan that describes a site it no longer is, stops."""
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(sample_copy_plan()))
    site = make_site(tmp_path, copy_site("the edited text"))
    state = site.state
    state["products"]["6530"]["legacy"]["en"] = json.dumps({"value_prop": {}})
    site.path.write_text(json.dumps(state))

    assert facts.main(["--plan", str(plan_path), "--wp", site.wp]) == 1
    assert "drift" in capsys.readouterr().out


def test_a_copy_write_that_does_not_read_back_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan_path = tmp_path / "c15-facts.json"
    plan_path.write_text(json.dumps(sample_copy_plan()))
    state = copy_site("the edited text")
    state["faults"] = ["ignore-writes"]
    site = make_site(tmp_path, state)

    assert (
        facts.main(
            [
                "--plan",
                str(plan_path),
                "--wp",
                site.wp,
                "--write",
                "--backup-dir",
                str(tmp_path),
            ]
        )
        == 1
    )
    assert "Not every change reads done." in capsys.readouterr().err


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
