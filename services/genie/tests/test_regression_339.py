"""#339 product-word cases, loaded from the regression file.

The rows are the fixture. This module only runs them.
docs/acceptance/2026-10-19/379/339-cases.md is the index.
"""

import json
from pathlib import Path
from typing import Any, Literal, cast

import pytest
from fastapi import Request

from linker_genie.app import _answer
from linker_genie.facts import Fact, TurnFacts, collect
from linker_genie.ground import Citation, check, cites_outside_turn
from linker_genie.jev import Reading
from linker_genie.language import clear_language
from linker_genie.lexicon import Vocabulary
from linker_genie.prices import Lookup
from linker_genie.route import NamedModel, Route, Subject, plan, with_page
from linker_genie.schema import (
    ActionBlock,
    AskBlock,
    CardsBlock,
    HandoffBlock,
    PageContext,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import DEGRADED, fallback, finish
from linker_genie.understand import Prepared

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
    "339-384-unknown-en",
    "339-384-unknown-de",
    "339-384-mix-en",
    "339-384-mix-de",
    "339-384-several-unknown-en",
    "339-384-cheapest-en",
    "339-384-cheapest-de",
    "339-384-applied-en",
    "339-384-applied-de",
    "339-384-hidden-en",
    "339-384-hidden-de",
    "339-384-hidden-omits-en",
    "339-384-hidden-omits-de",
    "339-11-en-out-visitor",
    "339-11-en-out-approved",
    "339-11-en-in-visitor",
    "339-11-en-in-approved",
    "339-11-de-out-visitor",
    "339-11-de-out-approved",
    "339-11-de-in-visitor",
    "339-11-de-in-approved",
    "339-11-failure",
    "339-f4-de",
    "339-396-im",
    "339-396-ins",
    "339-396-typ-a",
    "339-396-typ-a-short",
    "339-404-address",
    "339-396-document",
    "339-396-chunk",
    "339-396-product",
    "339-396-placeholder",
    "339-440-b30-en",
    "339-440-b30-de",
    "339-440-b43-en",
    "339-440-b43-de",
    "339-440-b44-en",
    "339-440-b44-de",
    "339-440-b07-en",
    "339-440-b07-de",
    "339-440-b08-en",
    "339-440-b08-de",
    "339-440-b06-de",
    "339-440-account-en",
    "339-440-account-de",
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
    if raw.get("price_hidden"):
        facts.add(
            Fact(id="search.extreme_price_hidden", value="1", source="search-products")
        )
    if "extreme_product_id" in raw:
        facts.add(
            Fact(
                id="search.extreme_product_id",
                value=str(raw["extreme_product_id"]),
                source="search-products",
            )
        )
    if "extreme_model" in raw:
        facts.add(
            Fact(
                id="search.extreme_model",
                value=str(raw["extreme_model"]),
                source="search-products",
            )
        )
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
    elif kind == "stock":
        _stock(row, vocabulary)
    elif kind == "language":
        _language(row)
    elif kind == "citation":
        _citation(row)
    elif kind == "signed":
        _signed(row, vocabulary)
    else:
        raise AssertionError(kind)


class _Model:
    """A generator that fails the test if the stock turn calls it."""

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("the model ran on a stock-status question")


class _Request:
    class app:  # noqa: N801 - the shape _answer reads is request.app.state
        class state:
            generate = _Model()


def _language(row: dict[str, Any]) -> None:
    assert clear_language(row["message"]) == row["expected"]


def _citation(row: dict[str, Any]) -> None:
    citation = Citation(row["citation_kind"], row["ref"])
    assert cites_outside_turn([citation]) is row["outside"]


def _plan(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    subject = _subject(vocabulary, row.get("subject_ids"))
    route = plan(
        row["message"],
        vocabulary.match(row["message"]),
        _reading(row["intent"], row["confidence"]),
        subject,
        row["lang"],
    )
    # These rows are the older product-word cases. A stock word inside a
    # document question stays on that route (#415 yields to documents_specs).
    assert route.stock is False
    if "max_calls" in row:
        assert len(route.calls) <= row["max_calls"]
    if row.get("named_empty"):
        assert route.named_models == ()
    if row.get("calls_empty"):
        assert route.calls == ()
    for banned in row.get("hint_excludes", []):
        assert banned not in route.hint
    for needle in row.get("hint_includes", []):
        assert needle in route.hint
    if "calls" in row:
        assert len(route.calls) == len(row["calls"])
        for call, expected in zip(route.calls, row["calls"], strict=True):
            assert call.ability == expected.get("ability", "linker/search-products")
            if expected.get("no_text"):
                assert "text" not in call.arguments
            for key, value in expected.items():
                if key in ("ability", "no_text"):
                    continue
                assert call.arguments.get(key) == value
    texts = [
        str(call.arguments.get("text"))
        for call in route.calls
        if call.ability == "linker/search-products"
    ]
    for code in row.get("text_absent", []):
        assert code not in texts
    for code in row.get("text_present", []):
        assert code in texts
    if row.get("brand_absent"):
        assert all(
            "brand" not in call.arguments
            for call in route.calls
            if call.ability == "linker/search-products"
        )
    if "note_codes" in row:
        assert [note.code for note in route.named_models] == row["note_codes"]
    for expected in row.get("notes", []):
        match = next(
            note for note in route.named_models if note.code == expected["code"]
        )
        assert match.searched is expected["searched"]
        if "unknown" in expected:
            assert match.unknown is expected["unknown"]
        if "written_brand" in expected:
            assert match.written_brand == expected["written_brand"]
        if "catalog_brand" in expected:
            assert match.catalog_brand == expected["catalog_brand"]
        if "product_ids" in expected:
            assert list(match.product_ids) == list(expected["product_ids"])
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


def _http() -> Request[Any]:
    """Enough of a request for a turn the service answers itself."""
    return cast(Request[Any], _Request())


def _turn(row: dict[str, Any]) -> TurnRequest:
    return TurnRequest(
        conversation_id="415",
        messages=[TurnMessage(role="user", content=row["message"])],
        locale=row["lang"],
    )


def _stock(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    """#415: the status sentence, the card, and no quantity."""
    route = plan(
        row["message"],
        vocabulary.match(row["message"]),
        _reading(row["intent"], row["confidence"]),
        _subject(vocabulary, None),
        row["lang"],
    )
    assert route.name == "products"
    assert route.stock is True
    assert route.no_handoff is True
    assert any(call.ability == "linker/search-products" for call in route.calls)
    assert all(call.ability != "linker/handoff-team" for call in route.calls)
    if row.get("failed"):
        result, block = _answer(
            _turn(row), Prepared(route=route), _http(), cast(Lookup, None)
        )
        assert block is None
        assert result.grounded is False
        assert result.fallback is True
        assert result.attempts == 0
        assert result.failures == ("stock status unavailable",)
        assert isinstance(result.output.blocks[0], HandoffBlock)
        assert result.output.blocks[0].summary == DEGRADED[row["lang"]]
        assert not any(isinstance(item, CardsBlock) for item in result.output.blocks)
        summary = result.output.blocks[0].summary
        assert "matching products" not in summary.casefold()
        assert "passende Produkte" not in summary
        return
    product_id = row["product_id"]
    facts = collect(
        "linker/search-products",
        {
            "qualified": [
                {
                    "product_id": product_id,
                    "title": "SAJ H2-10K-T3",
                    "url": "https://de-linker.com/product/saj-h2-10k-t3/",
                    "sku": "DLK-SAJ-H210KT3",
                    "facts": {},
                    "commerce": {
                        "price_visible": row["price_reason"] is None,
                        "in_stock": row["in_stock"],
                        "price_line": row["price_line"],
                        "price_reason": row["price_reason"],
                    },
                }
            ]
        },
        row["lang"],
    )
    assert facts.facts[f"p{product_id}.stock"].value == row["status"]
    result, block = _answer(
        _turn(row),
        Prepared(route=route, facts=facts),
        _http(),
        cast(Lookup, None),
    )
    assert block is None
    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 0
    assert result.failures == ()
    text = _sentence(result.output)
    assert text == row["status"]
    assert not any(character.isdigit() for character in text)
    for banned in (
        "quantity",
        "quantities",
        "units",
        "pieces",
        "stück",
        "lagerbestand",
    ):
        assert banned not in text.casefold()
    cards = [item for item in result.output.blocks if isinstance(item, CardsBlock)]
    assert len(cards) == 1
    assert cards[0].product_ids == [product_id]
    assert cards[0].prices is not None and len(cards[0].prices) == 1
    assert cards[0].prices[0].text == row["price_line"]
    assert cards[0].prices[0].reason == row["price_reason"]
    assert row["price_line"] not in text


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


def _signed(row: dict[str, Any], vocabulary: Vocabulary) -> None:
    """#440: the signed sentence beats a confident misreading, and only that row.

    A nearby question must not take the battery sentence. An account word
    without an inquiry noun must not take the open-inquiry sentence.
    """
    route = plan(
        row["message"],
        vocabulary.match(row["message"]),
        _reading(row["intent"], row["confidence"]),
        _subject(vocabulary, None),
        row["lang"],
    )
    if row["stamp"] == "none":
        assert route.name != "scripted"
        assert "esa battery" not in route.reasons
        return
    language: Literal["en", "de"] = "de" if row["lang"] == "de" else "en"
    assert route.answer == row["answer"]
    assert route.no_handoff is True
    if row["stamp"] == "scripted":
        assert route.name == "scripted"
        assert route.calls == ()
        assert route.no_cards is True
    else:
        assert row["stamp"] == "esa"
        assert "esa battery" in route.reasons
        assert route.name in ("products", "pairing", "model")
    finished = finish(
        TurnOutput(language=language, blocks=[TextBlock(text=row["prose"])]),
        TurnFacts(),
        route,
    )
    text = _sentence(finished)
    assert text == row["answer"]
    assert row["prose"] not in text
    for banned in row.get("excludes", []):
        assert banned not in text
    if row.get("action"):
        assert any(
            isinstance(block, ActionBlock) and block.name == row["action"]
            for block in finished.blocks
        )
    if row.get("ask"):
        assert any(isinstance(block, AskBlock) for block in finished.blocks)
    assert not any(isinstance(block, HandoffBlock) for block in finished.blocks)
