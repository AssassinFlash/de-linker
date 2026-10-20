"""A pairing answer keeps the one released set the tools returned (#376).

The behavioural tests call `cycle.run` only. On the code before the fill they
fail because the shipped cards are the draft's subset: the inverter is absent.
They do not depend on importing the fill.

#339 fixture `s4-repeat-h2-10k-t3` is the campaign shape: four rounds, DE and
EN, the thread carried forward (campaign 331 s4-repeat).
"""

import json
from pathlib import Path
from typing import Any

from linker_genie.cycle import run
from linker_genie.facts import TurnFacts, collect, merge
from linker_genie.route import SEARCH_LIMIT, Route
from linker_genie.schema import (
    AskBlock,
    CardsBlock,
    DocumentBlock,
    Locale,
    TextBlock,
    TurnMessage,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import LOGIN_REQUIRED

_MANIFEST = json.loads(
    (Path(__file__).parent / "fixtures" / "339" / "manifest.json").read_text(
        encoding="utf-8"
    )
)
CASE: dict[str, Any] = next(
    item for item in _MANIFEST["cases"] if item["id"] == "s4-repeat-h2-10k-t3"
)
CASE_ID = "s4-repeat-h2-10k-t3"
INVERTER = int(CASE["inverter"])
RELEASED = [int(product_id) for product_id in CASE["released"]]
BATTERIES = [product_id for product_id in RELEASED if product_id != INVERTER]
NOT_RELEASED = 9999


def _payload(
    inverter: int = INVERTER, batteries: list[int] | None = None
) -> dict[str, Any]:
    paired = BATTERIES if batteries is None else batteries
    pairings: list[dict[str, Any]] = [
        {"product_id": battery, "verdict": "released_with_accessory", "conditions": []}
        for battery in paired
    ]
    if inverter == INVERTER:
        pairings.append(
            {"product_id": NOT_RELEASED, "verdict": "not_released", "conditions": []}
        )
    return {
        "qualified": [
            {
                "product_id": inverter,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": pairings,
            }
        ]
    }


def _facts(
    locale: Locale = "de",
    inverter: int = INVERTER,
    batteries: list[int] | None = None,
    text: str = "H2-10K-T3",
) -> TurnFacts:
    payload = _payload(inverter, batteries)
    gathered = collect("linker/search-products", payload, locale)
    search = CASE["search"]
    gathered.tool_calls.append(
        {
            "name": search["ability"],
            "arguments": {
                "device_class": search["device_class"],
                "with_pairings": True,
                "text": text,
                "lang": locale,
                "limit": search["limit"],
            },
            "ok": True,
            "result": payload,
        }
    )
    return gathered


def _request(locale: Locale, messages: list[TurnMessage] | None = None) -> TurnRequest:
    question = str(CASE["questions"][locale])
    return TurnRequest(
        conversation_id=f"c376-{locale}",
        messages=messages or [TurnMessage(role="user", content=question)],
        locale=locale,
    )


def _answer(
    language: Locale, text: str, cards: list[int], refs: list[str] | None = None
) -> TurnOutput:
    return TurnOutput(
        language=language,
        blocks=[
            TextBlock(
                text=text,
                refs=refs
                if refs is not None
                else [str(product_id) for product_id in cards],
            ),
            CardsBlock(product_ids=cards),
        ],
    )


def _card_ids(output: TurnOutput) -> list[int]:
    blocks = [block for block in output.blocks if isinstance(block, CardsBlock)]
    assert len(blocks) == 1
    return list(blocks[0].product_ids)


def _text(output: TurnOutput) -> TextBlock:
    block = output.blocks[0]
    assert isinstance(block, TextBlock)
    return block


def test_a_german_retry_that_drops_the_inverter_ships_the_released_set() -> None:
    """Campaign turns 62–65: the first draft quoted "Artikel" and the retry
    kept only the batteries. The tool result still had the inverter.

    Before the fill, `run` ships the retry's cards and this assertion fails
    because 4107 is not among them.
    """
    facts = _facts()
    drafts: list[list[int]] = []

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        if retry is None:
            drafts.append(list(RELEASED))
            return (
                _answer(
                    "de",
                    "Das Steuermodul ist ein eigener Artikel.",
                    RELEASED,
                ),
                facts,
            )
        drafts.append(list(BATTERIES))
        return (
            _answer(
                "de",
                "Das Steuermodul ist ein eigenes Produkt.",
                BATTERIES,
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert result.grounded is True
    assert result.fallback is False
    assert result.attempts == 2
    assert drafts == [RELEASED, BATTERIES]
    assert INVERTER not in drafts[1]
    assert _card_ids(result.output) == RELEASED
    text = _text(result.output)
    assert text.text == "Das Steuermodul ist ein eigenes Produkt."
    assert str(INVERTER) in text.refs
    assert NOT_RELEASED not in _card_ids(result.output)


def test_a_first_attempt_that_omits_the_inverter_card_still_shows_it() -> None:
    """c376 replay, rounds 1 and 3, attempts=1: the draft's cards omitted 4107.

    The expected ids are the #339 fixture list, not a second walk of the
    payload. The draft is recorded so the assertion is that the shipped set
    differs from the draft. A no-op fill fails here with the battery list.
    """
    facts = _facts()
    drafts: list[list[int]] = []
    prose = "Diese Batterien haben ein dokumentiertes Pairing."

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        drafts.append(list(BATTERIES))
        return (
            _answer(
                "de",
                prose,
                BATTERIES,
                [str(INVERTER), *[str(product_id) for product_id in BATTERIES]],
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert result.attempts == 1
    assert drafts == [BATTERIES]
    assert INVERTER not in drafts[0]
    assert _card_ids(result.output) == RELEASED
    assert _text(result.output).text == prose


def test_a_pairing_fallback_stays_inside_six_cards_and_keeps_the_inverter() -> None:
    """Both drafts fail the number check. The template's six-card cap stays
    (trial question 11). The six are the front of the released set, so the
    inverter is not sorted out of the window.

    Before the fill the template's sorted sample does not start with 4107.
    A fill that ignores the cap ships all eight and fails the length check.
    """
    facts = _facts()

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            _answer(
                "de",
                "Die Spannung liegt bei 180 V.",
                BATTERIES,
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    cards = _card_ids(result.output)
    assert result.fallback is True
    assert result.attempts == 2
    assert len(cards) == SEARCH_LIMIT
    assert cards == RELEASED[:SEARCH_LIMIT]
    assert cards[0] == INVERTER
    assert NOT_RELEASED not in cards
    assert RELEASED[-1] not in cards


def test_s4_repeat_h2_10k_t3_four_rounds_de_and_en() -> None:
    """#339 fixture s4-repeat-h2-10k-t3: campaign 331 s4-repeat.

    Four rounds, the previous answer carried in the thread. DE round 1 is the
    campaign's Artikel retry. Rounds 2 and 3 omit the inverter on the first
    attempt, as c376 did. EN round 1 already has the set; later rounds omit
    it. Every shipped round is the fixture's released list.
    """
    assert CASE["id"] == CASE_ID
    assert CASE["rounds"] == 4
    assert CASE["locales"] == ["de", "en"]
    assert CASE["campaign"] == "campaign-331/s4-repeat"

    locales: tuple[Locale, Locale] = ("de", "en")
    for language in locales:
        facts = _facts(language)
        history: list[TurnMessage] = []
        question = str(CASE["questions"][language])
        drafts: list[list[int]] = []

        def generate(
            request: TurnRequest,
            retry: str | None,
            language: Locale = language,
            facts: TurnFacts = facts,
            question: str = question,
            drafts: list[list[int]] = drafts,
        ) -> tuple[TurnOutput, TurnFacts]:
            users = [message for message in request.messages if message.role == "user"]
            assert users[-1].content == question
            if len(users) > 1:
                assert any(message.role == "assistant" for message in request.messages)
            if language == "de" and len(users) == 1 and retry is None:
                drafts.append(list(RELEASED))
                return (
                    _answer("de", "Das Steuermodul ist ein eigener Artikel.", RELEASED),
                    facts,
                )
            if language == "de" and len(users) == 1:
                drafts.append(list(BATTERIES))
                return (
                    _answer(
                        "de",
                        "Das Steuermodul ist ein eigenes Produkt.",
                        BATTERIES,
                    ),
                    facts,
                )
            if len(users) in (2, 3):
                assert retry is None
                drafts.append(list(BATTERIES))
                text = (
                    "Diese Batterien haben ein dokumentiertes Pairing."
                    if language == "de"
                    else "These batteries have a documented pairing."
                )
                return (_answer(language, text, BATTERIES), facts)
            assert retry is None
            drafts.append(list(RELEASED))
            text = (
                "Diese Batterien haben ein dokumentiertes Pairing."
                if language == "de"
                else "These batteries have a documented pairing."
            )
            return (_answer(language, text, RELEASED), facts)

        for _round in range(4):
            result = run(
                _request(
                    language,
                    [*history, TurnMessage(role="user", content=question)],
                ),
                generate,
                Route("pairing", no_handoff=True),
            )
            assert result.fallback is False
            assert _card_ids(result.output) == RELEASED
            history.append(TurnMessage(role="user", content=question))
            history.append(
                TurnMessage(role="assistant", content=_text(result.output).text)
            )
        assert INVERTER not in drafts[1]
        assert INVERTER not in drafts[2]
        if language == "de":
            assert INVERTER not in drafts[3]


def test_an_english_answer_that_already_shows_the_set_keeps_its_order() -> None:
    facts = _facts("en")
    order = list(reversed(RELEASED))
    prose = "These batteries have a documented pairing."

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (_answer("en", prose, order), facts)

    result = run(_request("en"), generate, Route("pairing", no_handoff=True))
    assert result.attempts == 1
    assert _card_ids(result.output) == order
    assert _text(result.output).text == prose
    assert _text(result.output).refs == [str(product_id) for product_id in order]


def test_a_product_route_does_not_gain_the_inverter_card() -> None:
    facts = _facts()

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            _answer(
                "de",
                "Diese Batterien haben ein dokumentiertes Pairing.",
                BATTERIES,
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("products", no_handoff=True))
    assert _card_ids(result.output) == BATTERIES


def test_a_model_routed_pairing_that_omits_the_inverter_still_shows_it() -> None:
    """Jev read pairing and code did not prefetch: the route name is `model`
    and the model called the pairing search. The same fill applies.
    """
    facts = _facts()

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            _answer(
                "de",
                "Diese Batterien haben ein dokumentiertes Pairing.",
                BATTERIES,
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("model", no_handoff=True))
    assert result.attempts == 1
    assert _card_ids(result.output) == RELEASED


def test_a_model_route_without_a_pairing_set_keeps_the_draft() -> None:
    """A model route is not enough. Without one pairing set the draft stands."""
    payload = {
        "qualified": [
            {"product_id": INVERTER, "facts": {}, "commerce": {"price_visible": False}},
            {"product_id": 3556, "facts": {}, "commerce": {"price_visible": False}},
        ]
    }
    facts = collect("linker/search-products", payload, "de")
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"text": "hybrid", "lang": "de", "limit": SEARCH_LIMIT},
            "ok": True,
            "result": payload,
        }
    )

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (_answer("de", "Hier ist der Wechselrichter.", [INVERTER]), facts)

    result = run(_request("de"), generate, Route("model", no_handoff=True))
    assert _card_ids(result.output) == [INVERTER]


def test_two_independent_pairing_searches_are_not_merged() -> None:
    """Two search-products calls, each with its own released batteries.

    The draft names only the first search's batteries. Neither route may
    concatenate the two sets, and neither may fill from just one of them.
    """
    first = _facts()
    second = _facts("de", 3556, [6519], "GW10K-ET")
    facts = merge([first, second])

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            _answer(
                "de",
                "Diese Batterien haben ein dokumentiertes Pairing.",
                BATTERIES,
            ),
            facts,
        )

    for route in (Route("pairing", no_handoff=True), Route("model", no_handoff=True)):
        result = run(_request("de"), generate, route)
        assert _card_ids(result.output) == BATTERIES
        assert 3556 not in _card_ids(result.output)
        assert 6519 not in _card_ids(result.output)
        assert INVERTER not in _card_ids(result.output)


def test_two_pairing_rows_in_one_search_are_not_merged() -> None:
    payload = {
        "qualified": [
            {
                "product_id": INVERTER,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": [
                    {
                        "product_id": battery,
                        "verdict": "released_with_accessory",
                        "conditions": [],
                    }
                    for battery in BATTERIES
                ],
            },
            {
                "product_id": 3556,
                "facts": {},
                "commerce": {"price_visible": False},
                "pairings": [
                    {
                        "product_id": 6519,
                        "verdict": "released",
                        "conditions": [],
                    }
                ],
            },
        ]
    }
    facts = collect("linker/search-products", payload, "de")
    facts.tool_calls.append(
        {
            "name": "linker/search-products",
            "arguments": {"with_pairings": True, "text": "hybrid", "lang": "de"},
            "ok": True,
            "result": payload,
        }
    )

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (_answer("de", "Eine der Batterien.", [BATTERIES[0]]), facts)

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert _card_ids(result.output) == [BATTERIES[0]]


def test_a_document_block_stays_when_the_inverter_card_is_restored() -> None:
    """The fill replaces the cards block in place. A document the draft cited
    stays the next block, and the inverter ref is added after the battery refs.
    """
    payload = _payload()
    payload["qualified"][0]["pairings"][0]["documents"] = [
        {
            "url": "https://files.example/h2.pdf",
            "page": 3,
            "title": "H2 manual",
        }
    ]
    facts = collect("linker/search-products", payload, "de")
    search = CASE["search"]
    facts.tool_calls.append(
        {
            "name": search["ability"],
            "arguments": {
                "device_class": search["device_class"],
                "with_pairings": True,
                "text": search["text"],
                "lang": "de",
                "limit": search["limit"],
            },
            "ok": True,
            "result": payload,
        }
    )
    document = DocumentBlock(ref="compat.document.1832.0")

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            TurnOutput(
                language="de",
                blocks=[
                    TextBlock(
                        text="Diese Batterien haben ein dokumentiertes Pairing.",
                        refs=[str(product_id) for product_id in BATTERIES],
                    ),
                    CardsBlock(product_ids=BATTERIES),
                    document,
                ],
            ),
            facts,
        )

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert result.attempts == 1
    assert _card_ids(result.output) == RELEASED
    restored = result.output.blocks[2]
    assert isinstance(restored, DocumentBlock)
    assert restored.ref == document.ref
    assert restored.url == "https://files.example/h2.pdf#page=3"
    assert _text(result.output).refs == [
        *[str(product_id) for product_id in BATTERIES],
        str(INVERTER),
    ]


def test_a_pairing_route_with_login_required_ships_only_the_login_sentence() -> None:
    """Pairing route × inquiry.login_required. The login sentence is the only
    block, on a grounded draft and on the fallback the cycle post-processes.
    """
    facts = merge(
        [_facts(), collect("linker/inquiry-status", {"error": "login_required"})]
    )

    def grounded(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            TurnOutput(
                language="de",
                blocks=[TextBlock(text=LOGIN_REQUIRED["de"])],
            ),
            facts,
        )

    passed = run(_request("de"), grounded, Route("pairing", no_handoff=True))
    assert passed.grounded is True
    assert passed.fallback is False
    assert len(passed.output.blocks) == 1
    assert _text(passed.output).text == LOGIN_REQUIRED["de"]
    assert not any(isinstance(block, CardsBlock) for block in passed.output.blocks)

    def refused(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (_answer("de", "Die Spannung liegt bei 180 V.", BATTERIES), facts)

    failed = run(_request("de"), refused, Route("pairing", no_handoff=True))
    assert failed.fallback is True
    assert len(failed.output.blocks) == 1
    assert _text(failed.output).text == LOGIN_REQUIRED["de"]
    assert not any(isinstance(block, CardsBlock) for block in failed.output.blocks)


def test_a_released_pair_check_restores_the_omitted_product() -> None:
    """route.name stays `pairing` when the call is check-compatibility.

    A released verdict makes the two argument ids the set. The same holds
    when the model made that call itself (`model`).
    """
    for name in ("pairing", "model"):
        route = (
            Route("pairing", no_handoff=True)
            if name == "pairing"
            else Route("model", no_handoff=True)
        )
        facts = _pair_facts("released_with_accessory", [INVERTER, BATTERIES[0]])

        def generate(
            request: TurnRequest,
            retry: str | None,
            facts: TurnFacts = facts,
        ) -> tuple[TurnOutput, TurnFacts]:
            del request
            assert retry is None
            return (
                _answer("de", "Das Paar ist freigegeben.", [BATTERIES[0]]),
                facts,
            )

        result = run(_request("de"), generate, route)
        assert _card_ids(result.output) == [INVERTER, BATTERIES[0]]
        assert str(INVERTER) in _text(result.output).refs


_CONDITION_EN = (
    "The cited documents do not list this pair. This states "
    "no incompatibility and makes no claim about documents not checked."
)
_CONDITION_DE = (
    "Die zitierten Dokumente führen dieses Paar nicht auf. "
    "Das stellt keine Inkompatibilität fest."
)


def _not_released_facts(locale: Locale) -> TurnFacts:
    """One not_released check, conditions in `locale`, plus its document."""
    checked = collect(
        "linker/check-compatibility",
        {
            "verdict": "not_released",
            "conditions": [{"en": _CONDITION_EN, "de": _CONDITION_DE}],
            "documents": [
                {
                    "url": (
                        "https://de-linker.com/wp-content/uploads/2026/08/"
                        "ecoflow_ocean2-three-phase_datasheet_en_20260310.pdf"
                    )
                }
            ],
        },
        locale,
    )
    return merge([_pair_facts("not_released", [INVERTER, BATTERIES[0]]), checked])


def test_a_grounded_absence_answer_is_not_rewritten() -> None:
    """A not_released answer that passes grounding ships as written (#396).

    The service does not replace it with a verdict sentence. A condition the
    model cited stays, and so does the check's document. The pair is not
    filled in as cards the model did not ask for.
    """

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(
                        text=(
                            "Our documents do not state that this inverter "
                            "works with this battery. {fact:compat.condition.0}"
                        )
                    ),
                    DocumentBlock(ref="compat.document.0"),
                ],
            ),
            _not_released_facts("en"),
        )

    result = run(_request("en"), generate, Route("products", no_handoff=True))
    assert result.grounded and not result.fallback and result.attempts == 1
    text = _text(result.output).text
    assert text.startswith(
        "Our documents do not state that this inverter works with this battery."
    )
    assert _CONDITION_EN in text
    assert "This pairing is not released." not in text
    assert not any(isinstance(block, CardsBlock) for block in result.output.blocks)
    documents = [
        block for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert [block.ref for block in documents] == ["compat.document.0"]

    def generate_de(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (
            TurnOutput(
                language="de",
                blocks=[
                    TextBlock(
                        text=(
                            "Unsere Dokumente nennen nicht, dass dieser "
                            "Wechselrichter mit dieser Batterie funktioniert. "
                            "{fact:compat.condition.0}"
                        )
                    ),
                    DocumentBlock(ref="compat.document.0"),
                ],
            ),
            _not_released_facts("de"),
        )

    german = run(_request("de"), generate_de, Route("products", no_handoff=True))
    assert german.grounded and not german.fallback and german.attempts == 1
    german_text = _text(german.output).text
    assert german_text.startswith(
        "Unsere Dokumente nennen nicht, dass dieser Wechselrichter "
        "mit dieser Batterie funktioniert."
    )
    assert _CONDITION_DE in german_text
    assert "Die Kombination ist nicht freigegeben." not in german_text
    assert not any(isinstance(block, CardsBlock) for block in german.output.blocks)


def test_a_not_released_pair_that_fails_grounding_uses_the_contract_conditions() -> (
    None
):
    """A bare number is not replaced by a new verdict sentence (#396).

    Grounding fails twice. The fallback is the check's own condition and its
    document, not product cards and not an unreviewed sentence.
    """

    def generate_en(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            _answer(
                "en",
                "The EcoFlow OCEAN 2 has no released pairing.",
                [BATTERIES[0]],
            ),
            _not_released_facts("en"),
        )

    english = run(_request("en"), generate_en, Route("products", no_handoff=True))
    assert english.fallback and not english.grounded and english.attempts == 2
    assert _text(english.output).text == _CONDITION_EN
    assert "This pairing is not released." not in _text(english.output).text
    assert not any(isinstance(block, CardsBlock) for block in english.output.blocks)
    documents = [
        block for block in english.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert [block.ref for block in documents] == ["compat.document.0"]

    def generate_de(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            _answer("de", "Die Kombination trägt die Ziffer 2.", [BATTERIES[0]]),
            _not_released_facts("de"),
        )

    german = run(_request("de"), generate_de, Route("products", no_handoff=True))
    assert german.fallback and not german.grounded
    assert _text(german.output).text == _CONDITION_DE
    assert "Die Kombination ist nicht freigegeben." not in _text(german.output).text
    assert not any(isinstance(block, CardsBlock) for block in german.output.blocks)


def test_a_not_released_pair_that_cites_outside_the_turn_still_gets_the_conditions() -> (
    None
):
    """b09's model guessed compat.condition.1 and compat.document.1 twice.

    Those refs are outside this turn, so they cannot ship. The answer is the
    check's own condition and document, not the degraded sentence: it is
    assembled from the turn's tool facts, and the contract facts are there.
    """

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request, retry
        return (
            TurnOutput(
                language="en",
                blocks=[
                    TextBlock(text="{fact:compat.condition.1}"),
                    DocumentBlock(ref="compat.document.1"),
                ],
            ),
            _not_released_facts("en"),
        )

    result = run(_request("en"), generate, Route("products", no_handoff=True))
    assert result.fallback and not result.grounded and result.attempts == 2
    assert [block.type for block in result.output.blocks] == ["text", "document"]
    assert _text(result.output).text == _CONDITION_EN
    documents = [
        block for block in result.output.blocks if isinstance(block, DocumentBlock)
    ]
    assert [block.ref for block in documents] == ["compat.document.0"]


def test_a_not_released_answer_without_the_check_document_fails_grounding() -> None:
    """The prompt's next step is the document; a text-only answer is a retry."""
    from linker_genie.ground import check

    result = check(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="{fact:compat.condition.0}")],
        ),
        _not_released_facts("en"),
    )
    assert not result.ok
    assert "links the check's document" in result.reason


def test_a_missing_condition_index_names_the_refs_the_check_returned() -> None:
    """The retry reason names the condition refs, so the second attempt can copy.

    b09's model wrote compat.condition.2 where the check returned 0 and 1.
    """
    from linker_genie.ground import check

    result = check(
        TurnOutput(
            language="en",
            blocks=[TextBlock(text="{fact:compat.condition.2}")],
        ),
        _not_released_facts("en"),
    )
    assert not result.ok
    assert "compat.condition.0" in result.reason
    assert "first condition is index 0" in result.reason


def test_a_released_search_pairing_answer_asks_no_question() -> None:
    """The prompt says no ask once those cards stand (#396, b10)."""
    from linker_genie.ground import check

    output = _answer("en", "These are released.", list(RELEASED))
    output.blocks.append(
        AskBlock(field="phase", options=["single-phase", "three-phase"])
    )
    result = check(output, _facts(locale="en"))
    assert not result.ok
    assert "asks no question" in result.reason


def test_a_released_search_pairing_answer_links_a_pairing_document() -> None:
    """Every pairing document the search returned is linked (#396, b10)."""
    from linker_genie.ground import check

    payload = _payload()
    payload["qualified"][0]["pairings"][0]["documents"] = [
        {"url": "https://de-linker.com/manual.pdf"}
    ]
    facts = collect("linker/search-products", payload, "en")
    search = CASE["search"]
    facts.tool_calls.append(
        {
            "name": search["ability"],
            "arguments": {
                "device_class": search["device_class"],
                "with_pairings": True,
                "text": "H2-10K-T3",
                "lang": "en",
                "limit": search["limit"],
            },
            "ok": True,
            "result": payload,
        }
    )
    missing = check(_answer("en", "These are released.", list(RELEASED)), facts)
    assert not missing.ok
    assert "links no document" in missing.reason

    linked = _answer("en", "These are released.", list(RELEASED))
    linked.blocks.append(DocumentBlock(ref=f"compat.document.{BATTERIES[0]}.0"))
    assert check(linked, facts).ok


def test_two_pair_checks_are_not_merged() -> None:
    first = _pair_facts("released", [INVERTER, BATTERIES[0]])
    second = _pair_facts("released", [3556, 6519])
    facts = merge([first, second])

    def generate(
        request: TurnRequest, retry: str | None
    ) -> tuple[TurnOutput, TurnFacts]:
        del request
        assert retry is None
        return (_answer("de", "Ein Paar.", [BATTERIES[0]]), facts)

    result = run(_request("de"), generate, Route("pairing", no_handoff=True))
    assert _card_ids(result.output) == [BATTERIES[0]]


def test_the_released_set_uses_the_same_verdicts_as_qualification() -> None:
    """`pairing_card_sets` and `_from_search` share RELEASED_VERDICTS."""
    from linker_genie.facts import RELEASED_VERDICTS, pairing_card_sets

    facts = _facts()
    (ids,) = pairing_card_sets(facts)
    assert "released" in RELEASED_VERDICTS
    assert "released_with_accessory" in RELEASED_VERDICTS
    assert ids == RELEASED
    assert set(ids) == facts.qualified_ids
    assert NOT_RELEASED in facts.product_ids
    assert NOT_RELEASED not in facts.qualified_ids


def _pair_facts(verdict: str, product_ids: list[int]) -> TurnFacts:
    payload: dict[str, Any] = {"verdict": verdict, "conditions": [], "documents": []}
    gathered = collect("linker/check-compatibility", payload, "de")
    gathered.tool_calls.append(
        {
            "name": "linker/check-compatibility",
            "arguments": {"product_ids": product_ids},
            "ok": True,
            "result": payload,
        }
    )
    gathered.product_ids.update(product_ids)
    if verdict in ("released", "released_with_accessory"):
        gathered.qualified_ids.update(product_ids)
    return gathered
