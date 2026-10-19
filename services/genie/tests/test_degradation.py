"""A failed turn says it failed (#410, #332 D1/D2).

The seven injected scenarios are M500-EN, M500-DE, M-EMPTY, M-429, M500-DOC,
IDX-MISS and IDX-BAD. AB-500 is the products-search 500 that was printed as
the sales mailbox. EN and DE both use the reviewed degraded sentence.
"""

from collections.abc import Callable

from linker_genie.cycle import fatal_class, run
from linker_genie.facts import Document, Fact, TurnFacts, collect
from linker_genie.knowledge import KnowledgeUnavailable
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
    FailureClass,
    fallback,
    german_is_clean,
)

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
_M500 = (
    "status_code: 500, model_name: deepseek-flash, body: "
    "{'message': 'injected chat 500', 'type': 'server_error'}"
)
_M429 = (
    "status_code: 429, model_name: deepseek-flash, body: "
    "{'message': 'injected chat 429', 'type': 'rate_limit_error'}"
)
_EMPTY = (
    "Invalid response from deepseek chat completions endpoint: "
    "1 validation error for ChatCompletion\nmodel\n  Input should be a "
    "valid string [type=string_type, input_value=None, input_type=NoneType]"
)
_IDX_MISS = (
    "linker/search-knowledge: document index unavailable: unable to open database file"
)
_IDX_BAD = "linker/search-knowledge: document index unavailable: file is not a database"
_AB500 = (
    "linker/search-products: linker/search-products returned 500 "
    "for {'input[series]': 'saj-h2'}"
)
_AB_TIMEOUT = "linker/search-products could not be reached: timed out"
# knowledge.py re-raises EmbeddingError; understand records it under the tool.
# These are the sentences embedding.GeminiEmbedder._embed raises (QUERY_ATTEMPTS
# is 2): "HTTP 502 on attempt 2 of 2", "URLError after 2 attempts".
_ENCODER_HTTP = (
    "linker/search-knowledge: gemini-embedding-2: HTTP 502 on attempt 2 of 2"
)
_ENCODER_URL = (
    "linker/search-knowledge: gemini-embedding-2: "
    "URLError after 2 attempts: <urlopen error [Errno 111] Connection refused>"
)
_ENCODER_HTTP_BARE = "gemini-embedding-2: HTTP 502 on attempt 2 of 2"
_ENCODER_URL_BARE = "gemini-embedding-2: URLError after 2 attempts"
_PAGE_500 = "linker/read-page: page /blog/x/ returned 500"
_PDF = "https://de-linker.com/wp-content/uploads/2026/03/SAJ-H2-user-manual.pdf"
_LANGUAGES: tuple[Locale, ...] = ("en", "de")

Generate = Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]


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


def test_fatal_classes_match_the_injected_failures() -> None:
    """The class passed into fallback. A grounding miss is not a class."""
    cases: tuple[tuple[str, FailureClass | None], ...] = (
        (_M500, "model"),
        (_M429, "model"),
        (_EMPTY, "model"),
        (_IDX_MISS, "retrieval"),
        (_IDX_BAD, "retrieval"),
        (_ENCODER_HTTP, "retrieval"),
        (_ENCODER_URL, "retrieval"),
        (_ENCODER_HTTP_BARE, "retrieval"),
        (_ENCODER_URL_BARE, "retrieval"),
        ("gemini: HTTP 401 on attempt 1 of 2", "retrieval"),
        ("gemini: URLError after 2 attempts", "retrieval"),
        ("EmbeddingError: gemini-embedding-2: HTTP 502 on attempt 2 of 2", "retrieval"),
        ("KnowledgeUnavailable: document index unavailable: locked", "retrieval"),
        (_AB500, "ability"),
        (_AB_TIMEOUT, "ability"),
        ("linker/search-products did not answer after 3 attempts", "ability"),
        (_PAGE_500, None),
        ("linker/read-page: draft products returned 500", None),
        ("a products turn is not a question for the team", None),
        ("status_code: 400, model_name: deepseek-flash, body: bad request", None),
        ("linker/search-products returned 404 for {}", None),
    )
    for failure, kind in cases:
        assert fatal_class((failure,)) == kind, failure
    # AB-500's meta.failures is the grounding sentence. The 500 is the
    # route call. Together they are an ability failure, not a model failure.
    assert (
        fatal_class((_AB500, "a products turn is not a question for the team"))
        == "ability"
    )


def test_a_model_or_index_failure_with_cards_says_it_failed() -> None:
    """M500, M-EMPTY, M-429, IDX-MISS, IDX-BAD. Cards may stay."""
    cases: tuple[tuple[str, FailureClass, BaseException], ...] = (
        ("M500", "model", RuntimeError(_M500)),
        ("M-EMPTY", "model", RuntimeError(_EMPTY)),
        ("M-429", "model", RuntimeError(_M429)),
        ("IDX-MISS", "retrieval", KnowledgeUnavailable(_IDX_MISS)),
        ("IDX-BAD", "retrieval", KnowledgeUnavailable(_IDX_BAD)),
    )
    for name, kind, error in cases:
        assert fatal_class((str(error),)) == kind, name
        route = _PRODUCTS if kind == "model" else _DOCUMENTS
        for language in _LANGUAGES:
            result = run(
                _question(language),
                _raise(error),
                route=route,
                seed=_stock(),
            )
            assert result.fallback is True
            assert result.grounded is False
            _assert_degraded(result.output, language)
            cards = [
                block for block in result.output.blocks if isinstance(block, CardsBlock)
            ]
            assert cards and set(cards[0].product_ids) == set(_STOCK), name
            assert not any(block.type == "ask" for block in result.output.blocks)


def test_a_model_500_on_a_document_turn_does_not_claim_it_answered() -> None:
    """M500-DOC. The manuals may stay. The success sentence does not."""
    for language in _LANGUAGES:
        result = run(
            _question(language, documents=True),
            _raise(RuntimeError(_M500)),
            route=_DOCUMENTS,
            seed=_manual(),
        )
        assert result.fallback is True
        _assert_degraded(result.output, language)
        links = [
            block for block in result.output.blocks if isinstance(block, DocumentBlock)
        ]
        assert links and links[0].url
        assert not any(isinstance(block, CardsBlock) for block in result.output.blocks)


def test_a_products_search_failure_is_not_the_sales_mailbox() -> None:
    """AB-500, and an ability timeout of the same shape. EN and DE."""
    cases = (("AB-500", _AB500), ("AB-TIMEOUT", _AB_TIMEOUT))
    for name, failure in cases:
        assert fatal_class((failure,)) == "ability", name
        for language in _LANGUAGES:
            result = run(
                _question(language),
                _handoff(language),
                route=_PRODUCTS,
                call_failures=(failure,),
            )
            assert result.fallback is True
            assert result.grounded is False
            assert any(
                "not a question for the team" in item for item in result.failures
            )
            _assert_degraded(result.output, language)
            assert not any(
                isinstance(block, CardsBlock) for block in result.output.blocks
            ), name


def test_an_encoder_failure_with_cards_says_it_failed() -> None:
    """The encoder's own sentences are a retrieval failure, not a match."""
    for failure in (_ENCODER_HTTP, _ENCODER_URL, _ENCODER_HTTP_BARE, _ENCODER_URL_BARE):
        assert fatal_class((failure,)) == "retrieval"
        for language in _LANGUAGES:
            result = run(
                _question(language),
                _raise(RuntimeError(failure)),
                route=_PRODUCTS,
                seed=_stock(),
            )
            assert result.fallback is True
            _assert_degraded(result.output, language)
            cards = [
                block for block in result.output.blocks if isinstance(block, CardsBlock)
            ]
            assert cards and set(cards[0].product_ids) == set(_STOCK)


def test_a_page_outage_stays_a_normal_fallback() -> None:
    """read-page 500 is not an ability failure. A grounding miss still matches."""
    assert fatal_class((_PAGE_500,)) is None
    assert fatal_class((_PAGE_500, _AB500)) == "ability"
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

    for language in _LANGUAGES:
        result = run(
            _question(language),
            generate,
            route=_PRODUCTS,
            seed=facts,
            call_failures=(_PAGE_500,),
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
        call_failures=(_AB500,),
    )
    assert result.fallback is True
    assert result.failures[0].startswith("answer in ")
    _assert_degraded(result.output, "de")


def test_a_model_tool_failure_cannot_become_the_sales_sentence() -> None:
    """search-products 500, then handoff-team, on a model route.

    The 500 is appended during generate, the way the runner writes
    `prepared.log["call_failures"]`. The handoff would otherwise ground.
    """
    recorded: list[str] = []

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        # Appended during the attempt, after `run` has copied the list.
        if not recorded:
            recorded.append(_AB500)
        return _handoff("en")(request, retry)

    result = run(
        _question("en"), generate, route=Route("model"), call_failures=recorded
    )
    assert result.fallback is True
    assert result.grounded is False
    _assert_degraded(result.output, "en")
    assert any("returned 500" in item for item in result.failures)


def test_a_raised_search_failure_then_handoff_is_not_the_sales_sentence() -> None:
    """pydantic-ai raises the tool error out of the first attempt."""
    calls = {"n": 0}

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError(
                "linker/search-products returned 500 for {'input[series]': 'saj-h2'}"
            )
        return _handoff("en")(request, retry)

    result = run(_question("en"), generate, route=Route("model"))
    assert calls["n"] == 2
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    assert any("returned 500" in item for item in result.failures)


def test_a_recovered_model_error_may_still_hand_off() -> None:
    """A chat 500 the retry replaced is not a tool failure."""
    calls = {"n": 0}

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError(_M500)
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

    prepared = Prepared(route=_PRODUCTS, log={"call_failures": [_AB500]})
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
        )
    finally:
        del app.state.generate
    assert block is None
    assert result.fallback is True
    _assert_degraded(result.output, "en")
    assert any("not a question for the team" in item for item in result.failures)
    assert prepared.log["call_failures"] == [_AB500]


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
            raise RuntimeError(_M500)
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

    for language in _LANGUAGES:
        result = run(_question(language), generate, route=_PRODUCTS, seed=facts)
        assert result.fallback is True
        assert _sentence(result.output) == _MATCHING[language]
        cards = [
            block for block in result.output.blocks if isinstance(block, CardsBlock)
        ]
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
    assert not any(isinstance(block, CardsBlock) for block in output.blocks)


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
