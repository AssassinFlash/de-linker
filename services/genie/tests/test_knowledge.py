"""The in-process document search tool: its result, its errors, and what the model reads."""

import logging
import sqlite3
from dataclasses import dataclass, field
from typing import Any

import pytest

from linker_genie.embedding import EmbeddingError
from linker_genie.knowledge import (
    KnowledgeSearch,
    KnowledgeUnavailable,
    model_view,
    validate,
)
from linker_genie.retrieval import DocumentHit


@dataclass
class Encoder:
    model: str = "google/gemini-embedding-2"


@dataclass
class FakeIndex:
    """Answers `search` with one table chunk, or raises what it is told to."""

    error: Exception | None = None
    encoder: Encoder | None = field(default_factory=Encoder)
    version: str = "20261016T072222Z"
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    @property
    def ranking(self) -> str:
        return "vector" if self.encoder else "keywords"

    def search(
        self, query: str, lang: str, product_ids: Any = None
    ) -> list[DocumentHit]:
        self.calls.append((query, lang, product_ids))
        if self.error:
            raise self.error
        return [
            DocumentHit(
                chunk_id="770c-p37-63a0",
                doc_sha256="770c",
                doc_url="https://de-linker.com/h2.pdf",
                title="SAJ H2 manual",
                doc_type="manual",
                page=37,
                section="Datasheet",
                text="| No. of MPPT | 3 | 3 |",
                lang="en",
                score=0.0,
            )
        ]


def test_a_search_returns_tagged_hits_with_the_ranking_and_encoder() -> None:
    index = FakeIndex()

    payload = KnowledgeSearch(lambda: index)(  # type: ignore[arg-type,return-value]
        {"query": "MPPT H2-10K-T3", "lang": "de", "product_ids": [3556, 3556]}
    )

    assert index.calls == [("MPPT H2-10K-T3", "de", [3556])]
    assert payload["ranking"] == "vector"
    assert payload["encoder"] == "google/gemini-embedding-2"
    assert payload["index_version"] == "20261016T072222Z"
    hit = payload["hits"][0]
    assert hit["text"] == "| No. of MPPT | [n1=3] | [n2=3] |"
    assert hit["figures"] == {"770c-p37-63a0.n1": "3", "770c-p37-63a0.n2": "3"}
    assert hit["doc_url"] == "https://de-linker.com/h2.pdf"


def test_the_model_reads_no_url_and_no_figure_table() -> None:
    payload = KnowledgeSearch(lambda: FakeIndex())({"query": "q", "lang": "en"})  # type: ignore[arg-type,return-value]

    view = model_view(payload)

    assert view == {
        "hits": [
            {
                "chunk_id": "770c-p37-63a0",
                "title": "SAJ H2 manual",
                "page": 37,
                "section": "Datasheet",
                "text": "| No. of MPPT | [n1=3] | [n2=3] |",
            }
        ]
    }


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "query"),
        ({"query": "  "}, "query"),
        ({"query": "q", "lang": "fr"}, "lang"),
        ({"query": "q", "product_ids": ["7"]}, "product_ids"),
        ({"query": "q", "product_ids": [0]}, "product_ids"),
    ],
)
def test_an_invalid_input_is_answered_with_an_error_object(
    arguments: dict[str, Any], message: str
) -> None:
    index = FakeIndex()

    payload = KnowledgeSearch(lambda: index)(arguments)  # type: ignore[arg-type,return-value]

    assert message in payload["error"]
    assert index.calls == []


def test_a_failed_query_encoding_is_raised_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    index = FakeIndex(error=EmbeddingError("gemini: HTTPError after 3 attempts"))

    with caplog.at_level(logging.ERROR), pytest.raises(EmbeddingError):
        KnowledgeSearch(lambda: index)({"query": "q", "lang": "en"})  # type: ignore[arg-type,return-value]

    assert "document search failed" in caplog.text


def test_an_unreadable_index_is_raised_as_knowledge_unavailable() -> None:
    index = FakeIndex(error=sqlite3.OperationalError("unable to open database file"))

    with pytest.raises(KnowledgeUnavailable, match="unable to open"):
        KnowledgeSearch(lambda: index)({"query": "q", "lang": "en"})  # type: ignore[arg-type,return-value]


def test_validate_defaults_the_language_to_english() -> None:
    assert validate({"query": " MPPT "}) == ("MPPT", "en", [])


def test_a_document_answer_passes_the_logged_citation_check() -> None:
    """The quality check rebuilds the turn's facts from the logged tool results
    (quality.citations): a hydrated document answer - localized figures, the
    document link - must check out against the result the runner logged."""
    from linker_genie.agent import ToolBudget, _knowledge_runner
    from linker_genie.hydrate import hydrate
    from linker_genie.quality.citations import verify
    from linker_genie.quality.turns import LoggedTurn
    from linker_genie.schema import TextBlock, TurnOutput

    def search(arguments: dict[str, Any] | None) -> dict[str, Any]:
        tagged = "[n1=10 years] for units produced on/after [n2=1 st January 2026]"
        return {
            "ranking": "vector",
            "hits": [
                {
                    "chunk_id": "a786-p1-b113",
                    "doc_url": "https://de-linker.com/gw.pdf",
                    "title": "GoodWe-Garantie",
                    "page": 1,
                    "section": "",
                    "text": tagged,
                    "figures": {
                        "a786-p1-b113.n1": "10 years",
                        "a786-p1-b113.n2": "1 st January 2026",
                    },
                }
            ],
        }

    budget = ToolBudget()
    _knowledge_runner(search, budget, "de")({"query": "Garantie", "lang": "de"})
    output = TurnOutput(
        language="de",
        blocks=[
            TextBlock(
                text="Ab dem {fact:a786-p1-b113.n2} gelten {fact:a786-p1-b113.n1}.",
                refs=["a786-p1-b113"],
            )
        ],
    )
    shipped = hydrate(output, budget.facts())
    turn = LoggedTurn(
        id=1,
        conversation_id="c",
        created_at="2026-10-17 20:00:00",
        locale="de",
        fallback=False,
        tool_calls=budget.facts().tool_calls,
        output=shipped.model_dump(),
        question="Garantie?",
        page={},
    )

    assert shipped.blocks[0].text == "Ab dem 1. Januar 2026 gelten 10 Jahre."  # type: ignore[union-attr]
    assert shipped.blocks[1].model_dump()["label"] == "GoodWe-Garantie · S.\u00a01"
    assert verify(turn) == []
