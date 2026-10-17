"""Document search over an index written by index.store (FTS5 + sqlite-vec)."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from index import corpus, store
from index.chunking import Chunk
from index.corpus import DocumentRow
from linker_genie.embedding import EmbeddingError, Passage, pack
from linker_genie.retrieval import DocumentIndex, fts_query, is_passage, rrf

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
    fingerprint = {"model": "toy", "dimensions": "3"}

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
    meta = corpus.Meta(
        "20261009T000000Z",
        "toy",
        3,
        "docling test",
        512,
        embedding=AxisEncoder.fingerprint,
    )
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


def test_a_preencoded_query_vector_ranks_like_the_encoder_would(
    index_path: Path,
) -> None:
    index = DocumentIndex(index_path, encoder=AxisEncoder())

    preencoded = index.search(
        "certificate grid code", "en", k=1, query_vector=pack(AXES["certificate"])
    )

    assert [hit.chunk_id for hit in preencoded] == ["cert-1"]


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


def test_an_encoder_other_than_the_one_that_built_the_index_is_refused(
    index_path: Path,
) -> None:
    class Other(AxisEncoder):
        fingerprint = {"model": "toy", "dimensions": "3", "onnx_sha256": "different"}

    with pytest.raises(RuntimeError, match="differs"):
        DocumentIndex(index_path, encoder=Other())


class BrokenEncoder(AxisEncoder):
    """An encoder whose endpoint is down: every query raises."""

    def embed_query(self, text: str) -> bytes:
        raise EmbeddingError("toy: URLError after 3 attempts")


def test_a_failed_encoding_raises_instead_of_ranking_by_keywords(
    index_path: Path,
) -> None:
    index = DocumentIndex(index_path, encoder=BrokenEncoder())

    with pytest.raises(EmbeddingError, match="after 3 attempts"):
        index.search("maximum input power GW10K-ET", "en")


def test_without_an_encoder_bm25_ranks_and_the_log_says_so(
    index_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    index = DocumentIndex(index_path, encoder=None)

    with caplog.at_level("WARNING"):
        hits = index.search("Zertifikat", "de")

    assert index.ranking == "keywords"
    assert [hit.chunk_id for hit in hits] == ["cert-1"]
    assert "document search by BM25: no query encoder for toy" in caplog.text


def test_with_an_encoder_the_ranking_is_vector(index_path: Path) -> None:
    assert DocumentIndex(index_path, encoder=AxisEncoder()).ranking == "vector"


@pytest.mark.parametrize(
    ("text", "kept"),
    [
        ("SAND", False),
        ("3.", False),
        ("D A N G E R :", False),
        ("10 mm²", False),
        ("|  | HVM 16.6 | ● | ● |", True),
        ("Max. Input Power (kW) 15", True),
    ],
)
def test_parsing_scraps_are_not_passages(text: str, kept: bool) -> None:
    assert is_passage(text) is kept


def test_a_model_code_in_the_question_narrows_to_its_documents(
    index_path: Path,
) -> None:
    index = DocumentIndex(index_path, encoder=AxisEncoder())

    assert index.documents_naming("battery for the GW10K-ET?") == [ET]
    assert index.documents_naming("the F12.8-H stack") == [LYNX]
    assert index.documents_naming("which battery?") == []
    # The vector says "battery" (the Lynx manual); the named model keeps the search
    # in the ET's documents.
    hits = index.search("battery GW10K-ET", "en")
    assert {hit.doc_sha256 for hit in hits} == {ET}


def _build(tmp_path: Path, documents: list[DocumentRow], chunks: list[Chunk]) -> Path:
    meta = corpus.Meta(
        "v", "toy", 3, "docling test", 512, embedding=AxisEncoder.fingerprint
    )
    vectors = [pack(AXES["battery"]) for _ in chunks]
    corpus.write(tmp_path / "c", meta, documents, [], chunks, vectors)
    store.export(tmp_path / "c", tmp_path / "n.sqlite")
    return tmp_path / "n.sqlite"


def _document(sha: str, doc_type: str, pages: int) -> DocumentRow:
    return DocumentRow(
        sha, (f"https://de-linker.com/{sha[:4]}.pdf",), sha[:4], "", (), (),
        doc_type, "en", pages, "indexed",
    )  # fmt: skip


def test_a_hit_brings_the_other_passages_of_its_page(tmp_path: Path) -> None:
    path = _build(
        tmp_path,
        [_document(LYNX, "manual", 40)],
        [
            chunk("row-1", LYNX, 3, "| Warranty | 5 years | before 2026 |"),
            chunk("scrap", LYNX, 3, "SAND"),
            chunk("row-2", LYNX, 3, "| Warranty | 10 years | from 2026 |"),
            chunk("other", LYNX, 4, "Another page entirely, battery wiring."),
        ],
    )
    index = DocumentIndex(path, encoder=AxisEncoder())
    first = index.hits([(1, 0.0)], "en")

    hits = index.with_page_neighbours(first, "en")

    assert [hit.chunk_id for hit in hits] == ["row-1", "row-2"]


def test_a_short_datasheet_comes_whole(tmp_path: Path) -> None:
    path = _build(
        tmp_path,
        [_document(ET, "datasheet", 2)],
        [
            chunk("overview", ET, 1, "Overview of the battery system and its range."),
            chunk("table", ET, 2, "| Nominal Capacity (kWh) | 260 |"),
        ],
    )
    index = DocumentIndex(path, encoder=AxisEncoder())
    first = index.hits([(1, 0.0)], "en")

    hits = index.with_page_neighbours(first, "en")

    assert [hit.chunk_id for hit in hits] == ["overview", "table"]


def test_neighbours_stop_at_the_limit(tmp_path: Path) -> None:
    path = _build(
        tmp_path,
        [_document(LYNX, "manual", 40)],
        [chunk(f"row-{n}", LYNX, 3, f"| Row {n} | battery data |") for n in range(6)],
    )
    index = DocumentIndex(path, encoder=AxisEncoder())

    hits = index.with_page_neighbours(index.hits([(1, 0.0)], "en"), "en", limit=3)

    assert [hit.chunk_id for hit in hits] == ["row-0", "row-1", "row-2"]
