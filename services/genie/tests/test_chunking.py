"""Chunking rules (docs/specs/10-knowledge-index.md, Build 2), with a word tokenizer."""

from index.chunking import Chunk, DocumentMeta, chunk_document, context_header
from index.extract import Block, Page


class Words:
    """One token per whitespace-separated word; the chunker only needs count and split."""

    def count(self, text: str) -> int:
        return len(text.split())

    def split(self, text: str, max_tokens: int) -> list[str]:
        words = text.split()
        return [
            " ".join(words[i : i + max_tokens])
            for i in range(0, len(words), max_tokens)
        ] or [text]


META = DocumentMeta(
    sha256="ab" * 32,
    title_en="ET datasheet",
    title_de="ET Datenblatt",
    brands=("GoodWe",),
    models=("GW10K-ET",),
    doc_type="datasheet",
    lang="en",
)


def chunks(
    pages: list[Page], max_tokens: int = 40, meta: DocumentMeta = META
) -> list[Chunk]:
    return chunk_document(meta, pages, Words(), lambda text: "de", max_tokens)


def text(words: int, word: str = "w") -> Block:
    return Block(kind="text", text=" ".join([word] * words))


def test_the_context_header_names_brand_models_type_title_section_and_page() -> None:
    assert (
        context_header(META, "Technical Data", 2)
        == "GoodWe | GW10K-ET | datasheet | ET datasheet / ET Datenblatt | Technical Data | p. 2"
    )


def test_empty_header_parts_are_left_out() -> None:
    bare = DocumentMeta("cd" * 32, "S9", "", (), (), "other", "")

    assert context_header(bare, "", 7) == "other | S9 | p. 7"


def test_a_chunk_never_spans_two_pages() -> None:
    result = chunks([Page(1, "docling", [text(5)]), Page(2, "docling", [text(5)])])

    assert [chunk.page for chunk in result] == [1, 2]


def test_a_heading_closes_the_chunk_and_names_the_following_section_across_pages() -> (
    None
):
    result = chunks(
        [
            Page(
                1, "docling", [text(3), Block(kind="heading", text="Wiring"), text(4)]
            ),
            Page(2, "docling", [text(2)]),
        ]
    )

    assert [(chunk.page, chunk.section) for chunk in result] == [
        (1, ""),
        (1, "Wiring"),
        (2, "Wiring"),
    ]
    assert all("Wiring" not in chunk.text for chunk in result)


def test_every_chunk_including_its_header_stays_within_the_limit() -> None:
    result = chunks(
        [Page(1, "docling", [text(15), text(15), text(15), text(90)])], max_tokens=40
    )

    assert len(result) > 2
    assert all(chunk.tokens <= 40 for chunk in result)
    assert all(
        chunk.tokens == Words().count(f"{chunk.header}\n{chunk.text}")
        for chunk in result
    )


def test_a_table_is_a_chunk_of_its_own() -> None:
    table = Block(
        kind="table",
        rows=(("Model", "GW10K-ET"), ("Max. Input Power (kW)", "15")),
        header_rows=1,
    )

    result = chunks([Page(1, "docling", [text(3), table, text(3)])])

    assert [chunk.kind for chunk in result] == ["text", "table", "text"]
    assert result[1].text == "| Model | GW10K-ET |\n| Max. Input Power (kW) | 15 |"


def test_a_long_table_is_cut_between_rows_and_each_piece_repeats_the_header_rows() -> (
    None
):
    rows = (("Parameter", "GW8K-ET", "GW10K-ET"),) + tuple(
        (f"Row{i}", "1", "2") for i in range(20)
    )
    table = Block(kind="table", rows=rows, header_rows=1)

    result = chunks([Page(3, "docling", [table])], max_tokens=40)

    assert len(result) > 1
    assert all(
        chunk.text.startswith("| Parameter | GW8K-ET | GW10K-ET |") for chunk in result
    )
    body = [line for chunk in result for line in chunk.text.split("\n")[1:]]
    assert body == [f"| Row{i} | 1 | 2 |" for i in range(20)]


def test_chunk_ids_are_stable_unique_and_carry_document_and_page() -> None:
    pages = [
        Page(
            4,
            "docling",
            [text(3, "same"), Block(kind="heading", text="h"), text(3, "same")],
        )
    ]

    first, again = chunks(pages), chunks(pages)

    assert [chunk.id for chunk in first] == [chunk.id for chunk in again]
    assert len({chunk.id for chunk in first}) == len(first)
    assert all(chunk.id.startswith(f"{'ab' * 6}-p4-") for chunk in first)


def test_language_comes_from_the_documents_field_when_it_names_one_language() -> None:
    assert {chunk.lang for chunk in chunks([Page(1, "docling", [text(3)])])} == {"en"}


def test_language_is_detected_per_chunk_for_multilingual_documents() -> None:
    multi = DocumentMeta("ef" * 32, "Guide", "", (), (), "manual", "multi")

    assert {
        chunk.lang for chunk in chunks([Page(1, "docling", [text(3)])], meta=multi)
    } == {"de"}
