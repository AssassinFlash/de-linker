"""A failed turn says it failed (#410, #332 D1/D2).

The #339 rows (issue 410) run the exception the catch site raises. A logged
string is not classified again, and a class name in the sentence is not a class.
"""

from __future__ import annotations

import functools
import io
import json
import sqlite3
import urllib.error
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from baseline.grade import NEXT_STEP_BLOCKS
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

from linker_genie.abilities import Abilities, AbilityClient, AbilityError
from linker_genie.cycle import TurnResult, fatal_class, run
from linker_genie.embedding import EmbeddingError, GeminiEmbedder
from linker_genie.facts import Document, Fact, TurnFacts, collect
from linker_genie.failure import from_log, kind_of, note
from linker_genie.jev import Reading
from linker_genie.knowledge import KnowledgeSearch, KnowledgeUnavailable
from linker_genie.lexicon import Vocabulary
from linker_genie.page import PageUnavailable
from linker_genie.route import Route
from linker_genie.schema import (
    CardsBlock,
    DocumentBlock,
    HandoffBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    DOCUMENTS,
    LOGIN_REQUIRED,
    PARTNER,
    PROMISE,
    REPLY_PROMISE,
    TALK,
    fallback,
    finish,
    german_is_clean,
)
from linker_genie.understand import Understander

_STOCK = (1179, 1181, 2063, 2064, 4107, 4108)
_PRODUCTS = Route("products", show_products=True, no_handoff=True)
_DOCUMENTS = Route("documents", no_handoff=True)
_SALES = "Our team will answer that at sales@de-linker.com."
_SALES_DE = "Unser Team beantwortet das unter sales@de-linker.com."
_MATCHING = {
    "en": "Here are matching products from our range.",
    "de": "Hier sind passende Produkte aus unserem Sortiment.",
}
_FORBIDDEN = (
    _MATCHING["en"],
    _MATCHING["de"],
    DOCUMENTS["en"],
    DOCUMENTS["de"],
    "sales@de-linker.com",
)
# The probe from review round 2. The embedder's own unexpected-response
# error is a KeyError; this sentence is what that probe raised.
_REVIEW_UNEXPECTED = (
    "linker/search-knowledge: gemini-embedding-2: "
    "unexpected response (ValueError: bad data)"
)
_PDF = "https://de-linker.com/wp-content/uploads/2026/03/SAJ-H2-user-manual.pdf"
_MANIFEST = Path(__file__).parent / "fixtures" / "339" / "manifest.json"
_REQUIRED = (
    "410-m500",
    "410-m-empty",
    "410-m-429",
    "410-m500-doc",
    "410-idx-miss",
    "410-idx-bad",
    "410-ab-500",
    "410-ab-timeout",
    "410-encoder-http",
    "410-encoder-transport",
    "410-encoder-unexpected",
    "410-encoder-count",
    "410-degraded-no-cards",
)

Generate = Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]


class _FailingApi:
    """Raises `error` from every embeddings request."""

    def __init__(self, error: Exception) -> None:
        self.error = error

    @contextmanager
    def __call__(self, request: object, timeout: float) -> Iterator[io.BytesIO]:
        del request, timeout
        raise self.error
        yield io.BytesIO()  # pragma: no cover - the raise ends the call


class _Body:
    """Returns one embeddings body and does not retry."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    @contextmanager
    def __call__(self, request: object, timeout: float) -> Iterator[io.BytesIO]:
        del request, timeout
        yield io.BytesIO(self.raw)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://a.example", code, "x", {}, None)  # type: ignore[arg-type]


@functools.cache
def _encoder(kind: str) -> EmbeddingError:
    """The exception `GeminiEmbedder.embed_query` raises for `kind`."""
    if kind == "http":
        urlopen: Callable[..., Any] = _FailingApi(_http_error(502))
    elif kind == "transport":
        urlopen = _FailingApi(urllib.error.URLError("connection refused"))
    elif kind == "unexpected":
        urlopen = _Body(json.dumps({"error": "no data"}).encode())
    elif kind == "count":
        urlopen = _Body(json.dumps({"data": []}).encode())
    else:
        raise AssertionError(kind)
    try:
        GeminiEmbedder(
            "k", "https://a.example", urlopen=urlopen, sleep=lambda _: None
        ).embed_query("q")
    except EmbeddingError as error:
        return error
    raise AssertionError(kind)


@functools.cache
def _ability(kind: str) -> AbilityError:
    """A 500 or a transport failure from `AbilityClient.run`."""

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        if kind == "timeout":
            raise httpx.ConnectError("timed out")
        return httpx.Response(500, json={"message": "boom"})

    client = AbilityClient(
        "http://abilities.test",
        transport=httpx.MockTransport(handler),
        sleep=lambda _: None,
    )
    try:
        client.run("linker/search-products", {"series": "saj-h2"})
    except AbilityError as error:
        return error
    raise AssertionError(kind)


@functools.cache
def _index(message: str) -> KnowledgeUnavailable:
    """The exception `KnowledgeSearch` raises for an unreadable index."""

    class Broken:
        def search(
            self, query: str, lang: str, product_ids: object = None
        ) -> list[object]:
            del query, lang, product_ids
            raise sqlite3.OperationalError(message)

    try:
        KnowledgeSearch(lambda: Broken())(  # type: ignore[arg-type,return-value]
            {"query": "q", "lang": "en"}
        )
    except KnowledgeUnavailable as error:
        return error
    raise AssertionError(message)


def _model(status: int) -> ModelHTTPError:
    return ModelHTTPError(
        status,
        "deepseek-flash",
        {"message": f"injected chat {status}", "type": "server_error"},
    )


def _empty_stream() -> UnexpectedModelBehavior:
    # OpenAIChatModel._process_response, an empty stream.
    return UnexpectedModelBehavior(
        "Invalid response from deepseek chat completions endpoint: "
        "1 validation error for ChatCompletion"
    )


def _ability_note(kind: str) -> dict[str, str]:
    return note(_ability(kind), prefix="linker/search-products").dump()


def _question(language: Locale, *, documents: bool = False) -> TurnRequest:
    if documents:
        content = (
            "Wie hoch ist der maximale PV-Eingang des SAJ H2-10K-T2?"
            if language == "de"
            else "What is the maximum PV input of the SAJ H2-10K-T2?"
        )
    else:
        content = (
            "Haben Sie den SAJ H2-10K-T2 auf Lager?"
            if language == "de"
            else "Do you stock the SAJ H2-10K-T2?"
        )
    return TurnRequest(
        conversation_id="c332",
        locale=language,
        messages=[TurnMessage(role="user", content=content)],
    )


def _stock() -> TurnFacts:
    facts = TurnFacts()
    facts.qualified_ids = set(_STOCK)
    facts.product_ids = set(_STOCK)
    return facts


def _manual() -> TurnFacts:
    facts = TurnFacts()
    facts.chunk_ids = {"k1"}
    facts.documents["k1"] = Document(url=_PDF, title="SAJ H2 user manual", page=8)
    return facts


def _raise(error: BaseException) -> Generate:
    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        raise error

    return generate


def _locale(value: object) -> Locale:
    if value != "en" and value != "de":
        raise AssertionError(value)
    return value


def _sentence(output: TurnOutput) -> str:
    block = output.blocks[0]
    if isinstance(block, HandoffBlock):
        return block.summary
    if isinstance(block, TextBlock):
        return block.text
    return ""


def _visible(output: TurnOutput) -> str:
    parts: list[str] = []
    for block in output.blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
        elif isinstance(block, HandoffBlock):
            parts.append(block.summary)
        elif isinstance(block, DocumentBlock) and block.label:
            parts.append(block.label)
    return "\n".join(parts)


def _assert_degraded(output: TurnOutput, language: Locale) -> None:
    assert _sentence(output) == DEGRADED[language]
    visible = _visible(output)
    for forbidden in _FORBIDDEN:
        assert forbidden not in visible, forbidden
    if language == "de":
        assert german_is_clean(_sentence(output))


def _cards(output: TurnOutput) -> list[CardsBlock]:
    return [block for block in output.blocks if isinstance(block, CardsBlock)]


def _scenario(name: str, language: Locale) -> TurnResult:
    request = _question(language, documents=name == "m500-doc")
    if name == "m500":
        return run(request, _raise(_model(500)), route=_PRODUCTS, seed=_stock())
    if name == "m-empty":
        return run(request, _raise(_empty_stream()), route=_PRODUCTS, seed=_stock())
    if name == "m-429":
        return run(request, _raise(_model(429)), route=_PRODUCTS, seed=_stock())
    if name == "m500-doc":
        return run(request, _raise(_model(500)), route=_DOCUMENTS, seed=_manual())
    # These stock questions use the native products route. A documents route
    # without show_products must not display cards, even on an index failure.
    if name == "idx-miss":
        return run(
            request,
            _raise(_index("unable to open database file")),
            route=_PRODUCTS,
            seed=_stock(),
        )
    if name == "idx-bad":
        return run(
            request,
            _raise(_index("file is not a database")),
            route=_PRODUCTS,
            seed=_stock(),
        )
    if name == "ab-500":
        return run(
            request,
            _handoff(language),
            route=_PRODUCTS,
            call_failures=(_ability_note("500"),),
        )
    if name == "ab-timeout":
        return run(
            request,
            _handoff(language),
            route=_PRODUCTS,
            call_failures=(_ability_note("timeout"),),
        )
    if name.startswith("encoder-"):
        return run(
            request,
            _raise(_encoder(name.removeprefix("encoder-"))),
            route=_PRODUCTS,
            seed=_stock(),
        )
    if name == "degraded-no-cards":
        return run(request, _raise(_ability("500")), route=_PRODUCTS)
    raise AssertionError(name)


@pytest.mark.parametrize("language", ["en", "de"])
def test_index_outage_stock_fixture_uses_the_native_products_route(
    language: Locale, vocabulary: Vocabulary
) -> None:
    """The old hard-coded documents route contradicted these stock questions."""

    class StockReading:
        def read(
            self,
            message: str,
            page: dict[str, Any],
            history: Sequence[tuple[str, str]] = (),
        ) -> Reading:
            # A product-availability reading exercises the native planner,
            # vocabulary and abilities without a model request.
            return Reading("find_products", 0.99, 0.1, 0.05, 0.2, 0.0, 0.0)

    client = AbilityClient(
        "http://site.test",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"result": {"qualified": [{"product_id": pid} for pid in _STOCK]}},
            )
        ),
    )
    request = _question(language)
    prepared = Understander(lambda: vocabulary, StockReading()).prepare(request, client)
    assert prepared.route.name == "products"
    assert prepared.route.show_products
    assert not any(
        call.ability.endswith("search-knowledge") for call in prepared.route.calls
    )
    result = run(
        request,
        _raise(_index("unable to open database file")),
        route=prepared.route,
        seed=_stock(),
    )
    assert result.fallback
    _assert_degraded(result.output, language)
    assert set(_cards(result.output)[0].product_ids) == set(_STOCK)


def _cases_410() -> list[dict[str, Any]]:
    payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    cases = [item for item in payload["cases"] if item.get("issue") == 410]
    found = {item["id"] for item in cases}
    missing = [item_id for item_id in _REQUIRED if item_id not in found]
    if missing:
        raise AssertionError(f"missing #410 rows: {missing}")
    return cases


def test_real_exceptions_carry_their_class() -> None:
    """The class is the exception's, including the two encoder forms."""
    unexpected = _encoder("unexpected")
    counted = _encoder("count")
    assert "unexpected response" in str(unexpected)
    assert "embeddings for" in str(counted)
    for kind in ("http", "transport", "unexpected", "count"):
        assert kind_of(_encoder(kind)) == "retrieval"
    assert kind_of(EmbeddingError("not a known sentence")) == "retrieval"
    assert _ability("500").fatal is True
    assert kind_of(_ability("500")) == "ability"
    assert "returned 500" in str(_ability("500"))
    assert _ability("timeout").fatal is True
    assert kind_of(_ability("timeout")) == "ability"
    assert kind_of(_index("unable to open database file")) == "retrieval"
    assert kind_of(_index("file is not a database")) == "retrieval"
    assert kind_of(_model(500)) == "model"
    assert kind_of(_model(429)) == "model"
    assert kind_of(_model(400)) is None
    assert kind_of(_empty_stream()) == "model"
    exhausted = UnexpectedModelBehavior("Tool 'x' exceeded max retries count of 2")
    assert kind_of(exhausted) is None
    assert kind_of(AbilityError("returned 404", fatal=False)) is None
    assert kind_of(PageUnavailable("page /blog/x/ returned 500")) is None
    assert kind_of(RuntimeError("EmbeddingError: not a known sentence")) is None
    assert kind_of(RuntimeError("KnowledgeUnavailable: locked")) is None


def test_the_first_fatal_kind_wins_and_every_class_uses_one_sentence() -> None:
    """Nothing ranks the three classes. The template sentence does not either."""
    retrieval = note(_encoder("unexpected"))
    ability = note(_ability("500"))
    model = note(_model(500))
    assert fatal_class((retrieval, ability, model)) == "retrieval"
    assert fatal_class((ability, retrieval)) == "ability"
    assert fatal_class((model, ability)) == "model"
    for failure_class in ("model", "retrieval", "ability"):
        output = fallback(_stock(), "en", _PRODUCTS, failure_class=failure_class)
        assert _sentence(output) == DEGRADED["en"]
        assert _cards(output)


def test_the_review_encoder_sentences_degrade_a_products_turn() -> None:
    """Round 2: both real forms, the probe sentence, and the re-raised index error."""
    counted = _encoder("count")
    unexpected = _encoder("unexpected")
    prefixed_count = f"linker/search-knowledge: {counted}"
    cases: tuple[BaseException, ...] = (
        unexpected,
        counted,
        RuntimeError(_REVIEW_UNEXPECTED),
        RuntimeError(prefixed_count),
        KnowledgeUnavailable(f"linker/search-knowledge: {unexpected}"),
        KnowledgeUnavailable(prefixed_count),
        EmbeddingError("not a known sentence"),
    )
    for error in cases:
        assert kind_of(error) == "retrieval", error
        for language in ("en", "de"):
            result = run(
                _question(language),
                _raise(error),
                route=_PRODUCTS,
                seed=_stock(),
            )
            assert result.fallback is True
            _assert_degraded(result.output, language)
            cards = _cards(result.output)
            assert cards and set(cards[0].product_ids) == set(_STOCK)


def test_a_logged_string_is_not_reread_as_a_class() -> None:
    """`from_log` keeps a string's words and does not give them a class."""
    assert from_log(_REVIEW_UNEXPECTED).kind is None
    assert (
        from_log("EmbeddingError: gemini-embedding-2: HTTP 502 on attempt 2 of 2").kind
        is None
    )
    assert (
        from_log("KnowledgeUnavailable: document index unavailable: locked").kind
        is None
    )
    assert kind_of(RuntimeError(_REVIEW_UNEXPECTED)) == "retrieval"
    result = run(
        _question("en"),
        _raise(ValueError("not a TurnOutput")),
        route=_PRODUCTS,
        seed=_stock(),
        call_failures=(_REVIEW_UNEXPECTED,),
    )
    assert result.fallback is True
    assert _sentence(result.output) == _MATCHING["en"]


def test_a_class_name_in_the_sentence_is_not_a_failed_turn() -> None:
    result = run(
        _question("en"),
        _raise(RuntimeError("EmbeddingError: not a known sentence")),
        route=_PRODUCTS,
        seed=_stock(),
    )
    assert result.fallback is True
    assert _sentence(result.output) == _MATCHING["en"]


def test_a_recorded_note_keeps_its_class_when_the_wrapper_loses_the_type() -> None:
    """The tool wrote the class, then a wrapper raised the same sentence."""
    dumped = note(
        EmbeddingError("not a known sentence"), prefix="linker/search-knowledge"
    ).dump()
    recorded = [dumped]

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        if len(recorded) == 1:
            recorded.append(dumped)
        raise RuntimeError(dumped["text"])

    result = run(
        _question("en"),
        generate,
        route=_PRODUCTS,
        seed=_stock(),
        call_failures=recorded,
    )
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    assert kind_of(RuntimeError(dumped["text"])) is None


def test_issue_410_rows_in_the_339_manifest() -> None:
    """Every #410 row in the #339 manifest runs, in both languages."""
    for case in _cases_410():
        assert set(case["locales"]) == {"en", "de"}
        for language in (_locale(item) for item in case["locales"]):
            result = _scenario(case["scenario"], language)
            assert result.fallback is True
            _assert_degraded(result.output, language)
            cards = _cards(result.output)
            documents = [
                block
                for block in result.output.blocks
                if isinstance(block, DocumentBlock)
            ]
            if case["cards"]:
                assert cards and set(cards[0].product_ids) == set(_STOCK)
            else:
                assert not cards
            if case["documents"]:
                assert documents and documents[0].url
            else:
                assert not documents
            if case["scenario"] == "degraded-no-cards":
                # Gate 6 counts a handoff. The block is a paragraph
                # (Handoff.tsx); a clickable control is #394.
                types = {block.type for block in result.output.blocks}
                assert types == {"handoff"}
                assert types & set(NEXT_STEP_BLOCKS)


def test_a_page_outage_stays_a_normal_fallback() -> None:
    """read-page 500 is not an ability failure. A grounding miss still matches."""
    page = note(
        PageUnavailable("page /blog/x/ returned 500"), prefix="linker/read-page"
    )
    ability = note(_ability("500"), prefix="linker/search-products")
    assert page.kind is None
    assert "kind" not in page.dump()
    assert fatal_class((page, ability)) == "ability"
    assert fatal_class((ability, page)) == "ability"
    facts = _stock()

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text="This inverter is 10 kW.", refs=["1179"])],
            ),
            facts,
        )

    for language in ("en", "de"):
        result = run(
            _question(language),
            generate,
            route=_PRODUCTS,
            seed=facts,
            call_failures=(page.dump(),),
        )
        assert result.fallback is True
        assert _sentence(result.output) == _MATCHING[language]


def test_a_language_repair_does_not_hide_a_route_ability_failure() -> None:
    """The last line is a language re-ask. The route 500 is still fatal."""
    facts = _stock()

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="These are the products from the search.",
                        refs=[str(product_id) for product_id in _STOCK],
                    ),
                    CardsBlock(product_ids=list(_STOCK)),
                ],
            ),
            facts,
        )

    result = run(
        _question("de"),
        generate,
        route=_PRODUCTS,
        seed=facts,
        call_failures=(_ability_note("500"),),
    )
    assert result.fallback is True
    assert result.failures[0].startswith("answer in ")
    _assert_degraded(result.output, "de")


def _mailbox_answer(text: str, refs: list[str]) -> Generate:
    """A text block that would hydrate to the sales mailbox, or already is it."""

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        facts = TurnFacts()
        facts.add(Fact(id="handoff.sentence_en", value=_SALES, source="handoff-team"))
        facts.add(Fact(id="handoff.sentence", value=_SALES, source="handoff-team"))
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text=text, refs=list(refs))],
            ),
            facts,
        )

    return generate


def test_a_tool_failure_in_a_text_block_is_not_the_sales_mailbox() -> None:
    """The mailbox is the hydrated sentence, not the block class.

    `{fact:handoff.sentence}` inside a TextBlock hydrates to the sales
    sentence (hydrate.py). The literal sentence does too. Both routes
    that can ground that block — model, and products — declare the failure.
    """
    recorded = _ability_note("500")
    routes = (
        Route("model"),
        Route("products", show_products=True, no_handoff=True),
    )
    forms: tuple[tuple[str, list[str]], ...] = (
        ("{fact:handoff.sentence}", ["handoff.sentence"]),
        (_SALES, ["handoff.sentence"]),
        (_SALES, []),
    )
    for route in routes:
        for text, refs in forms:
            result = run(
                _question("en"),
                _mailbox_answer(text, refs),
                route=route,
                call_failures=(recorded,),
            )
            assert result.fallback is True
            assert result.grounded is False
            assert result.failures
            assert recorded["text"] in result.failures
            _assert_degraded(result.output, "en")
            assert not _cards(result.output)


def _grounded_product(
    request: TurnRequest, retry: str | None
) -> tuple[TurnOutput, TurnFacts]:
    """A products answer grounded on one qualified card, with no handoff."""
    del request, retry
    facts = TurnFacts()
    facts.qualified_ids = {1179}
    facts.product_ids = {1179}
    facts.add(Fact(id="p1179.title", value="hybrid inverter", source="get-product"))
    return (
        TurnOutput(
            language="en",
            blocks=[
                TextBlock(
                    text="The {fact:p1179.title} is in stock.",
                    refs=["1179", "p1179.title"],
                ),
                CardsBlock(product_ids=[1179]),
            ],
        ),
        facts,
    )


def test_a_grounded_product_answer_declares_a_recorded_fatal_failure() -> None:
    """Ability 5xx, timeout, and a retrieval failure are not a normal match.

    The model grounded on the product fact and the card. The customer
    sentence is still the reviewed degraded line, and the card stays.
    """
    retrieval = note(_encoder("unexpected"), prefix="linker/search-knowledge").dump()
    cases = (
        _ability_note("500"),
        _ability_note("timeout"),
        retrieval,
    )
    for recorded in cases:
        result = run(
            _question("en"),
            _grounded_product,
            route=_PRODUCTS,
            call_failures=(recorded,),
        )
        assert result.fallback is True
        assert result.grounded is False
        assert recorded["text"] in result.failures
        _assert_degraded(result.output, "en")
        cards = _cards(result.output)
        assert cards and cards[0].product_ids == [1179]


def test_a_grounded_document_answer_keeps_the_link_under_a_fatal_failure() -> None:
    """The document link stays. The success sentence does not."""

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        facts = TurnFacts()
        facts.chunk_ids = {"k1"}
        facts.documents["k1"] = Document(url=_PDF, title="SAJ H2 user manual", page=8)
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="The manual has the steps.", refs=["k1"]),
                    DocumentBlock(ref="k1"),
                ],
            ),
            facts,
        )

    result = run(
        _question("en"),
        generate,
        route=_DOCUMENTS,
        call_failures=(_ability_note("500"),),
    )
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    documents = [
        block for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert documents and documents[0].url == _PDF + "#page=8"


def test_a_model_tool_failure_cannot_become_the_sales_sentence() -> None:
    """search-products 500, then handoff-team, on a model route.

    The note is appended during generate, the way the runner writes
    `prepared.log["call_failures"]`. The handoff would otherwise ground.
    """
    recorded: list[object] = []

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        if not recorded:
            recorded.append(_ability_note("500"))
        return _handoff("en")(request, retry)

    result = run(
        _question("en"), generate, route=Route("model"), call_failures=recorded
    )
    assert result.fallback is True
    assert result.grounded is False
    _assert_degraded(result.output, "en")
    assert any("returned 500" in item for item in result.failures)


def test_a_raised_ability_failure_then_handoff_is_not_the_sales_sentence() -> None:
    """The runner re-raises `AbilityError`. The retry's handoff does not ship."""
    calls = {"n": 0}

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _ability("500")
        return _handoff("en")(request, retry)

    result = run(_question("en"), generate, route=Route("model"))
    assert calls["n"] == 2
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    assert any("returned 500" in item for item in result.failures)


def test_a_bare_ability_sentence_is_not_a_class() -> None:
    """A wrapper that kept only the words, and no note, is not an ability failure."""
    calls = {"n": 0}

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("linker/search-products returned 500 for {}")
        return _handoff("en")(request, retry)

    result = run(_question("en"), generate, route=Route("model"))
    assert calls["n"] == 2
    assert result.grounded is True
    assert _sentence(result.output) == _SALES


def test_a_recovered_model_error_may_still_hand_off() -> None:
    """A chat 500 the retry replaced is not a tool failure."""
    calls = {"n": 0}

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _model(500)
        return _handoff("en")(request, retry)

    result = run(_question("en"), generate, route=Route("model"))
    assert calls["n"] == 2
    assert result.grounded is True
    assert result.fallback is False
    assert _sentence(result.output) == _SALES
    assert result.failures == ()


def test_a_model_route_handoff_without_a_tool_failure_ships() -> None:
    result = run(_question("en"), _handoff("en"), route=Route("model"))
    assert result.grounded is True
    assert _sentence(result.output) == _SALES


def test_answer_passes_call_failures_into_the_run() -> None:
    """AB-500: `prepared.log["call_failures"]` reaches `cycle.run` via `_answer`."""
    from starlette.requests import Request

    from linker_genie.app import _answer, app
    from linker_genie.understand import Prepared

    recorded = _ability_note("500")
    prepared = Prepared(route=_PRODUCTS, log={"call_failures": [recorded]})
    app.state.generate = _handoff("en")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/turn",
        "raw_path": b"/turn",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 0),
        "server": ("test", 80),
        "app": app,
    }
    try:
        result, block = _answer(
            _question("en"),
            prepared,
            Request(scope),
            lambda _ids: (TurnFacts(), []),
            abilities=cast(Abilities, None),
        )
    finally:
        del app.state.generate
    assert block is None
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    assert any("not a question for the team" in item for item in result.failures)
    assert prepared.log["call_failures"] == [recorded]


def test_a_later_language_miss_is_not_declared_a_model_outage() -> None:
    """Attempt 1 is a 500. Attempt 2 grounds in the wrong language.

    The template repairs the language (#374). It does not tell the customer
    the turn failed.
    """
    facts = _stock()
    calls = {"n": 0}

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise _model(500)
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text="These are the products from the search.",
                        refs=[str(product_id) for product_id in _STOCK],
                    ),
                    CardsBlock(product_ids=list(_STOCK)),
                ],
            ),
            facts,
        )

    result = run(_question("de"), generate, route=_PRODUCTS, seed=facts)
    assert result.fallback is True
    assert calls["n"] == 2
    assert result.failures[0].startswith("answer in ")
    assert _sentence(result.output) == _MATCHING["de"]


def test_a_grounding_miss_keeps_the_recommendation_sentence() -> None:
    """A bare number is not a fatal failure. The qualified cards stay a match."""
    facts = _stock()

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text="This inverter is 10 kW.", refs=["1179"])],
            ),
            facts,
        )

    for language in ("en", "de"):
        result = run(_question(language), generate, route=_PRODUCTS, seed=facts)
        assert result.fallback is True
        assert _sentence(result.output) == _MATCHING[language]
        cards = _cards(result.output)
        assert cards and set(cards[0].product_ids) == set(_STOCK)


def test_a_person_route_is_not_a_fallback_mailbox() -> None:
    """A request for a person is answered in app._answer, before this template."""
    facts = TurnFacts()
    facts.add(Fact(id="handoff.sentence_en", value=_SALES, source="handoff-team"))
    output = fallback(facts, "en", Route("person"), failure_class="ability")
    assert isinstance(output.blocks[0], HandoffBlock)
    assert output.blocks[0].summary == DEGRADED["en"]


def test_a_fatal_products_turn_does_not_borrow_unqualified_ids() -> None:
    """#366 still holds under a fatal class: product 3608 is not a match."""
    facts = TurnFacts()
    facts.product_ids = {3608}
    output = fallback(facts, "en", _PRODUCTS, failure_class="model")
    assert isinstance(output.blocks[0], HandoffBlock)
    assert output.blocks[0].summary == DEGRADED["en"]
    assert not _cards(output)


def test_exhaustion_still_ships_no_cards_when_a_class_is_also_set() -> None:
    facts = TurnFacts()
    facts.qualified_ids = {3608}
    output = fallback(
        facts,
        "en",
        _PRODUCTS,
        exhausted=True,
        failure_class="ability",
    )
    assert len(output.blocks) == 1
    handoff = output.blocks[0]
    assert isinstance(handoff, HandoffBlock)
    assert handoff.summary == DEGRADED["en"]


def test_login_outranks_a_model_failure() -> None:
    guest = collect("linker/inquiry-status", {"error": "login_required"})
    guest.qualified_ids = {1179}
    output = fallback(guest, "en", _PRODUCTS, failure_class="model")
    assert isinstance(output.blocks[0], TextBlock)
    assert output.blocks[0].text == LOGIN_REQUIRED["en"]


def test_login_still_outranks_a_recorded_ability_failure() -> None:
    """A grounded login sentence is not replaced by the degraded line."""
    guest = collect("linker/inquiry-status", {"error": "login_required"})

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[TextBlock(text=LOGIN_REQUIRED["en"])],
            ),
            guest,
        )

    result = run(
        TurnRequest(
            conversation_id="c-guest",
            locale="en",
            messages=[
                TurnMessage(role="user", content="Where does my Proforma stand?")
            ],
        ),
        generate,
        route=_PRODUCTS,
        seed=guest,
        call_failures=(_ability_note("500"),),
    )
    assert result.fallback is True
    assert len(result.output.blocks) == 1
    block = result.output.blocks[0]
    assert isinstance(block, TextBlock)
    assert block.text == LOGIN_REQUIRED["en"]


def _handoff(language: Locale) -> Generate:
    sentence = _SALES_DE if language == "de" else _SALES
    side: Locale = language

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        facts = TurnFacts()
        facts.add(
            Fact(
                id=f"handoff.sentence_{side}",
                value=sentence,
                source="handoff-team",
            )
        )
        facts.add(Fact(id="handoff.sentence", value=sentence, source="handoff-team"))
        return (
            TurnOutput(
                language=language,
                blocks=[HandoffBlock(summary=sentence)],
            ),
            facts,
        )

    return generate


_SHAPED = {
    "talk": Route("model", shape="talk", no_handoff=True, no_cards=True),
    "promise": Route("model", shape="promise", no_handoff=True, no_cards=True),
    "partner": Route("model", shape="partner", no_handoff=True, no_cards=True),
    "service": Route("service"),
}
_SIGNED = {"talk": TALK, "promise": PROMISE, "partner": PARTNER}


def test_a_fatal_failure_outranks_a_signed_next_step() -> None:
    """talk, promise, partner and service must not rewrite the degraded sentence.

    finish used to replace the degraded handoff with the signed sentence, or
    append the reply promise on a service turn. The failure sentence stays,
    and a second finish does not grow a next step onto it.
    """
    for language in ("en", "de"):
        for name, route in _SHAPED.items():
            result = run(_question(language), _raise(_ability("500")), route)
            assert result.fallback is True
            assert result.grounded is False
            _assert_degraded(result.output, language)
            assert [block.type for block in result.output.blocks] == ["handoff"]
            visible = _visible(result.output)
            assert REPLY_PROMISE[language] not in visible
            signed = _SIGNED.get(name)
            if signed is not None:
                assert signed[language] not in visible
            assert finish(result.output, TurnFacts(), route) == result.output


def test_a_fatal_shaped_turn_keeps_findings_under_the_degraded_sentence() -> None:
    """Qualified cards stay. The signed sentence does not replace the handoff."""
    route = _SHAPED["talk"]
    result = run(_question("en"), _raise(_ability("500")), route, seed=_stock())
    _assert_degraded(result.output, "en")
    cards = _cards(result.output)
    assert cards and set(cards[0].product_ids) == set(_STOCK)
    assert TALK["en"] not in _visible(result.output)
    service = run(
        _question("en"), _raise(_model(500)), _SHAPED["service"], seed=_stock()
    )
    _assert_degraded(service.output, "en")
    assert REPLY_PROMISE["en"] not in _visible(service.output)
    kept = _cards(service.output)
    assert kept and set(kept[0].product_ids) == set(_STOCK)


def test_an_unclassed_exception_on_a_shaped_route_stays_degraded() -> None:
    """kind_of(RuntimeError) is None. The signed sentence must not hide that."""
    assert kind_of(RuntimeError("boom")) is None
    for language in ("en", "de"):
        for name, route in _SHAPED.items():
            result = run(_question(language), _raise(RuntimeError("boom")), route)
            assert result.fallback is True
            assert result.failures == ("boom",)
            _assert_degraded(result.output, language)
            assert REPLY_PROMISE[language] not in _visible(result.output)
            signed = _SIGNED.get(name)
            if signed is not None:
                assert signed[language] not in _visible(result.output)


def test_a_grounding_miss_on_a_shaped_route_still_ships_the_signed_sentence() -> None:
    """The shape is owed when the model answered and grounding refused it."""

    def generate(
        _request: TurnRequest, _retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        return (
            TurnOutput(
                language="en",
                blocks=[HandoffBlock(summary="Please write to sales@de-linker.com.")],
            ),
            TurnFacts(),
        )

    talk = run(_question("en"), generate, _SHAPED["talk"])
    assert talk.fallback is True
    assert talk.grounded is False
    assert _sentence(talk.output) == TALK["en"]
    promise = run(_question("en"), generate, _SHAPED["promise"])
    assert _sentence(promise.output) == PROMISE["en"]
    partner = run(_question("en"), generate, _SHAPED["partner"])
    assert _sentence(partner.output) == PARTNER["en"]
