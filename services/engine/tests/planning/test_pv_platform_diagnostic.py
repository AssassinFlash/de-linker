"""Temporary platform diagnostic for the actual exported PV witness."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import cast
from unittest.mock import patch

from linker_engine.planning.canonical import Json, decode_object
from linker_engine.planning.pv_generation import PvGeneration

from . import export_preparation_fixture

BASELINE = Path(__file__).resolve().parents[1] / "fixtures" / "pv-platform-witness.json"


def capture_witness() -> tuple[dict[str, Json], dict[str, Json]]:
    witnesses: list[bytes] = []
    original = PvGeneration

    def record(
        profile: object, inputs_json: bytes, witness_json: bytes
    ) -> PvGeneration:
        witnesses.append(witness_json)
        return original(profile, inputs_json, witness_json)  # type: ignore[arg-type]

    with patch("linker_engine.planning.pv_generation.PvGeneration", record):
        document = export_preparation_fixture.capture()
    assert len(witnesses) == 1
    return document, decode_object(witnesses[0])


def differences(
    expected: Json, actual: Json, path: str = ""
) -> list[tuple[str, Json, Json]]:
    if type(expected) is not type(actual):
        return [(path, expected, actual)]
    if isinstance(expected, dict) and isinstance(actual, dict):
        return [
            row
            for key in sorted(expected.keys() | actual.keys())
            for row in differences(
                expected.get(key), actual.get(key), path + "/" + str(key)
            )
        ]
    if isinstance(expected, list) and isinstance(actual, list):
        rows = (
            [] if len(expected) == len(actual) else [(path, len(expected), len(actual))]
        )
        return rows + [
            row
            for index, (left, right) in enumerate(zip(expected, actual, strict=False))
            for row in differences(left, right, path + "/" + str(index))
        ]
    return [] if expected == actual else [(path, expected, actual)]


def test_actual_witness_platform_differences() -> None:
    document, actual = capture_witness()
    if os.environ.get("CI") == "true":
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True).encode()
        packed = gzip.compress(raw, mtime=0)
        print("PV_PLATFORM_DOCUMENT_SHA256", hashlib.sha256(raw).hexdigest())
        print("PV_PLATFORM_DOCUMENT", base64.b64encode(packed).decode())
    if os.environ.get("LINKER_PV_PLATFORM_WRITE") == "1":
        BASELINE.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + "\n")
    expected = cast(dict[str, Json], json.loads(BASELINE.read_text()))
    changed = differences(expected, actual)
    for path, before, after in changed[:40]:
        print(
            "PV_PLATFORM_DIFF",
            path,
            repr(before),
            repr(after),
            before.hex() if isinstance(before, float) else "",
            after.hex() if isinstance(after, float) else "",
        )
    print("PV_PLATFORM_DIFF_COUNT", len(changed))
    assert not changed
