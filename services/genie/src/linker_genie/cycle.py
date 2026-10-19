"""One Genie turn: generate → ground → hydrate; retry once; then the template.

Grounding does not rewrite the model text (docs/specs/13-genie.md). A failed
check is a reason to ask the model again with the error list, then to fall
back to qualified cards plus one ask.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from linker_genie import timing
from linker_genie.facts import TurnFacts, merge
from linker_genie.ground import check
from linker_genie.hydrate import complete_pairing_cards, hydrate
from linker_genie.language import language_failure, turn_language
from linker_genie.prices import Lookup, fill
from linker_genie.route import SEARCH_LIMIT, Route
from linker_genie.schema import TextBlock, TurnOutput, TurnRequest
from linker_genie.template import LOGIN_PLACEHOLDER, LOGIN_REQUIRED, fallback

Generate = Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]


@dataclass
class TurnResult:
    output: TurnOutput
    facts: TurnFacts
    grounded: bool
    failures: tuple[str, ...]
    fallback: bool
    attempts: int
    # The failures of an attempt the retry replaced, kept for the turn log.
    retried: tuple[str, ...] = ()
    # Card price lookups that failed (prices.fill); their cards show no price line.
    price_failures: tuple[str, ...] = ()


def align_login(output: TurnOutput, facts: TurnFacts, expected: str) -> TurnOutput:
    """Ship the login sentence in the answer language.

    The sentence is the service's. A guest turn whose only block is either
    exact sentence, or the `{fact:inquiry.login}` placeholder, is rewritten
    to `LOGIN_REQUIRED` of `expected` before hydration and the language check.
    Any other shape is left for grounding, which already refused it.
    """
    if "inquiry.login_required" not in facts.facts:
        return output
    if len(output.blocks) != 1 or not isinstance(output.blocks[0], TextBlock):
        return output
    block = output.blocks[0]
    if block.refs or block.text not in {
        LOGIN_REQUIRED["en"],
        LOGIN_REQUIRED["de"],
        LOGIN_PLACEHOLDER,
    }:
        return output
    if block.text == LOGIN_REQUIRED[expected] and output.language == expected:
        return output
    return output.model_copy(
        update={
            "language": expected,
            "blocks": [TextBlock(text=LOGIN_REQUIRED[expected])],
        }
    )


def run(
    request: TurnRequest,
    generate: Generate,
    route: Route | None = None,
    seed: TurnFacts | None = None,
    commerce: Lookup | None = None,
    clock: timing.Timing | None = None,
) -> TurnResult:
    """Produce a grounded, hydrated turn. `generate` may call tools.

    `route` and `seed` are the understanding layer's (understand.py): the checks
    hold the answer to the route, and the facts of the route's own calls survive a
    model that fails twice, so the fallback still shows what code found.
    Every card of the shipped turn, the fallback's too, gets its price line from
    the turn's tools (prices.fill, #242); `commerce` reads the products no tool
    priced, as the customer. `clock` only times the phases (timing.py, #336).

    The answer language is the last customer message when that message is
    clearly one language, otherwise the page locale (language.py, #374). The
    check reads the hydrated answer, price lines included. A mismatch is a
    failed attempt: the model is asked once with that reason, and the template
    then answers in the required language. The violating text is not shipped.
    A grounding failure is retried on its own; the language check runs only
    after grounding has passed.
    """
    expected = turn_language(request)
    retry_reason: str | None = None
    seeded = seed or TurnFacts()
    last_facts = seeded
    last_failures: tuple[str, ...] = ()
    for attempt in (1, 2):
        try:
            with (
                timing.phase(clock, timing.MODEL),
                timing.phase(clock, timing.attempt_key(attempt)),
            ):
                output, facts = generate(request, retry_reason)
        except (ValueError, TypeError, RuntimeError) as error:
            last_failures = (str(error),)
            retry_reason = last_failures[0]
            last_facts = seeded
            continue
        last_facts = merge([seeded, facts])
        with timing.phase(clock, timing.GROUND):
            result = check(output, last_facts, route)
        if not result.ok:
            last_failures = result.failures
            retry_reason = result.reason
            continue
        aligned = align_login(output, last_facts, expected)
        with timing.phase(clock, timing.HYDRATE):
            # One pairing set fills cards the attempt omitted, including the
            # first attempt; the hydrated sentences follow the answer language
            # (#382). Prose is not rewritten.
            completed = complete_pairing_cards(aligned, last_facts, route)
            hydrated = hydrate(completed, last_facts, expected)
            priced, priced_facts, missed = fill(hydrated, last_facts, commerce)
        mismatch = language_failure(priced, expected)
        if mismatch is not None:
            last_failures = (mismatch,)
            retry_reason = mismatch
            continue
        return TurnResult(
            output=priced,
            facts=priced_facts,
            grounded=True,
            failures=(),
            fallback=False,
            attempts=attempt,
            retried=last_failures,
            price_failures=tuple(missed),
        )
    with timing.phase(clock, timing.TEMPLATE):
        rendered = fallback(last_facts, expected, route)
    with timing.phase(clock, timing.HYDRATE):
        # Login stays the login sentence. Any other pairing fallback keeps the
        # front of the released set, inside the template's six-card cap.
        rendered = complete_pairing_cards(
            rendered, last_facts, route, card_limit=SEARCH_LIMIT
        )
        priced, priced_facts, missed = fill(rendered, last_facts, commerce)
    return TurnResult(
        output=priced,
        facts=priced_facts,
        grounded=False,
        failures=last_failures,
        fallback=True,
        attempts=2,
        retried=last_failures,
        price_failures=tuple(missed),
    )
