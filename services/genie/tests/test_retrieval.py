"""Hybrid search over an index written by index.store (FTS5 + sqlite-vec)."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from linker_genie.embedding import Passage, pack
from linker_genie.retrieval import DocumentIndex, fts_query, rrf

ET = "e7" * 32
LYNX = "1f" * 32
CERT = "c3" * 32
# Toy 3-dimensional vectors: axis 0 = PV input, axis 1 = battery, axis 2 = certificate.
AXES = {
    "pv": (1.0, 0.0, 0.0),
    "battery": (0.0, 1.0, 0.0),
    "certificate": (0.0, 0.0, 1.0),
}


class AxisEncoder:
    """Embeds a query onto the axis its first known word names."""

    model = "toy"
    dimensions = 3

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        raise AssertionError("queries only")

    def embed_query(self, text: str) -> bytes:
        for word, axis in AXES.items():
            if word in text.lower():
                return pack(axis)
        return pack((0.577, 0.577, 0.577))


def chunk(chunk_id: str, sha: str, page: int, text: str, header: str = "") -> Chunk:
    return Chunk(chunk_id, sha, page, "", "text", header, text, "en", 10)


@pytest.fixture
def index_path(tmp_path: Path) -> Path:
    path = tmp_path / "index.sqlite"
    documents = [
        DocumentRow(
            ET,
            (f"https://de-linker.com/{ET[:4]}.pdf",),
            "ET datasheet",
            "ET Datenblatt",
            ("GoodWe",),
            ("GW10K-ET",),
            "datasheet",
            "en",
            2,
            "indexed",
        ),
        DocumentRow(
            LYNX,
            ("https://de-linker.com/lynx.pdf",),
            "Lynx manual",
            "",
            ("GoodWe",),
            ("LX F12.8-H",),
            "manual",
            "en",
            40,
            "indexed",
        ),
        DocumentRow(
            CERT,
            ("https://de-linker.com/cert.pdf",),
            "VDE certificate",
            "",
            (),
            (),
            "certificate",
            "de",
            3,
            "indexed",
        ),
    ]
    chunks = [
        chunk(
            "et-2",
            ET,
            2,
            "| Max. Input Power (kW) | 15 |\n| Start-up Voltage (V) | 180 |",
            "GoodWe | GW10K-ET | datasheet | ET datasheet / ET Datenblatt | Technical Data | p. 2",
        ),
        chunk(
            "lynx-12",
            LYNX,
            12,
            "Battery modules per stack: 2 to 8. Connect the PCU first.",
            "GoodWe | LX F12.8-H | manual | p. 12",
        ),
        chunk(
            "lynx-30",
            LYNX,
            30,
            "Commissioning: switch on the battery breaker, then the inverter.",
            "GoodWe | LX F12.8-H | manual | p. 30",
        ),
        chunk(
            "cert-1",
            CERT,
            1,
            "Zertifikat VDE-AR-N 4105 für Wechselrichter GW10K-ET",
            "certificate | VDE certificate | p. 1",
        ),
    ]
    vectors = [
        pack(AXES["pv"]),
        pack(AXES["battery"]),
        pack(AXES["battery"]),
        pack(AXES["certificate"]),
    ]
    meta = corpus.Meta("20261009T000000Z", "toy", 3, "docling test", 512)
    products = [(101, "GW10K-ET"), (202, "LX F12.8-H")]
    corpus.write(tmp_path / "corpus", meta, documents, products, chunks, vectors)
    store.export(tmp_path / "corpus", path)
    return path


def test_fts_query_quotes_each_term_and_keeps_model_codes_together() -> None:
    assert (
        fts_query('Max input of the GW10K-ET? "quoted"')
        == '"max" OR "input" OR "of" OR "the" OR "gw10k-et" OR "quoted"'
    )


def test_fts_query_of_punctuation_only_is_empty() -> None:
    assert fts_query("?? --") == ""


def test_rrf_adds_reciprocal_ranks_with_k_60() -> None:
    fused = rrf([[1, 2, 3], [3, 1]])

    assert [item for item, _ in fused] == [1, 3, 2]
    assert fused[0][1] == pytest.approx(1 / 61 + 1 / 62)


def test_keyword_search_finds_a_table_row_through_the_model_code_in_its_header(
    index_path: Path,
) -> None:
    index = DocumentIndex(index_path, encoder=None)

    hits = index.search("maximum input power GW10K-ET", "en")

    assert hits[0].chunk_id == "et-2"
    assert (hits[0].page, hits[0].link) == (
        2,
        f"https://de-linker.com/{ET[:4]}.pdf#page=2",
    )


def test_vectors_find_a_passage_without_shared_words(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=AxisEncoder())

    hits = index.search("certificate grid code", "en", k=1)

    assert [hit.chunk_id for hit in hits] == ["cert-1"]


def test_product_ids_narrow_to_the_documents_of_their_models(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=AxisEncoder())

    hits = index.search("battery pv certificate", "en", product_ids=[202])

    assert {hit.doc_sha256 for hit in hits} == {LYNX}


def test_unknown_products_search_the_whole_library(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=None)

    hits = index.search("GW10K-ET", "en", product_ids=[999])

    assert {hit.chunk_id for hit in hits} == {"et-2", "cert-1"}


def test_an_empty_narrowed_search_falls_back_to_the_whole_library(
    index_path: Path,
) -> None:
    index = DocumentIndex(index_path, encoder=None)

    hits = index.search("Zertifikat", "de", product_ids=[202])

    assert [hit.chunk_id for hit in hits] == ["cert-1"]


def test_doc_types_filter_the_results(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=None)

    hits = index.search("GW10K-ET", "en", doc_types=["certificate"])

    assert [hit.chunk_id for hit in hits] == ["cert-1"]


def test_lang_picks_the_title_language(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=None)

    assert index.search("GW10K-ET power", "de", k=1)[0].title == "ET Datenblatt"
    assert index.search("GW10K-ET power", "en", k=1)[0].title == "ET datasheet"


def test_an_unsupported_lang_is_refused(index_path: Path) -> None:
    with pytest.raises(ValueError):
        DocumentIndex(index_path, encoder=None).search("x", "fr")


def test_chunks_resolve_cited_ids_in_the_given_order(index_path: Path) -> None:
    index = DocumentIndex(index_path, encoder=None)

    assert [
        hit.chunk_id for hit in index.chunks(["lynx-30", "nope", "et-2"], "en")
    ] == ["lynx-30", "et-2"]


def test_an_index_of_another_schema_version_is_refused(index_path: Path) -> None:
    import sqlite3

    db = sqlite3.connect(index_path)
    db.execute("UPDATE meta SET value = '0' WHERE key = 'schema_version'")
    db.commit()
    db.close()

    with pytest.raises(RuntimeError, match="schema"):
        DocumentIndex(index_path, encoder=None)


def test_the_store_refuses_an_existing_file_and_the_corpus_mismatched_vectors(
    index_path: Path, tmp_path: Path
) -> None:
    with pytest.raises(FileExistsError):
        store.export(tmp_path / "corpus", index_path)
    meta = corpus.Meta("v", "toy", 3, "p", 512)
    with pytest.raises(ValueError):
        corpus.write(tmp_path / "other", meta, [], [], [chunk("x", ET, 1, "t")], [])


def test_a_keywords_only_index_searches_without_vectors(tmp_path: Path) -> None:
    meta = corpus.Meta("v", None, None, "p", 512)
    document = DocumentRow(
        ET,
        ("https://de-linker.com/et.pdf",),
        "ET",
        "",
        (),
        (),
        "datasheet",
        "en",
        2,
        "indexed",
    )
    corpus.write(
        tmp_path / "bm25", meta, [document], [], [chunk("x", ET, 1, "Max. Input Power")]
    )
    store.export(tmp_path / "bm25", tmp_path / "bm25.sqlite")

    index = DocumentIndex(tmp_path / "bm25.sqlite", encoder=AxisEncoder())

    assert index.encoder is None
    assert [hit.chunk_id for hit in index.search("input power", "en")] == ["x"]
