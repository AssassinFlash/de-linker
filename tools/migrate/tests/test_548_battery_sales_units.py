"""Local contract tests for the guarded #548 battery sales-unit migration."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

HERE = Path(__file__).resolve().parent

# The excluded-by-design control module (draft docs/acceptance/2026-11-03/548/
# evidence/sales-unit-draft.json) must never gain an entry.
POOL = {
    "1832",
    "2067",
    "2068",
    "2069",
    "2070",
    "4103",
    "4104",
    "4105",
    "4106",
    "2090",
    "2093",
    "3611",
    "3612",
    "6519",
    "6520",
    "6521",
    "6522",
}
SALES_UNIT = {
    "1832": "battery_system",
    "2067": "battery_system",
    "2068": "battery_system",
    "2069": "battery_system",
    "2070": "battery_system",
    "4103": "battery_system",
    "4104": "battery_system",
    "4105": "battery_system",
    "4106": "battery_system",
    "2090": "battery_module",
    "2093": "battery_module",
    "3611": "battery_module",
    "3612": "battery_module",
    "6519": "battery_module",
    "6520": "battery_module",
    "6521": "battery_module",
    "6522": "battery_module",
}
MODULES_PER_SALES_UNIT = {
    "1832": 1,
    "2067": 2,
    "2068": 3,
    "2069": 4,
    "2070": 5,
    "4103": 4,
    "4104": 5,
    "4105": 6,
    "4106": 7,
}
PRODUCT_REVISIONS = {
    "1832": "42877aece6adcf49349bad7e3ca22c3fbcaf4e69864718683fc1f1dd7ec1fb70",
    "2067": "81e0658a21b984008531d9f919f7868fa508817d9383874af918b4d3fd17e742",
    "2068": "b91f8897cdbd3e46e033e49f868216fb4ff6fff177502aa5292c4d350256740d",
    "2069": "65a741b4511dc53a0fcff8ca0a2cc0eeb8dbad548270a156de8c96163ca3d2cd",
    "2070": "d22d846475575a9182400e2c6a02a42ab1aa504367947e9695884d4978672ede",
    "2090": "7ef533314f23c57b4762418b665d639501bb4b64b76c6bd831d48ec7887cb2a3",
    "2093": "10f38f4819946de814d24f378ba5a022169dca7f33fd2e7e2728a94508add257",
    "3611": "21ec761399ec8beeb483e8f0b6021e8d73aef5a0835e270aea704aa834ef8833",
    "3612": "fff0934583f9342cca78cb43ef9180378782a8cf785eaa7db41f3012f049507a",
    "4103": "c5b70c0960b29c593e185222e4b66226d397ed43de5fa61ea91aa97a4fca765f",
    "4104": "54fd89f5d0de731c020628455d6a3418f7ebb5f5f1912d86341dcd67dd1eee7a",
    "4105": "cdfcb04ca728c2b9b32d972acf162fe4334b1b2b88017c06b6a93b0437168e59",
    "4106": "6ad1407147bc8c8002508b989e1fdf8b6c2bcfbc9c63f43d22555c7136081010",
    "6519": "e3566437d53846acad4ca5a5b50c419d33364e598872b99061b01305503269e5",
    "6520": "cad9a33a067513d9593b0414b8231faa1359f237746833b13fd89d45e98b1782",
    "6521": "d9b8c9d0f7ea9a73284a7fc6a2d6341ede50c907e2cfd0d3fdc015d1fdc7e9c9",
    "6522": "8fbec19aeb77967ff92e73fd65410aec7c399aec41add77731f59b523230f9a4",
}
# Cited manufacturer originals (production feed, read 2026-11-03).
DOCUMENTS = {
    "doc-2a01f2dd8ad8ee475603e0643a7e1a2d10810917a5367c84ed0dd7cc1950a904": (
        "02d20e0d3ef6a38fc484e5ff72676b176baa4c26b9356993a0f41fe74cb41758",
        "74d86778ee033622d64deeb3bc2f0017e814f1cecd3a484c491c939be9529a2a",
    ),
    "doc-595423f7b5faeafeeb9e81ff2c54f75dcdb99fc0546e063bc86f02258f6fb1fe": (
        "2977d5d0acddc95aca69569fa9d8ee285d4a881be8c15d4d4f1c9c0b28a6a3ee",
        "31e69160217850be491a5b7ab31dae2bbf17ec33723c0368a1aec4d751c04ab9",
    ),
    "doc-62719ddebe0f8a4b3f070630ac3824f78b75e4cb60f416a64b66eb3c6953074a": (
        "cfcb53a726f19fb059ea48b534fcd4fa85f3a27081d76780b034672444b8259a",
        "ee6b3a41b8250367c67e285e5d69c15f19981eda3d83fdd476226393cb38cff5",
    ),
    "doc-a7cfa5ad5c55cfba8128f3992a05ac5cb86138460b1e9dcbea4fd833142abdf7": (
        "50f227b4ca819bc905bda317c96e5b0cfbab936e282dd03c04a0372498ddc695",
        "67a7f715ca9db734edba1b4f15b50d1a29c866b172ffd1909759e0abc66c8d2a",
    ),
    "doc-df9998a7bef786ff08b6d70159531e8909358c27caf0495be7527d80596ac2e1": (
        "986f14b06c28f467102c39c51153ad0b8d580ee7808898c9ae3bdea4795be2c4",
        "c68e43b669c1dad71c56a25455613036eca2991ea8f3a67ca9a5867843613603",
    ),
}


def load_plan() -> dict[str, Any]:
    plan = json.loads((HERE.parent / "548-battery-sales-units.json").read_text())
    assert isinstance(plan, dict)
    return plan


def load_migration() -> Any:
    spec = importlib.util.spec_from_file_location(
        "battery_sales_units_migration", HERE.parent / "548-battery-sales-units.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reviewed_plan_is_frozen() -> None:
    plan = load_plan()
    assert plan["schema_version"] == 1
    assert plan["kind"] == "battery_sales_unit_v1"
    assert "2092" not in plan["products"]
    assert set(plan["products"]) == POOL
    assert {pid: row["product_revision"] for pid, row in plan["products"].items()} == (
        PRODUCT_REVISIONS
    )
    cited: dict[str, tuple[str, str]] = {}
    for pid, row in plan["products"].items():
        basis = row["basis"]
        assert row["conditions"] == []
        assert basis["sales_unit"] == SALES_UNIT[pid]
        assert basis.get("modules_per_sales_unit") == MODULES_PER_SALES_UNIT.get(pid)
        assert re.fullmatch(r"[a-f0-9]{64}", basis["document_revision"])
        cited[basis["document_id"]] = (
            basis["document_revision"],
            basis["blob_sha256"],
        )
        figure = row["figures"]["sales_unit_kind"]
        assert figure["expect"] is None
        assert figure["set"] == {
            "value": SALES_UNIT[pid],
            "unit": None,
            "citation": {"url": basis["url"], "page": basis["page"]},
        }
        assert row["documents"] == {basis["document_id"]: basis["blob_sha256"]}
    assert cited == DOCUMENTS
    stripped = json.loads(json.dumps(plan))
    for row in stripped["products"].values():
        row.pop("product_revision")
        row["basis"].pop("document_revision")
    canonical = json.dumps(
        stripped, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert hashlib.sha256(canonical.encode()).hexdigest() == (
        "ef3a91dbde68c238dc91bfc7226092445c1f5f671aed2cc57a896f574c814d4e"
    )


def test_cli_preview_ships_reviewed_plan_and_writes_private_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    migration = load_migration()
    observed: dict[str, Any] = {}

    def transport(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        source = kwargs["input"]
        assert isinstance(source, str)
        encoded = re.search(r"'([A-Za-z0-9+/=]{100,})'", source)
        assert encoded is not None
        request = json.loads(base64.b64decode(encoded[1]))
        observed["request"] = request
        observed["php"] = source
        payload = {
            "site": "https://de-linker.com",
            "products": {},
            "changes": 17,
            "source_revision": "a" * 64,
        }
        return subprocess.CompletedProcess(
            command, 0, migration.MARKER + json.dumps(payload), ""
        )

    monkeypatch.setattr(migration.subprocess, "run", transport)
    monkeypatch.setattr(
        migration,
        "remote_target",
        lambda: observed.setdefault("target", _target("https://de-linker.com")),
    )
    receipt = tmp_path / "receipt"
    monkeypatch.setattr(
        migration.sys,
        "argv",
        ["migration", "--production", "preview", "--receipt", str(receipt)],
    )
    assert migration.main() == 0
    # The transport receives the reviewed plan verbatim and the guarded PHP.
    assert observed["request"]["action"] == "preview"
    assert observed["request"]["plan"] == load_plan()
    assert observed["php"].startswith("<?php")
    assert "WP_CLI::error" in observed["php"]
    assert stat.S_IMODE(receipt.stat().st_mode) == 0o600
    saved = json.loads(receipt.read_text())
    assert saved["site"] == "https://de-linker.com"
    assert saved["changes"] == 17
    summary = json.loads(capsys.readouterr().out.strip())
    assert summary == {
        "action": "preview",
        "site": "https://de-linker.com",
        "changes": 17,
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


def _target(site: str):  # noqa: ANN202 - minimal transport double
    # The migration module registered linker_cutover on sys.path at import.
    from linker_cutover.target import (  # type: ignore[import-not-found]
        Target,
    )

    return Target("fixture", "/fixture", site, ("wp",), None, None)
