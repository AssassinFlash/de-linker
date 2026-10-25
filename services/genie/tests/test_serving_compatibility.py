"""A real persisted generation cannot bypass upgraded applicability rules."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from test_publication import authority
from test_publication_compiler import H2_DE, compiled_index, manifest

from linker_genie.knowledge import KnowledgeSearch, KnowledgeUnavailable
from linker_genie.preparation import RUNTIME_SERVING_REVISION
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex


def managed_index(path: Path, expected: str) -> DocumentIndex:
    original = compiled_index(path, H2_DE[:12])
    original.close()
    target = path / "index.sqlite"
    with sqlite3.connect(target) as db:
        db.executemany(
            "UPDATE meta SET value=? WHERE key=?",
            [("b" * 64, "recipe_revision"), (expected, "serving_revision")],
        )
    return DocumentIndex(target, encoder=None)


@pytest.mark.parametrize("expected", ["previous-serving-rules", ""])
def test_mismatched_managed_generation_is_readable_only_for_repair(
    tmp_path: Path, expected: str
) -> None:
    index = managed_index(tmp_path, expected)
    snapshot = Snapshot.read(manifest())
    try:
        # Activation needs this endpoint to load the matching replacement.
        receipt = index.loaded()
        assert receipt["expected_serving_revision"] == expected
        assert receipt["serving_revision"] == RUNTIME_SERVING_REVISION
        with pytest.raises(RuntimeError, match="serving rules"):
            index.search("Nennleistung AC", "en", [1179], publication=snapshot)
        with pytest.raises(RuntimeError, match="serving rules"):
            index.permissions(snapshot, [1179])
        # Omitting the current snapshot cannot reopen the old proof generation.
        with pytest.raises(RuntimeError, match="serving rules"):
            index.search("Nennleistung AC", "en")
        search = KnowledgeSearch(lambda: index, authority(manifest()))
        with pytest.raises(KnowledgeUnavailable, match="serving rules"):
            search({"query": "Nennleistung AC", "lang": "en", "product_ids": [1179]})
    finally:
        index.close()


def test_matching_managed_generation_uses_current_original_evidence(
    tmp_path: Path,
) -> None:
    index = managed_index(tmp_path, RUNTIME_SERVING_REVISION)
    try:
        hits = index.search(
            "Nennleistung AC", "en", [1179], publication=Snapshot.read(manifest())
        )
        assert any("| Nennleistung AC [W] | 25000 |" in hit.text for hit in hits)
        assert index.permissions(Snapshot.read(manifest()), [1179])
    finally:
        index.close()
