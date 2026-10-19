"""#339 product-word cases, loaded from the regression file.

The rows are the fixture. This module only runs them.
docs/acceptance/2026-10-19/379/339-cases.md is the index.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from linker_genie.facts import TurnFacts
from linker_genie.ground import check
from linker_genie.jev import Reading
from linker_genie.lexicon import Vocabulary
from linker_genie.route import NamedModel, Route, Subject, plan, with_page
from linker_genie.schema import (
    CardsBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnOutput,
)
from linker_genie.template import DEGRADED, fallback

SET = (
    Path(__file__).resolve().parents[1]
    / "eval"
    / "regression"
    / "339-product-words.jsonl"
)
EXPECTED = (
    "339-1-en",
    "339-1-de",
    "339-2",
    "339-3",
    "339-4",
    "339-5-order",
    "339-5-dlk",
    "339-5-order-g20",
    "339-6",
    "339-7-en",
    "339-7-de",
    "339-8-split",
    "339-8-catalog-only",
    "339-8-pointed",
    "339-8-brands",
    "339-9-omitted",
    "339-9-mixed",
    "339-10-page",
)


def _rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SET.read_text().splitlines() if line.strip()]


def _reading(intent: str, confidence: float) -> Reading:
    return Reading(intent, confidence, 0.1, 0.05, 0.2, 2.6, 0.0)  # type: ignore[arg-type]


def _subject(vocabulary: Vocabulary, ids: list[int] | None) -> Subject:
    subject = Subject(
        tuple(ids or ()),
        vocabulary.device_class,
        vocabulary.labels,
        vocabulary.phase,
        vocabulary.series_members,
        brand_of={key: set(value) for key, value in vocabulary.brand_of.items()},
        brand_names=dict(vocabulary.brand_names),
        names=dict(vocabulary.names),
        catalog_models=vocabulary.model_codes(),
    )
    return subject


def _note(raw: dict[str, Any]) -> NamedModel:
    return NamedModel(
        code=raw["code"],
        product_ids=tuple(raw.get("product_ids", ())),
        searched=raw.get("searched", True),
        written_brand=raw.get("written_brand", ""),
        catalog_brand=raw.get("catalog_brand", ""),
        unknown=raw.get("unknown", False),
    )


def _calls(raw_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    built: list[dict[str, Any]] = []
    for raw in raw_calls:
        text = raw.get("text") or ""
        ids = raw.get("ids", [])
        arguments: dict[str, Any] = {"lang": "en", "limit": 6}
        if text:
            arguments["text"] = text
        built.append(
            {
                "name": "linker/search-products",
                "arguments": arguments,
                "ok": raw.get("ok", True),
                "result": {"qualified": [{"product_id": pid} for pid in ids]},
            }
        )
    return built


def _facts(raw: dict[str, Any]) -> TurnFacts:
    ids = list(raw.get("qualified", []))
    facts = TurnFacts()
    facts.product_ids = set(ids)
    facts.qualified_ids = set(ids)
    mode = raw.get("mode")
    if mode == "legacy":
        facts.tool_calls.append(
            {
                "name": "linker/search-products",
                "arguments": {},
                "ok": True,
                "result": {},
            }
        )
        return facts
    facts.tool_calls.extend(_calls(raw.get("calls", [])))
    return facts


def _sentence(output: TurnOutput) -> str:
    if output.blocks and isinstance(output.blocks[0], HandoffBlock):
        return output.blocks[0].summary
    return " ".join(
        block.text for block in output.blocks if isinstance(block, TextBlock)
    )


def test_the_fixture_lists_the_ticket_cases() -> None:
    assert [row["id"] for row in _rows()] == list(EXPECTED)


@pytest.mark.parametrize("row", _rows(), ids=[row["id"] for row in _rows()])
def test_339_product_word_case(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    kind = row["kind"]
    if kind == "plan":
        _plan(row, vocabulary)
    elif kind == "ground":
        _ground(row)
    elif kind == "fallback":
        _fallback(row)
    else:
        raise AssertionError(kind)


def _plan(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    subject = _subject(vocabulary, row.get("subject_ids"))
    route = plan(
        row["message"],
        vocabulary.match(row["message"]),
        _reading(row["intent"], row["confidence"]),
        subject,
        row["lang"],
    )
    if "max_calls" in row:
        assert len(route.calls) <= row["max_calls"]
    if row.get("named_empty"):
        assert route.named_models == ()
    if row.get("calls_empty"):
        assert route.calls == ()
    for banned in row.get("hint_excludes", []):
        assert banned not in route.hint
    texts = [
        str(call.arguments.get("text"))
        for call in route.calls
        if call.ability == "linker/search-products"
    ]
    for code in row.get("text_absent", []):
        assert code not in texts
    for code in row.get("text_present", []):
        assert code in texts
    if "note_codes" in row:
        assert [note.code for note in route.named_models] == row["note_codes"]
    for expected in row.get("notes", []):
        match = next(
            note for note in route.named_models if note.code == expected["code"]
        )
        assert match.searched is expected["searched"]
    if row.get("some_unsearched"):
        assert any(not note.searched for note in route.named_models)
    if row.get("searched_matches_calls"):
        fetched = {
            call.arguments.get("product_id")
            for call in route.calls
            if call.ability == "linker/get-product"
        }
        for note in route.named_models:
            covered = note.code in texts or any(
                pid in fetched for pid in note.product_ids
            )
            assert note.searched is covered
    if "page" in row:
        page = row["page"]
        paged = with_page(
            route,
            PageContext(
                type=page["type"], url=page["url"], product_id=page.get("product_id")
            ),
            True,
            False,
            subject,
            row["message"],
        )
        assert any(call.ability == row["page_ability"] for call in paged.calls)
        assert len(paged.calls) <= row["paged_max_calls"]
    if "fallback" in row:
        _check_fallback(route, row["fallback"], row["lang"])


def _ground(row: dict[str, Any]) -> None:
    notes = tuple(_note(raw) for raw in row["notes"])
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    facts = _facts(row)
    blocks: list[Any] = [TextBlock(text=row["text"], refs=row.get("refs", []))]
    if row.get("cards"):
        blocks.append(CardsBlock(product_ids=row["cards"]))
    output = TurnOutput(language=row["language"], blocks=blocks)
    result = check(output, facts, route)
    assert result.ok is row["expect_ok"]
    for needle in row.get("failure_has", []):
        assert any(needle in failure for failure in result.failures)


def _fallback(row: dict[str, Any]) -> None:
    notes = tuple(_note(raw) for raw in row["notes"])
    route = Route("products", show_products=True, no_handoff=True, named_models=notes)
    _check_fallback(route, row, row["lang"])


def _check_fallback(route: Route, raw: dict[str, Any], lang: str) -> None:
    facts = _facts(raw)
    output = fallback(facts, lang, route)
    if raw.get("expect_handoff"):
        assert isinstance(output.blocks[0], HandoffBlock)
        assert output.blocks[0].summary == DEGRADED[lang]
    text = _sentence(output)
    for needle in raw.get("contains", []):
        assert needle in text
    for needle in raw.get("excludes", []):
        assert needle not in text
    if "cards" in raw:
        cards = [block for block in output.blocks if isinstance(block, CardsBlock)]
        assert cards and cards[0].product_ids == raw["cards"]
