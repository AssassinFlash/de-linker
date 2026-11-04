"""Local contract tests for the guarded #548 battery parallel-limits migration."""

from __future__ import annotations

import base64
import json
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent
PLAN = HERE.parent / "548-battery-parallel-limits.json"
EXCERPTS = HERE.parent / "548-page-excerpts.json"

EXPECTED = {
    "1956": ("GW208.9-BAT-LC-G10", "4", "units"),
    "1957": ("GW208.9-BAT-LCD-G10", "4", "units"),
    "3611": ("GW6.0-BAT-D-G20", "3", "expansion groups"),
    "3612": ("GW9.0-BAT-D-G20", "3", "expansion groups"),
    "6519": ("GW5.1-BAT-D-G20", "3", "expansion groups"),
    "6520": ("GW8.3-BAT-D-G20", "3", "expansion groups"),
    "6521": ("GW5.1-BAT-D-G21", "3", "expansion groups"),
    "6522": ("GW8.3-BAT-D-G21", "3", "expansion groups"),
    "6321": ("GW125/261-ESA-LCN-G10", "8", "units"),
    "2003": ("L260-OMNI", "6", "units"),
}
# Products whose own associated documents print no parallel-cluster limit stay out.
NOT_WRITTEN = ("1954", "1955", "1958", "2409", "2093")


def load_migration() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "battery_parallel_limits", HERE.parent / "548-battery-parallel-limits.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_reviewed_plan_pins_every_limit_to_one_document_page() -> None:
    plan = json.loads(PLAN.read_text())
    assert plan["kind"] == "battery_parallel_limits_v1"
    assert {
        key: (
            row["model"],
            row["figures"]["stacks_parallel_max"]["set"]["value"],
            row["figures"]["stacks_parallel_max"]["set"]["unit"],
        )
        for key, row in plan["products"].items()
    } == EXPECTED
    for key, row in plan["products"].items():
        change = row["figures"]["stacks_parallel_max"]
        source = change["source"]
        citation = change["set"]["citation"]
        if key in {"3611", "3612", "6519", "6520"}:
            # CAS replacement of the superseded 12-unit value (wrong axis, #910).
            assert change["expect"] == {"value": "12", "unit": "units"}, key
        else:
            assert change["expect"] is None, key
        assert source["page"] == citation["page"]
        assert citation["url"].startswith("https://de-linker.com/wp-content/uploads/")
        assert source["quote"].strip(), key
        assert len(source["blob_sha256"]) == 64
        assert len(source["document_revision"]) == 64


def test_every_limit_quote_appears_on_the_page_it_cites() -> None:
    plan = json.loads(PLAN.read_text())
    excerpts = json.loads(EXCERPTS.read_text())
    for key, row in plan["products"].items():
        source = row["figures"]["stacks_parallel_max"]["source"]
        document = excerpts["documents"].get(source["document_id"])
        assert document is not None, key
        assert document["blob_sha256"] == source["blob_sha256"], key
        page = document["pages"].get(str(source["page"]))
        assert page is not None, key
        assert not _absent_words(source["quote"], page), key


def _absent_words(quote: str, page: str) -> list[str]:
    """Words of the quote that do not appear on the page, ignoring line wrapping."""

    def squash(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    flat = squash(page)
    return [
        word
        for word in quote.split()
        if len(re.sub(r"[^A-Za-z0-9]", "", word)) >= 3 and squash(word) not in flat
    ]


def test_no_limit_is_invented_for_a_product_without_its_own_statement() -> None:
    plan = json.loads(PLAN.read_text())
    for key in NOT_WRITTEN:
        assert key not in plan["products"], key
    joined = " ".join(f"{key} {value}" for key, value in plan["unbound"].items())
    # Every limit this batch declined to write names the reason it stayed out.
    assert "15 inverters" in joined
    assert "CH2" in joined
    assert "HS3" in joined
    assert "BAT-S" in joined
    # 6521/6522 moved from unbound into products: the ESA user manual V1.5 is
    # mounted on them and prints the 3-expansion-group limit for the family.


def test_the_engine_reads_the_same_figure_key() -> None:
    plan = json.loads(PLAN.read_text())
    assert {field for row in plan["products"].values() for field in row["figures"]} == {
        "stacks_parallel_max"
    }


def test_plan_rejects_an_unreviewed_path(tmp_path: Path) -> None:
    migration = load_migration()
    broken = json.loads(PLAN.read_text())
    next(iter(broken["products"].values()))["figures"]["stacks_parallel_max"]["set"][
        "citation"
    ]["url"] = "https://example.com/x.pdf"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(migration.MigrationError):
        migration.load_plan(path)


def test_plan_rejects_a_missing_source_quote(tmp_path: Path) -> None:
    migration = load_migration()
    broken = json.loads(PLAN.read_text())
    next(iter(broken["products"].values()))["figures"]["stacks_parallel_max"]["source"][
        "quote"
    ] = " "
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(broken))
    with pytest.raises(migration.MigrationError):
        migration.load_plan(path)


def test_a_preview_request_carries_the_plan_and_apply_carries_the_receipt() -> None:
    migration = load_migration()
    plan = migration.load_plan()
    assert migration.build_request("preview", plan=plan) == {
        "action": "preview",
        "plan": plan,
    }
    receipt = {"site": "https://de-linker.com", "products": {"1956": {}}}
    assert migration.build_request("apply", receipt=receipt) == {
        "action": "apply",
        "receipt": receipt,
    }
    with pytest.raises(migration.MigrationError):
        migration.build_request("apply", plan=plan)
    with pytest.raises(migration.MigrationError):
        migration.build_request("preview", receipt=receipt)


def test_the_php_side_declares_one_payload_and_one_marker() -> None:
    source = (HERE.parent / "548-battery-parallel-limits.php").read_text()
    assert source.count("'548-battery-parallel-limits-payload'") == 1
    assert "@@548-battery-parallel-limits@@" in source
    assert "FIGURES_META_KEY" in source
    assert "wp_slash" in source
    assert "Readback failed" in source


def test_preview_writes_a_private_receipt_and_prints_one_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    migration = load_migration()
    receipt = tmp_path / "receipt"
    payload: dict[str, Any] = {}

    def transport(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        source = kwargs["input"]
        assert isinstance(source, str)
        match = re.search(r"'([A-Za-z0-9+/=]{100,})'", source)
        assert match is not None
        payload.update(json.loads(base64.b64decode(match[1])))
        result = {
            "schema_version": 1,
            "site": "https://de-linker.com",
            "products": {"1956": {"model": "GW208.9-BAT-LC-G10"}},
            "changes": 8,
            "source_revision": "a" * 64,
        }
        return subprocess.CompletedProcess(
            command, 0, migration.MARKER + json.dumps(result), ""
        )

    monkeypatch.setattr(migration.subprocess, "run", transport)
    monkeypatch.setattr(
        migration, "remote_target", lambda: _target("https://de-linker.com")
    )
    monkeypatch.setattr(
        migration.sys,
        "argv",
        ["migration", "--production", "preview", "--receipt", str(receipt)],
    )
    assert migration.main() == 0
    assert payload["action"] == "preview"
    assert payload["plan"] == migration.load_plan()
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    assert json.loads(receipt.read_text())["changes"] == 8
    assert json.loads(capsys.readouterr().out.strip()) == {
        "action": "preview",
        "site": "https://de-linker.com",
        "changes": 8,
        "source_revision": "a" * 64,
    }


def test_cli_preview_refuses_to_shadow_an_existing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    migration = load_migration()
    receipt = tmp_path / "receipt"
    receipt.write_text("{}")
    monkeypatch.setattr(
        migration.sys,
        "argv",
        ["migration", "--production", "preview", "--receipt", str(receipt)],
    )
    with pytest.raises(SystemExit) as exc:
        migration.main()
    assert exc.value.code == 2
    assert receipt.read_text() == "{}"


def _target(site: str) -> Any:  # minimal transport double
    from linker_cutover.target import (  # type: ignore[import-not-found]
        Target,
    )

    return Target("fixture", "/fixture", site, ("wp",), None, None)
