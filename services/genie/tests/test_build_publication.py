"""Real model-column compilation precedes vectors and survives index export."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from test_build import CountingEmbedder
from test_chunking import Words
from test_publication import authority
from test_publication_compiler import H2_DE, chunks, manifest

from index import build as builder
from index import corpus
from index.corpus import DocumentRow
from index.preparation import recipe_revision
from linker_genie.embedding import Passage
from linker_genie.preparation import serving_revision
from linker_genie.publication import Snapshot
from linker_genie.retrieval import DocumentIndex


class CapturingEmbedder(CountingEmbedder):
    def __init__(self) -> None:
        super().__init__()
        self.passages: list[Passage] = []

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        self.passages.extend(passages)
        return super().embed_documents(passages)


def actual_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, deadlines: list[int] | None = None
) -> Path:
    raw = manifest()
    document = next(d for d in raw["documents"] if d["blob_sha256"] == H2_DE)
    selected = chunks(H2_DE[:12])
    row = DocumentRow(
        H2_DE,
        (document["url"],),
        document["title"],
        "",
        (),
        (),
        "datasheet",
        "de",
        2,
        "indexed",
    )
    original = builder.Chunked(
        [row],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        selected,
        [],
        {"original Docling"},
        0.0,
    )
    # The compiler/runtime tests exercise extraction of the native original.
    # Here the seam under test is compile -> embed -> SQLite, using those exact cells.
    monkeypatch.setattr(builder, "chunk_all", lambda *_: original)

    def publication_client(_source: str, **options: int) -> object:
        if deadlines is not None:
            deadlines.append(options["identify_deadline"])
        return authority(raw)

    monkeypatch.setattr(
        "linker_genie.publication.PublicationClient", publication_client
    )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps({"source": "https://site.test", "publication_manifest": raw})
    )
    return inventory


def test_current_model_projections_are_embedded_before_store_and_answer_the_right_column(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    deadlines: list[int] = []
    inventory = actual_input(tmp_path, monkeypatch, deadlines)
    embedder = CapturingEmbedder()
    directory = builder.build(
        inventory,
        tmp_path,
        tmp_path,
        tmp_path / "out",
        embedder,
        Words(),
        lambda _: "de",
        activation_epoch=23,
        publication_deadline=2_000_000_000,
    )
    assert deadlines == [2_000_000_000]
    output = capsys.readouterr().out
    for phase in ("chunk", "compile", "embed", "store"):
        for event in ("start", "done"):
            assert f'"phase": "{phase}", "event": "{event}"' in output
    meta = corpus.read_meta(directory / "corpus")
    rows = list(corpus.read_chunks(directory / "corpus"))
    assert meta.recipe_revision == recipe_revision()
    assert meta.serving_revision == serving_revision()
    assert meta.activation_epoch == 23
    assert len(embedder.passages) == len(rows)
    assert all(vector is not None for _, vector in rows)
    projected_ids = {
        cid
        for cid, scope in meta.publication["chunk_scopes"].items()
        if scope["basis"] == "table_projection" and scope["product_ids"] == [1179]
    }
    projected = [chunk for chunk, _ in rows if chunk.id in projected_ids]
    assert any("| Nennleistung AC [W] | 25000 |" in c.text for c in projected)
    assert any(
        "| Nennleistung AC [W] | 25000 |" in p.text and "H2-30K-T3" not in p.text
        for p in embedder.passages
    )
    report = json.loads((directory / "manifest.json").read_text())
    assert report["permission_coverage"]["projected_chunks"] > 0
    assert report["chunks"] == len(rows)
    with_index = DocumentIndex(directory / "index.sqlite", encoder=None)
    try:
        loaded = with_index.loaded()
        assert loaded["activation_epoch"] == 23
        assert loaded["recipe_revision"] == meta.recipe_revision
        hits = with_index.search(
            "Nennleistung AC", "de", [1179], publication=Snapshot.read(manifest())
        )
        assert any("| Nennleistung AC [W] | 25000 |" in h.text for h in hits)
        assert all("H2-30K-T3" not in h.text for h in hits)
    finally:
        with_index.close()


def test_code_changed_mid_build_never_receives_a_publishable_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = actual_input(tmp_path, monkeypatch)
    revisions = iter(["before", "after"])
    monkeypatch.setattr(builder, "recipe_revision", lambda: next(revisions))
    with pytest.raises(RuntimeError, match="code changed"):
        builder.build(
            inventory,
            tmp_path,
            tmp_path,
            tmp_path / "out",
            None,
            Words(),
            lambda _: "de",
        )
    assert not list((tmp_path / "out/builds").glob("*/manifest.json"))
