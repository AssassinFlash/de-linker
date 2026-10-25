"""One real Woo rehearsal of fact binding, preparation, idempotence and rollback.

Run only against this ticket's isolated, pre-repair live snapshot instance:
PHP=/opt/homebrew/opt/php@8.3/bin/php LINKER_MIGRATE_TEST_INSTANCE=dc615
uv run --project tools/migrate pytest tests/test_615_dc_figures_wordpress.py
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "615-dc-figures.py"
INSTANCE = os.environ.get("LINKER_MIGRATE_TEST_INSTANCE", "")
pytestmark = pytest.mark.skipif(
    not INSTANCE, reason="Requires an isolated Woo snapshot."
)


def test_native_preparation_and_guarded_recovery(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("dc_migration", SCRIPT)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    site = migration.local_target(INSTANCE)
    receipt = tmp_path / "receipt.json"

    def run(action: str, path: Path = receipt) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--instance",
                INSTANCE,
                action,
                "--receipt",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def state() -> dict[str, Any]:
        data: dict[str, Any] = json.loads(
            site.wp(
                "eval",
                'echo wp_json_encode(["feed"=>Linker\\Commerce\\Products\\EngineeringFeed::feed(),"pending"=>get_option("linker_publication_pending"),"jobs"=>get_option("linker_publication_jobs"),"raw"=>get_post_meta(4107,Linker\\Commerce\\Products\\SelectionFacts::FIGURES_META_KEY,true)]);',
            )
        )
        return data

    def set_h2(raw: str) -> None:
        encoded = base64.b64encode(raw.encode()).decode()
        site.wp(
            "eval",
            f'update_post_meta(4107,Linker\\Commerce\\Products\\SelectionFacts::FIGURES_META_KEY,wp_slash(base64_decode("{encoded}")));',
        )

    preview = run("preview")
    assert preview.returncode == 0, preview.stderr
    before = json.loads(receipt.read_text())
    assert before["changes"] == 3, "Rehearse against the original Woo facts."
    applied = run("apply")
    assert applied.returncode == 0, applied.stderr
    loaded = state()
    feed = loaded["feed"]
    assert feed["source_revision"] != before["source_revision"]
    assert feed["figure_projection_version"] == 2
    products = {p["id"]: p for p in feed["products"]}
    plan = json.loads(SCRIPT.with_suffix(".json").read_text())
    for product_id, patch in plan["products"].items():
        product = products[int(product_id)]
        documents = {d["document_id"]: d for d in product["documents"]}
        for key, change in patch["figures"].items():
            # Presence proves the native current-source binding passed Publication.
            figure = product["figures"][key]
            for field, expected in change["set"].items():
                assert figure[field] == expected
            assert any(
                d["url"] == figure["citation"]["url"] for d in documents.values()
            )
    assert loaded["pending"] or any(
        j.get("source_revision") == feed["source_revision"]
        for j in loaded["jobs"].values()
    )
    repeated = run("apply")
    assert repeated.returncode == 0, repeated.stderr
    assert json.loads(repeated.stdout)["changes"] == 0
    assert state()["feed"]["source_revision"] == feed["source_revision"]
    clean_preview = run("preview", tmp_path / "done.json")
    assert clean_preview.returncode == 0, clean_preview.stderr
    assert json.loads((tmp_path / "done.json").read_text())["changes"] == 0

    # A later real Woo edit must block recovery, leaving that edit intact.
    edited = json.loads(loaded["raw"])
    edited["max_battery_charge_a"]["qualifier"]["scope"] = "synthetic_later_edit"
    edited_raw = json.dumps(edited, ensure_ascii=False, separators=(",", ":"))
    set_h2(edited_raw)
    try:
        rejected = run("rollback")
        assert rejected.returncode != 0
        assert "Concurrent edit" in rejected.stderr
        assert state()["raw"] == edited_raw
    finally:
        set_h2(loaded["raw"])
    recovered = run("rollback")
    assert recovered.returncode == 0, recovered.stderr
    assert state()["raw"] == before["products"]["4107"]["before"]
    # Leave the current source facts ready for the strict consumer/readback.
    final = run("apply")
    assert final.returncode == 0, final.stderr
