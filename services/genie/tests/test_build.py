"""index.build end to end on real Docling output: inventory -> chunks -> index -> search."""

import json
from collections.abc import Sequence
from pathlib import Path

from test_chunking import Words
from test_extract import OCEAN2, STS, unpack

from index.build import EmbeddingCache, build, failure_reason
from linker_genie.embedding import Passage, pack
from linker_genie.retrieval import DocumentIndex

TRUNCATED = "7e" * 32


class CountingEmbedder:
    """Two-dimensional vectors from the passage length; counts what it was asked."""

    model = "counting"
    dimensions = 2
    fingerprint = {"model": "counting", "dimensions": "2"}

    def __init__(self) -> None:
        self.embedded = 0

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        self.embedded += len(passages)
        return [pack([1.0, float(len(passage.text) % 7)]) for passage in passages]

    def embed_query(self, text: str) -> bytes:
        return pack([1.0, 0.0])


class WireNamedEmbedder(CountingEmbedder):
    """An encoder whose API name differs from its provider-neutral identity.

    GeminiEmbedder is this shape: `model` is the provider's wire name
    (google/gemini-embedding-2 on OpenRouter), the fingerprint's is the
    identity the index is keyed by.
    """

    model = "vendor/counting"
    fingerprint = {"model": "counting", "dimensions": "2"}


def document(
    sha: str, url: str, models: list[str], doc_type: str, lang: str
) -> dict[str, object]:
    return {
        "sha256": sha,
        "bytes": 1,
        "urls": [url],
        "media_ids": [1],
        "title_en": url.rsplit("/", 1)[-1],
        "title_de": "",
        "brands": ["GoodWe"] if models else [],
        "models": models,
        "product_ids": [],
        "doc_type": doc_type,
        "lang": lang,
        "linked": bool(models),
    }


def corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    parsed = tmp_path / "parsed"
    parsed.mkdir()
    for sha in (STS, OCEAN2):
        unpack(sha, parsed)
    pdfs = tmp_path / "pdf"
    pdfs.mkdir()
    (pdfs / f"{TRUNCATED}.pdf").write_bytes(
        b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\n"
    )
    inventory = tmp_path / "inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "source": "https://de-linker.com",
                "products": [
                    {
                        "id": 6530,
                        "status": "publish",
                        "brand": "GoodWe",
                        "model": "GW60K-STS-G10",
                    }
                ],
                "documents": [
                    document(
                        STS,
                        "https://de-linker.com/GW_STS-30-60kW_Datasheet_EMEA-EN_V1.1.pdf",
                        ["GW30K-STS-G10", "GW60K-STS-G10"],
                        "datasheet",
                        "en",
                    ),
                    document(
                        OCEAN2,
                        "https://de-linker.com/ecoflow-ocean2-single-phase-datasheet-en.pdf",
                        [],
                        "datasheet",
                        "en",
                    ),
                    document(
                        TRUNCATED,
                        "https://de-linker.com/HS3-SinglePhase-EU.pdf",
                        [],
                        "other",
                        "",
                    ),
                ],
            }
        )
    )
    return inventory, pdfs, parsed


def test_a_build_indexes_every_parsed_page_and_reports_the_failure(
    tmp_path: Path,
) -> None:
    inventory, pdfs, parsed = corpus(tmp_path)

    directory = build(
        inventory,
        pdfs,
        parsed,
        tmp_path / "out",
        CountingEmbedder(),
        Words(),
        lambda text: "en",
    )

    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["documents"] == {"total": 3, "indexed": 2, "failed": 1}
    assert manifest["pages"] == {"total": 5, "with_chunks": 5}
    assert manifest["failures"][0]["sha256"] == TRUNCATED
    assert "truncated" in manifest["failures"][0]["error"]
    coverage = {
        item["sha256"]: item
        for item in json.loads((directory / "coverage.json").read_text())
    }
    assert coverage[OCEAN2]["empty_pages"] == {}


def test_the_built_index_answers_from_the_right_page(tmp_path: Path) -> None:
    inventory, pdfs, parsed = corpus(tmp_path)
    directory = build(
        inventory,
        pdfs,
        parsed,
        tmp_path / "out",
        CountingEmbedder(),
        Words(),
        lambda text: "en",
    )

    index = DocumentIndex(directory / "index.sqlite", encoder=None)
    sts = index.search("nominal frequency GW60K-STS-G10", "en", product_ids=[6530], k=1)
    ocean = index.search("Maximum PV Power", "en", k=3)

    assert (sts[0].doc_sha256, sts[0].page) == (STS, 2)
    assert (ocean[0].doc_sha256, ocean[0].page) == (
        OCEAN2,
        2,
    )  # the page rebuilt from OCR


def test_the_index_records_the_encoders_identity_not_its_wire_name(
    tmp_path: Path,
) -> None:
    # A rebuilt index that recorded google/gemini-embedding-2 opened with no query
    # encoder (retrieval.query_encoder resolves the neutral name) and every search
    # silently dropped to keywords. The identity is what the index is keyed by.
    inventory, pdfs, parsed = corpus(tmp_path)
    directory = build(
        inventory,
        pdfs,
        parsed,
        tmp_path / "out",
        WireNamedEmbedder(),
        Words(),
        lambda text: "en",
    )

    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["embedding_model"] == "counting"
    assert DocumentIndex(directory / "index.sqlite", encoder=None).embedding_model == (
        "counting"
    )


def test_a_complete_pdf_that_failed_to_parse_reports_the_parser_errors(
    tmp_path: Path,
) -> None:
    pdf = tmp_path / "ok.pdf"
    pdf.write_bytes(b"%PDF-1.7\n...\n%%EOF\n")

    assert failure_reason(pdf, ["layout: out of memory"]) == "layout: out of memory"


def test_the_embedding_cache_reuses_vectors_per_encoder_fingerprint(
    tmp_path: Path,
) -> None:
    passages = [Passage("t", "a"), Passage("t", "b")]
    embedder = CountingEmbedder()
    rebuilt = CountingEmbedder()
    # The same model name under a new revision: a fingerprint the index would reject.
    rebuilt.fingerprint = {**embedder.fingerprint, "revision": "new"}
    cache = EmbeddingCache(tmp_path / "cache.sqlite")
    cache.embed(embedder, passages)
    cache.embed(embedder, passages)
    cache.embed(rebuilt, passages)

    # Two passages for the original fingerprint (the second call is served from the
    # cache); the rebuilt encoder recomputes instead of silently reusing its vectors.
    assert embedder.embedded == 2
    assert rebuilt.embedded == 2
