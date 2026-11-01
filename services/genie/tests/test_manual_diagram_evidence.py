"""Original PDF figure pixels, exact model associations and runtime recall."""

from __future__ import annotations

import base64
import gzip
import io
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from test_chunking import Words

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from index.extract import enrich_model_axes
from index.manual_evidence import compile_manual_evidence
from index.physical_evidence import attach_physical_evidence, extract_diagram_evidence
from linker_genie.figures import tag
from linker_genie.manual_diagram import model_list_descriptor, physical_descriptor
from linker_genie.manual_diagram_records import DIAGRAMS
from linker_genie.manual_evidence import valid_reviewed_manual
from linker_genie.publication import Snapshot
from linker_genie.publication_scope import authorize_chunk
from linker_genie.retrieval import DocumentIndex

FIXTURE = (
    Path(__file__).parent
    / "fixtures/publication-compiler/reviewed-diagram-evidence.json.gz"
)


def fixture() -> tuple[dict[str, Any], list[Chunk], dict[str, bytes]]:
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    return (
        data["manifest"],
        [Chunk(**chunk) for chunk in data["chunks"]],
        {name: base64.b64decode(value) for name, value in data["pixels"].items()},
    )


class RenderedPage:
    def __init__(self, sha: str, number: int, images: dict[str, bytes]) -> None:
        self.sha, self.number, self.images = sha, number, images

    def get_rotation(self) -> int:
        return 0

    def get_size(self) -> tuple[float, float]:
        return 1207.56005859375, 824.8820190429688

    def render(self, scale: int) -> RenderedPage:
        assert scale == 2
        return self

    def to_pil(self) -> Image.Image:
        result = Image.new("RGB", (2416, 1650), "white")
        for record in DIAGRAMS:
            for descriptor in (
                physical_descriptor(record),
                model_list_descriptor(record),
            ):
                if (
                    descriptor["source_sha256"] == self.sha
                    and descriptor["source_page"] == self.number
                ):
                    image = Image.open(
                        io.BytesIO(self.images[descriptor["figure"]])
                    ).convert("RGB")
                    result.paste(
                        image, (descriptor["bbox"][0] * 2, descriptor["bbox"][1] * 2)
                    )
        return result

    def close(self) -> None:
        pass


class RenderedPDF:
    """Real manufacturer crop pixels placed at their original page locations."""

    def __init__(self, sha: str, images: dict[str, bytes]) -> None:
        self.sha, self.images = sha, images
        self.renders = 0

    def __len__(self) -> int:
        return 4 if self.sha.startswith("307b") else 2

    def __getitem__(self, index: int) -> RenderedPage:
        self.renders += 1
        return RenderedPage(self.sha, index + 1, self.images)


def compiled() -> tuple[dict[str, Any], list[Chunk], dict[str, Any]]:
    raw, chunks, images = fixture()
    evidence = []
    for sha in {record["sha256"] for record in DIAGRAMS}:
        pdf = RenderedPDF(sha, images)
        evidence += extract_diagram_evidence(pdf, sha, chunks)
        assert pdf.renders == (1 if sha.startswith("307b") else 2)
    chunks = attach_physical_evidence(chunks, evidence)
    units, proofs = compile_manual_evidence(
        chunks, Snapshot.read(raw), Words(), 512, restricted_contexts={}
    )
    for proof in proofs.values():
        proof["model_identity_revision"] = raw["model_identity_revision"]
    return raw, units, proofs


def test_original_figure_pixels_anchor_eight_exact_current_models() -> None:
    raw, units, proofs = compiled()
    assert len(units) == 14
    for pid in [3595, 6507, 6508, 6509, 6510, 6511]:
        selected = [c for c in units if proofs[c.id]["product_ids"] == [pid]]
        assert {c.page for c in selected} == {1}
        assert any("600 mm on each side" in c.text for c in selected)
        assert any(
            "80 mm deep" in c.text and "14 Nm to 24 Nm" in c.text for c in selected
        )
    for pid in [1954, 1955]:
        selected = [c for c in units if proofs[c.id]["product_ids"] == [pid]]
        assert len(selected) == 1 and selected[0].page == 2
        assert "985 mm by 330 mm" in selected[0].text
        assert "14 mm diameter and 80 mm depth" in selected[0].text
        assert "50 Nm" in selected[0].text
    assert len(raw["products"]) == 8


def test_hydration_figures_keep_dimensions_and_torque_units() -> None:
    wall = tag("etr", DIAGRAMS[1]["excerpt"]).figures
    battery = tag("battery", DIAGRAMS[2]["excerpt"]).figures
    assert {"14 Nm", "24 Nm"}.issubset(wall.values())
    assert {"985 mm", "330 mm", "50 Nm"}.issubset(battery.values())


def test_altered_pixels_identity_figures_and_wrong_model_are_denied(
    tmp_path: Path,
) -> None:
    raw, chunks, images = fixture()
    image = Image.open(io.BytesIO(images["ETR12510INT0002"])).convert("RGB")
    image.putpixel((50, 50), (1, 2, 3))
    changed = io.BytesIO()
    image.save(changed, format="PNG")
    images["ETR12510INT0002"] = changed.getvalue()
    etr_sha = DIAGRAMS[0]["sha256"]
    items = extract_diagram_evidence(RenderedPDF(etr_sha, images), etr_sha, chunks)
    assert {item["figure"] for item in items} == {"ETR12510DSC0001", "ETR model list"}
    diagram = next(item for item in items if item["figure"] == "ETR12510DSC0001")
    target = next(c for c in chunks if c.id == diagram["target_chunk_id"])
    assert not attach_physical_evidence([target, target], items)[
        0
    ].source_physical_evidence
    bad = [{**diagram, "source_page": 2}]
    assert not any(
        c.source_physical_evidence for c in attach_physical_evidence(chunks, bad)
    )
    without_model_list = attach_physical_evidence(chunks, [diagram])
    _, no_scope = compile_manual_evidence(
        without_model_list, Snapshot.read(raw), Words(), 512, restricted_contexts={}
    )
    assert not no_scope

    # A purported original with different full bytes is rejected before opening
    # it or invoking any physical-evidence extractor.
    path = tmp_path / f"{etr_sha}.pdf"
    path.write_bytes(b"not the source PDF")
    called: list[bool] = []
    with pytest.raises(ValueError, match="source PDF bytes"):
        enrich_model_axes([], path, on_physical=lambda *_: called.append(True))
    assert not called

    # A BTR model attached to the same manual does not appear in the ETR list.
    product = deepcopy(raw["products"][0])
    product.update(product_id=999999, model="GW80K-BTR-G10", product_revision="foreign")
    raw["products"].append(product)
    for document in raw["documents"]:
        if document["blob_sha256"] == etr_sha:
            document["product_ids"].append(999999)
    chunks = attach_physical_evidence(chunks, items)
    _, proofs = compile_manual_evidence(
        chunks, Snapshot.read(raw), Words(), 512, restricted_contexts={}
    )
    assert not any(999999 in proof["product_ids"] for proof in proofs.values())


def test_runtime_requires_original_pixels_and_live_association() -> None:
    raw, units, proofs = compiled()
    unit = next(c for c in units if "ETR12510INT0002" in c.text)
    proof = proofs[unit.id]
    source = Snapshot.read(raw)
    args = {"sha": unit.doc_sha256, "chunk_id": unit.id, "text": unit.text}
    assert valid_reviewed_manual(proof, proof["product_ids"], source.products, **args)
    for key, bad in [
        ("pixel_sha256", "0" * 64),
        ("bbox", [0, 0, 1, 1]),
        ("source_page", 2),
    ]:
        changed = deepcopy(proof)
        changed["reviewed_manual"]["physical_evidence"][key] = bad
        assert not valid_reviewed_manual(
            changed, proof["product_ids"], source.products, **args
        )
    changed = deepcopy(proof)
    changed["reviewed_manual"]["physical_model_evidence"]["pixel_sha256"] = "0" * 64
    assert not valid_reviewed_manual(
        changed, proof["product_ids"], source.products, **args
    )
    assert not authorize_chunk(
        unit.doc_sha256,
        proof["product_ids"],
        [],
        proof,
        products=source.products,
        documents=source.documents,
        chunk_id=unit.id,
        text=unit.text,
    )
    assert (
        physical_descriptor(DIAGRAMS[1])
        == proof["reviewed_manual"]["physical_evidence"]
    )


def test_figure_passages_reach_sqlite_and_withdrawals_are_enforced(
    tmp_path: Path,
) -> None:
    raw, units, proofs = compiled()
    source_dir = tmp_path / "corpus"
    corpus.write(
        source_dir,
        corpus.Meta(
            "reviewed-manual-diagram",
            None,
            None,
            "original figure pixels",
            512,
            publication={
                "manifest": raw,
                "chunk_products": {cid: p["product_ids"] for cid, p in proofs.items()},
                "chunk_scopes": proofs,
            },
        ),
        [
            DocumentRow(
                d["blob_sha256"],
                (d["url"],),
                d["title"],
                "",
                (),
                (),
                "manual",
                "en",
                4,
                "indexed",
            )
            for d in raw["documents"]
        ],
        [(p["product_id"], p["model"]) for p in raw["products"]],
        units,
    )
    target = tmp_path / "index.sqlite"
    store.export(source_dir, target)
    loaded = DocumentIndex(target, encoder=None)
    try:
        for pid in [3595, 6507, 6508, 6509, 6510, 6511]:
            hits = loaded.search(
                "wall mounting 10 mm holes", "en", [pid], publication=Snapshot.read(raw)
            )
            assert any("14 Nm to 24 Nm" in hit.text and hit.page == 1 for hit in hits)
        for pid in [1954, 1955]:
            hits = loaded.search(
                "floor mounting 985 330 holes",
                "en",
                [pid],
                publication=Snapshot.read(raw),
            )
            assert any("50 Nm" in hit.text and hit.page == 2 for hit in hits)
        revoked = deepcopy(raw)
        for document in revoked["documents"]:
            if document["blob_sha256"].startswith("307b"):
                document["product_ids"].remove(6507)
        assert not loaded.search(
            "wall mounting 10 mm holes",
            "en",
            [6507],
            publication=Snapshot.read(revoked),
        )
        assert loaded.search(
            "wall mounting 10 mm holes",
            "en",
            [6508],
            publication=Snapshot.read(revoked),
        )
    finally:
        loaded.close()
