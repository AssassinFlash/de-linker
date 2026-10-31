"""The actual compiler recipe, independent of a Woo edit or installation path."""

from pathlib import Path

import pytest

from index import corpus, store
from index.corpus import DocumentRow
from index.preparation import recipe_revision
from linker_genie.preparation import RUNTIME_SERVING_REVISION, serving_revision
from linker_genie.retrieval import DocumentIndex


def fixture(root: Path) -> None:
    (root / "index").mkdir(parents=True)
    (root / "ops").mkdir()
    (root / "src/linker_genie").mkdir(parents=True)
    (root / "index/build.py").write_text("compiler = 1\n")
    (root / "ops/publication_worker.py").write_text("prepare = 1\n")
    (root / "src/linker_genie/publication_scope.py").write_text("scope = 1\n")
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    (root / "uv.lock").write_text("version = 1\n")


def test_recipe_ignores_host_path_and_rebuildable_outputs(tmp_path: Path) -> None:
    first, second = tmp_path / "one", tmp_path / "elsewhere/two"
    for root in (first, second):
        fixture(root)
    revision = recipe_revision(first)
    assert len(revision) == 64
    assert revision == recipe_revision(second)
    (first / "index/__pycache__").mkdir()
    (first / "index/__pycache__/build.pyc").write_bytes(b"compiled cache")
    (first / "index/parsed.json").write_text("temporary output")
    assert revision == recipe_revision(first)


def test_recipe_automatically_tracks_new_compiler_modules_and_locked_dependencies(
    tmp_path: Path,
) -> None:
    fixture(tmp_path)
    revision = recipe_revision(tmp_path)
    (tmp_path / "index/table_projection.py").write_text("projection = 1\n")
    upgraded = recipe_revision(tmp_path)
    assert upgraded != revision
    (tmp_path / "uv.lock").write_text("version = 2\n")
    assert recipe_revision(tmp_path) != upgraded


def test_recipe_tracks_serving_applicability_code(tmp_path: Path) -> None:
    fixture(tmp_path)
    revision = recipe_revision(tmp_path)
    (tmp_path / "src/linker_genie/publication_scope.py").write_text("scope = 2\n")
    assert recipe_revision(tmp_path) != revision
    upgraded = recipe_revision(tmp_path)
    (tmp_path / "src/linker_genie/new_scope_helper.py").write_text("proof = 1\n")
    assert recipe_revision(tmp_path) != upgraded


def test_quality_delivery_changes_do_not_rebuild_or_relabel_knowledge(
    tmp_path: Path,
) -> None:
    fixture(tmp_path)
    before = recipe_revision(tmp_path), serving_revision(tmp_path)
    quality = tmp_path / "src/linker_genie/quality"
    quality.mkdir()
    for filename in ("worker.py", "store.py", "wordpress.py"):
        (quality / filename).write_text("delivery = 1\n")
    assert (recipe_revision(tmp_path), serving_revision(tmp_path)) == before
    (quality / "store.py").write_text("delivery = 2\n")
    assert (recipe_revision(tmp_path), serving_revision(tmp_path)) == before
    # A new runtime helper with quality in its name is still a real serving input.
    (tmp_path / "src/linker_genie/quality_gate.py").write_text("proof = 1\n")
    assert recipe_revision(tmp_path) != before[0]
    assert serving_revision(tmp_path) != before[1]


def test_serving_revision_is_actual_code_and_locked_inputs_independent_of_path(
    tmp_path: Path,
) -> None:
    one, two = tmp_path / "one", tmp_path / "elsewhere/two"
    fixture(one)
    fixture(two)
    actual = serving_revision(one)
    assert serving_revision(two) == actual
    (one / "src/linker_genie/another_runtime.py").write_text("proof = 2\n")
    assert serving_revision(one) != actual


@pytest.mark.parametrize("status", ["indexed", "failed"])
def test_materialization_is_independent_of_proven_coverage(
    tmp_path: Path, status: str
) -> None:
    sha, recipe = "b" * 64, "a" * 64
    manifest = {
        "schema_version": 1,
        "source_revision": "woo-source",
        "products": [{"product_id": 1, "product_revision": "p1", "documents": ["doc"]}],
        "documents": [
            {
                "document_id": "doc",
                "document_revision": "d1",
                "blob_sha256": sha,
                "product_ids": [1],
            }
        ],
    }
    directory = tmp_path / "corpus"
    corpus.write(
        directory,
        corpus.Meta(
            "generation-1",
            None,
            None,
            "fixture",
            256,
            publication={"manifest": manifest},
            recipe_revision=recipe,
            serving_revision="claimed-new-serving-code",
        ),
        [
            DocumentRow(
                sha,
                ("https://site.test/manual.pdf",),
                "Manual",
                "Handbuch",
                (),
                (),
                "manual",
                "en",
                1,
                status,
            )
        ],
        [(1, "MODEL-1")],
        [],
    )
    target = tmp_path / "index.sqlite"
    store.export(directory, target)
    index = DocumentIndex(target)
    try:
        loaded = index.loaded()
        assert loaded["recipe_revision"] == recipe
        assert loaded["expected_serving_revision"] == "claimed-new-serving-code"
        assert loaded["serving_revision"] == RUNTIME_SERVING_REVISION
        assert loaded["serving_revision"] != loaded["expected_serving_revision"]
        assert loaded["index_version"] == "generation-1"
        assert loaded["materialization_complete"] is (status == "indexed")
        assert loaded["preparation_complete"] is False
        assert loaded["products"] == []
        assert loaded["unprepared_documents"] == [
            {
                "document_id": "doc",
                "product_id": 1,
                "reason": "no_proven_passage"
                if status == "indexed"
                else "document_unparsed",
            }
        ]
    finally:
        index.close()
