"""The #339 fixture lists every regraded defect and parity row."""

from __future__ import annotations

import json
from pathlib import Path

import regrade

MANIFEST = Path(__file__).resolve().parents[1] / "fixtures" / "339" / "manifest.json"


def test_manifest_covers_overturns_and_kept_defects() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert payload["ticket"] == 339
    cases = payload["cases"]
    assert isinstance(cases, list)
    ids = {str(item["id"]) for item in cases}
    assert set(regrade.OVERTURNS) | set(regrade.KEPT_DEFECTS) <= ids
    for item in cases:
        assert item["issue"] == 330
        assert item["campaign"] == "330"
        assert str(item["evidence"]).endswith("#" + str(item["id"]))
        assert item["grade"] in {"defect", "parity"}


def test_round3_defect_and_parity_rows_are_registered() -> None:
    runs = Path(__file__).resolve().parents[2] / "round3-runs.jsonl"
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ids = {str(item["id"]) for item in payload["cases"]}
    seen = False
    for line in runs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["grade"] in {"defect", "parity"}:
            seen = True
            assert row["id"] in ids
    assert seen
