"""The in-process document search tool: its result, its errors, and what the model reads."""

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from test_publication import authority, manifest

import linker_genie.knowledge as knowledge
from linker_genie.embedding import EmbeddingError
from linker_genie.knowledge import (
    KnowledgeSearch,
    KnowledgeUnavailable,
    model_view,
    validate,
)
from linker_genie.retrieval import DocumentHit


@pytest.fixture(autouse=True)
def permission(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = manifest()
    raw["products"][0]["product_id"] = 3556
    monkeypatch.setattr(knowledge, "current", lambda: authority(raw))


@dataclass
class Encoder:
    model: str = "google/gemini-embedding-2"


@dataclass
class FakeIndex:
    """Answers `search` with one table chunk, or raises what it is told to."""

    error: Exception | None = None
    encoder: Encoder | None = field(default_factory=Encoder)
    version: str = "20261016T072222Z"
    source_revision: str = "source-1"
    calls: list[tuple[str, str, Any]] = field(default_factory=list)

    @property
    def ranking(self) -> str:
        return "vector" if self.encoder else "keywords"

    def search(
        self, query: str, lang: str, product_ids: Any = None, publication: Any = None
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
                "doc_type": "manual",
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


@pytest.mark.parametrize("language", ["en", "de"])
def test_original_etr_projection_reaches_the_customer_with_its_condition(
    language: str,
) -> None:
    """Use both original PDF/Docling pairs, through the real answer consumers."""
    from test_table_compiler_axis import etr_source, selected

    from linker_genie.cycle import run
    from linker_genie.ground import check
    from linker_genie.language import language_failure
    from linker_genie.quality.citations import verify
    from linker_genie.quality.turns import LoggedTurn
    from linker_genie.retrieval import Qualification
    from linker_genie.route import Route
    from linker_genie.schema import (
        DocumentBlock,
        TextBlock,
        TurnMessage,
        TurnOutput,
        TurnRequest,
    )

    manifest, original = etr_source(language)  # type: ignore[arg-type]
    compiled, proofs = selected(manifest, original)
    chunk = next(
        item
        for item in compiled
        if item.id in proofs
        and proofs[item.id]["basis"] == "table_projection"
        and proofs[item.id]["product_ids"] == [6507]
        and "125.7" in item.text
    )
    backup = next(
        item
        for item in compiled
        if item.id in proofs
        and proofs[item.id]["basis"] == "table_projection"
        and proofs[item.id]["product_ids"] == [6507]
        and "133.8" in item.text
        and "*3:" in item.text
    )
    document = manifest["documents"][0]
    hits = []
    for projection in (chunk, backup):
        proof_notes = proofs[projection.id]["table_projection"]["footnote_sources"]
        notes = tuple(
            Qualification(
                quote=note["quote"],
                page=note["page"],
                chunk_id=note["chunk_id"],
                lang=note["lang"],
            )
            for note in proof_notes
        )
        hits.append(
            DocumentHit(
                chunk_id=projection.id,
                doc_sha256=document["blob_sha256"],
                doc_url=document["url"],
                title=document["title"],
                doc_type="datasheet",
                page=projection.page,
                section=projection.section,
                text=projection.text,
                lang=language,
                score=1.0,
                product_ids=(6507,),
                qualifications=notes,
                qualification_required=True,
            )
        )

    class OriginalProjection(FakeIndex):
        def search(
            self,
            query: str,
            lang: str,
            product_ids: Any = None,
            publication: Any = None,
        ) -> list[DocumentHit]:
            return hits

    search = KnowledgeSearch(lambda: OriginalProjection(), authority(manifest))  # type: ignore[arg-type,return-value]
    payload, facts = knowledge.record(
        search,
        {"query": "battery current", "lang": language, "product_ids": [6507]},
        language,
    )
    result = payload["hits"][0]
    current_id = next(
        key for key, value in result["figures"].items() if value == "125.7 A"
    )
    power_id = next(
        key for key, value in result["figures"].items() if value == "88.0 kW"
    )
    backup_id = next(
        key
        for key, value in payload["hits"][1]["figures"].items()
        if value == "133.8 A"
    )
    assert "6" not in result["figures"].values()
    assert "3" not in result["figures"].values()  # markers and pages are not values
    assert hits[0].qualifications[0]["quote"] in result["text"]
    assert "qualification_required" not in model_view(payload)["hits"][0]
    prose = (
        f"Der Strom beträgt {{fact:{current_id}}}, die Leistung {{fact:{power_id}}} "
        f"und der Backup-Strom {{fact:{backup_id}}}."
        if language == "de"
        else f"The current is {{fact:{current_id}}}, the power is {{fact:{power_id}}} "
        f"and the backup current is {{fact:{backup_id}}}."
    )
    output = TurnOutput(
        language=language,  # type: ignore[arg-type]
        blocks=[TextBlock(text=prose, refs=[chunk.id, backup.id])],
    )
    assert check(output, facts).ok
    question = (
        "What are the battery and backup currents?"
        if language == "en"
        else "Wie hoch sind Batterie- und Backup-Strom?"
    )
    request = TurnRequest(
        conversation_id="fixture",
        locale=language,  # type: ignore[arg-type]
        messages=[TurnMessage(role="user", content=question)],
    )
    turn_result = run(
        request, lambda _request, _retry: (output, facts), Route("documents")
    )
    assert turn_result.grounded and not turn_result.fallback
    shipped = turn_result.output
    answer = shipped.blocks[0]
    assert isinstance(answer, TextBlock)
    for hit in hits:
        original_condition = hit.qualifications[0]["quote"].split(": ", 1)[1]
        assert answer.text.count(original_condition) == 1
    assert "125.7 A" in answer.text and "88.0 kW" in answer.text
    assert "133.8 A" in answer.text
    assert language_failure(shipped, language) is None  # type: ignore[arg-type]
    links = [block for block in shipped.blocks if isinstance(block, DocumentBlock)]
    assert [link.url for link in links] == [
        document["url"] + "#page=2",
        document["url"] + "#page=3",
    ]
    turn = LoggedTurn(
        id=1,
        conversation_id="fixture",
        created_at="2026-10-28 00:00:00",
        locale=language,
        fallback=False,
        tool_calls=facts.tool_calls,
        output=shipped.model_dump(),
        question=question,
        page={},
    )
    assert verify(turn) == []


def test_equal_numbers_do_not_make_two_language_hits_the_same_parameter() -> None:
    def qualified(lang: str) -> dict[str, Any]:
        quote = (
            "*6: Batterieseitige Parameter gelten nur für proprietäre Batteriesysteme "
            "oder DC/DC-unterstützte Batterieschnittstellen."
            if lang == "de"
            else "*6: Battery-side parameters are only applicable with proprietary battery "
            "systems or DC/DC-supported battery interface."
        )
        label = "Netzstrom" if lang == "de" else "Battery current"
        return {
            "chunk_id": f"{lang}-p2",
            "doc_url": f"https://de-linker.com/{lang}.pdf",
            "title": "ETR",
            "page": 2,
            "product_ids": [6507],
            "text": f"| {label} (A) | [n1=125.7 A] |\n{quote} (p. 3)",
            "figures": {f"{lang}-p2.n1": "125.7 A"},
            "qualification_required": True,
            "qualifications": [
                {"quote": quote, "page": 3, "chunk_id": f"{lang}-p3", "lang": lang}
            ],
        }

    unrelated = {"chunk_id": "other", "text": "A different source."}
    incoming = {"hits": [qualified("en"), unrelated, qualified("de")]}

    payload, _ = knowledge.record(
        lambda _: incoming, {"query": "q", "lang": "de"}, "de"
    )

    assert [hit["chunk_id"] for hit in payload["hits"]] == ["en-p2", "other", "de-p2"]


def test_search_hides_a_projection_with_its_condition_removed() -> None:
    hit = {
        "chunk_id": "etr-p2",
        "doc_url": "https://de-linker.com/etr.pdf",
        "page": 2,
        "text": "| Current (A) | [n1=125.7 A] |",
        "figures": {"etr-p2.n1": "125.7 A"},
        "qualification_required": True,
        "qualifications": [],
    }

    payload, facts = knowledge.record(lambda _: {"hits": [hit]}, {"query": "q"})

    assert payload["hits"] == []
    assert not facts.facts


def test_hca_filtered_rows_do_not_reappear_in_knowledge_facts(tmp_path: Path) -> None:
    """A local fixture index carries the real HCA table through the consumer."""
    from test_publication_columns import chunks, index
    from test_publication_columns import manifest as hca_manifest

    raw = hca_manifest()
    loaded = index(tmp_path, chunks())
    search = KnowledgeSearch(lambda: loaded, authority(raw))
    try:
        for query, ordinary in [
            ("Operating Temperature Range", "Over Temperature Protection"),
            ("Ingress Protection Rating", "Standby Power"),
        ]:
            payload, facts = knowledge.record(
                search, {"query": query, "lang": "en", "product_ids": [3586]}
            )
            text = "\n".join(hit["text"] for hit in payload["hits"])
            values = [
                fact.value
                for fact_id, fact in facts.facts.items()
                if fact_id.rpartition(".")[2].startswith("n")
            ]
            assert "Operating Temperature Range" not in text
            assert "Ingress Protection Rating" not in text
            assert "IP66" not in text
            assert all("-30" not in value and "+50" not in value for value in values)
            assert ordinary in text
    finally:
        loaded.close()
