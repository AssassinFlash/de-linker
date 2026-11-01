"""Reviewed HCA migration plan must preserve every unrelated source field."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.mark.parametrize("partial", [b"", b"reviewed", b"reviewed PDF bytes"])
def test_native_file_stage_without_hard_links(tmp_path: Path, partial: bytes) -> None:
    php = shutil.which("php")
    if php is None:
        pytest.skip("PHP is required for the native migration stage")
    source = (Path(__file__).resolve().parents[1] / "548-hca-warranty.php").read_text()
    stage = source.split("$partial = $path . '.partial';", 1)[1].split(
        "if ( ! $attachment_id ) {", 1
    )[0]
    body = b"reviewed PDF bytes"
    final = tmp_path / "reviewed.pdf"
    temporary = tmp_path / "reviewed.pdf.partial"
    temporary.write_bytes(partial)
    program = (
        "$path = $argv[1]; $partial = $path . '.partial'; "
        "$bytes = 'reviewed PDF bytes'; $new_sha = hash('sha256', $bytes); "
        + stage
    )

    def run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [php, "-d", "disable_functions=link", "-r", program, "--", str(final)],
            text=True,
            capture_output=True,
            check=False,
        )

    result = run()
    assert result.returncode == 0, result.stderr
    assert final.read_bytes() == body and not temporary.exists()
    assert run().returncode == 0
    final.write_bytes(b"another owner's file")
    assert run().returncode != 0
    assert final.read_bytes() == b"another owner's file"


def load_migration() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "548-hca-warranty-plan.py"
    spec = importlib.util.spec_from_file_location("hca_warranty", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source_and_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModuleType, Path, dict[str, Any]]:
    module = load_migration()
    pdf = tmp_path / "source.pdf"
    pdf.write_bytes(b"reviewed source bytes")
    monkeypatch.setattr(
        module, "SOURCE_SHA256", hashlib.sha256(pdf.read_bytes()).hexdigest()
    )
    products: dict[str, Any] = {}
    for en, de in module.PRODUCTS.items():
        for pid, language in ((en, "en"), (de, "de")):
            products[str(pid)] = {
                "woo_fields": {
                    "canonical_id": en,
                    "product_id": pid,
                    "actual_language": language,
                    "translation_en": en,
                    "translation_de": de,
                    "status": "publish",
                }
            }
        rows = [
            {
                "url": f"https://de-linker.com/wp-content/uploads/unchanged-{i}.pdf",
                "title": f"original {i}",
                "type": "manual",
                "lang": "EN",
            }
            for i in range(7)
        ]
        rows.insert(
            3, {"url": module.OLD_URL, "title": "old", "type": "warranty", "lang": "EN"}
        )
        downloads = [
            {"download_file": i + 100, "download_title": f"keep {i}"} for i in range(7)
        ]
        downloads.insert(
            2,
            {
                "download_file": 6426,
                "download_language": "EN",
                "download_role": "document",
            },
        )
        acf = json.dumps({"downloads": downloads, "other": {"unchanged": [1, 2]}})
        products[str(en)].update(
            {
                "documents_decoded": rows,
                "metadata": {
                    "_linker_documents_managed": ["1"],
                    "_tv_legacy_acf_json": [acf],
                    "_linker_de_acf_json": [acf],
                },
            }
        )
    return (
        module,
        pdf,
        {
            "site": "https://de-linker.com/",
            "captured_utc": "2026-11-01T12:38:00+00:00",
            "products": products,
            "media": {"6426": {"url": module.OLD_URL}},
        },
    )


def test_plan_changes_only_the_reviewed_warranty_row(
    source_and_snapshot: tuple[ModuleType, Path, dict[str, Any]],
) -> None:
    module, pdf, snapshot = source_and_snapshot
    plan = module.prepare(snapshot, pdf)
    assert len(plan["changes"]) == 9
    for change in plan["changes"]:
        before, after = change["before"], change["after"]
        if change["meta_key"] == "_linker_documents":
            assert len(before) == len(after) == 8
            assert all(before[i] == after[i] for i in range(8) if i != 3)
        else:
            assert before["other"] == after["other"]
            assert all(
                before["downloads"][i] == after["downloads"][i]
                for i in range(8)
                if i != 2
            )
            assert after["downloads"][2]["download_file"] == module.MEDIA_ID_PENDING


def test_refuses_ambiguous_old_document_and_changed_source(
    source_and_snapshot: tuple[ModuleType, Path, dict[str, Any]],
) -> None:
    module, pdf, snapshot = source_and_snapshot
    snapshot["products"]["3557"]["documents_decoded"].append(
        snapshot["products"]["3557"]["documents_decoded"][3].copy()
    )
    with pytest.raises(ValueError, match="exactly one old policy"):
        module.prepare(snapshot, pdf)
    pdf.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="source PDF bytes"):
        module.prepare(snapshot, pdf)
