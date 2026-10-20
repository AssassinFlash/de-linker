"""One Genie turn: generate → ground → hydrate; retry once; then the template.

Grounding does not rewrite the model text (docs/specs/13-genie.md). A failed
check is a reason to ask the model again with the error list. A miss that is
only bare numbers is stripped on that attempt and still shipped grounded: the
baseline floor treats `fallback: true` as no answer (#439). A second miss that
is only bare numbers is stripped the same way. Any other second miss falls
back to qualified cards plus one ask. A not_released pair is not rewritten:
a grounded answer ships as written, and a turn that fails twice for another
reason answers from the contract conditions the check returned (#396). A fatal
failure (model 5xx/429/empty stream, a missing or corrupt index, an encoder
error, an ability 5xx or timeout) is classified and the template says so with
the reviewed degraded sentence (#410). A page outage is not one of these.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from linker_genie import timing
from linker_genie.facts import TurnFacts, merge
from linker_genie.failure import FailureClass, RecordedFailure, from_log, note
from linker_genie.ground import Citation, check, cites_outside_turn, drop_bare_numbers
from linker_genie.hydrate import complete_pairing_cards, hydrate
from linker_genie.language import (
    LANGUAGE_RETRY_PREFIX,
    customer_message,
    language_failure,
    turn_language,
)
from linker_genie.prices import Lookup, fill
from linker_genie.route import SEARCH_LIMIT, Route
from linker_genie.schema import (
    HandoffBlock,
    Locale,
    TextBlock,
    TurnOutput,
    TurnRequest,
)
from linker_genie.template import (
    DEGRADED,
    LOGIN_PLACEHOLDER,
    LOGIN_REQUIRED,
    fallback,
    finish,
    seal,
)

# pydantic-ai tool_manager._check_max_retries, on UnexpectedModelBehavior
# after AgentRetries.tools is spent. Output retries use a different sentence
# ("Exceeded maximum output retries"), so this phrase is the tool budget only.
_TOOL_RETRIES_EXHAUSTED = "exceeded max retries count of"

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


def _tool_retries_exhausted(failures: tuple[str, ...]) -> bool:
    """True when a tool spent pydantic-ai's tool retries and the run stopped."""
    return any(_TOOL_RETRIES_EXHAUSTED in failure for failure in failures)


def fatal_class(failures: Sequence[RecordedFailure]) -> FailureClass | None:
    """The first fatal class of this turn, or None for an ordinary miss.

    The template uses one sentence for every fatal class (`model`,
    `retrieval`, `ability`), so nothing ranks them (#410). A page outage,
    a 4xx and a grounding miss have no class. The class is the one the
    catch site stored on the note (`failure.kind`); the sentence is not
    read again.
    """
    for failure in failures:
        if failure.kind is not None:
            return failure.kind
    return None


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


def _hydrate_priced(
    output: TurnOutput,
    facts: TurnFacts,
    route: Route | None,
    expected: str,
    commerce: Lookup | None,
    clock: timing.Timing | None,
) -> tuple[TurnOutput, TurnFacts, tuple[str, ...]]:
    """Login alignment, pairing cards, hydration and prices. One hydrate phase."""
    aligned = align_login(output, facts, expected)
    with timing.phase(clock, timing.HYDRATE):
        completed = complete_pairing_cards(aligned, facts, route)
        hydrated = hydrate(completed, facts, expected)
        priced, priced_facts, missed = fill(hydrated, facts, commerce)
    return priced, priced_facts, tuple(missed)


def _seal_and_finish(
    request: TurnRequest,
    priced: TurnOutput,
    priced_facts: TurnFacts,
    route: Route | None,
    expected: Locale,
) -> TurnOutput:
    """Required sentences after hydration, then the route's next step.

    `seal` adds no timing phase. If the sealed prose is the wrong language,
    the pre-seal text ships: the ask chips `finish` adds are not checked again.
    """
    sealed = seal(
        priced,
        priced_facts,
        route,
        customer_message(request),
        request.page_context.type,
    )
    cited = _cited_prose(priced_facts)
    if language_failure(sealed, expected, cited) is not None:
        sealed = priced
    return finish(sealed, priced_facts, route, customer_message(request))


def _cited_prose(facts: TurnFacts) -> str:
    """Search-knowledge chunk text, so a copied menu label does not vote (#443)."""
    return " ".join(
        fact.value
        for fact in facts.facts.values()
        if fact.source == "search-knowledge" and fact.id.endswith(".text")
    )


def _ship_number_correction(
    request: TurnRequest,
    output: TurnOutput,
    facts: TurnFacts,
    route: Route | None,
    expected: Locale,
    commerce: Lookup | None,
    clock: timing.Timing | None,
    attempt: int,
    retried: tuple[str, ...],
) -> TurnResult | str | None:
    """Strip a number-only miss and ship it when the re-check still holds.

    A model retry rewrites the answer and can drop the cards the row requires.
    The correction runs on this attempt. A citation or tool failure is not
    this path. A language miss after the strip is the retry reason, so the
    model is asked to rewrite in the required language rather than to drop
    a number it has already lost (#443).
    """
    corrected = drop_bare_numbers(output)
    with timing.phase(clock, timing.GROUND):
        result = check(corrected, facts, route)
    if not result.ok:
        return None
    priced, priced_facts, missed = _hydrate_priced(
        corrected, facts, route, expected, commerce, clock
    )
    mismatch = language_failure(priced, expected, _cited_prose(priced_facts))
    if mismatch is not None:
        return mismatch
    sealed = _seal_and_finish(request, priced, priced_facts, route, expected)
    return TurnResult(
        output=sealed,
        facts=priced_facts,
        grounded=True,
        failures=(),
        fallback=False,
        attempts=attempt,
        retried=retried,
        price_failures=missed,
    )


def _degraded_sentence(output: TurnOutput) -> bool:
    """True when the fallback is only the reviewed degraded sentence.

    #366 and #396 both use that sentence, and neither shows product cards
    (#410). `complete_pairing_cards` would append the released set.
    """
    if not output.blocks:
        return False
    for block in output.blocks:
        if not isinstance(block, HandoffBlock):
            return False
        if block.summary not in DEGRADED.values():
            return False
    return True


def _remember(recorded: list[RecordedFailure], failure: RecordedFailure) -> None:
    """Keep `failure`. A later note with a class replaces a sentence that had none."""
    for index, item in enumerate(recorded):
        if item.text != failure.text:
            continue
        if item.kind is None and failure.kind is not None:
            recorded[index] = failure
        return
    recorded.append(failure)


def _copy_call_failures(
    recorded: list[RecordedFailure], call_failures: Sequence[object]
) -> None:
    """Copy failures recorded while `generate` ran into `recorded`.

    `call_failures` is the live log list. A model tool appends a note during
    `generate` (agent._note_call_failure), after `recorded` was first copied.
    """
    for entry in call_failures:
        _remember(recorded, from_log(entry))


def _class_for_fallback(
    recorded: Sequence[RecordedFailure], last_failures: tuple[str, ...]
) -> FailureClass | None:
    """The class the template should say, or None for a normal fallback.

    A language miss is repaired in the required language (#374). That repair
    drops a model failure the retry already replaced. It does not drop an
    ability or retrieval failure still recorded: a route 500 must not ship
    the matching-products sentence because the last line is a language re-ask.
    """
    relevant = recorded
    if any(failure.startswith(LANGUAGE_RETRY_PREFIX) for failure in last_failures):
        relevant = [failure for failure in recorded if failure.kind != "model"]
    return fatal_class(relevant)


def _tool_failures(recorded: Sequence[RecordedFailure]) -> tuple[RecordedFailure, ...]:
    """Ability and retrieval failures. A recovered chat 500 is not one."""
    return tuple(
        failure for failure in recorded if failure.kind in ("ability", "retrieval")
    )


def run(
    request: TurnRequest,
    generate: Generate,
    route: Route | None = None,
    seed: TurnFacts | None = None,
    commerce: Lookup | None = None,
    clock: timing.Timing | None = None,
    *,
    call_failures: Sequence[object] = (),
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

    `call_failures` are the understanding layer's route-call notes
    (`prepared.log["call_failures"]`: `{text, kind}`), and the same list
    when a model tool appends during `generate`. The kind is the class the
    catch site already knew (#410). An ability or retrieval failure that
    is still recorded after a grounded answer is the degraded sentence.
    Hydration fills `{fact:handoff.sentence}` inside a text block, and a
    product sentence would otherwise ship with the failure only in the
    log. A model failure the retry replaced is not one of these. A
    request for a person is answered in `app._answer` before this runs.
    template.finish then adds the next step the route owes when the model
    left it out (#394); the fallback path does the same after its own fill,
    except a degraded handoff, which finish leaves unchanged. An unclassified
    exception is passed as `raised` so a shaped route does not ship the signed
    sentence in its place. Neither path adds a timing phase.
    """
    expected = turn_language(request)
    retry_reason: str | None = None
    seeded = seed or TurnFacts()
    last_facts = seeded
    last_failures: tuple[str, ...] = ()
    last_citations: tuple[Citation, ...] = ()
    # Every failed attempt, plus the route's own call failures. The shipped
    # `failures` stay the last attempt's sentences; this list only classifies.
    recorded: list[RecordedFailure] = []
    _copy_call_failures(recorded, call_failures)
    # The last attempt threw. A grounding miss clears this. An unclassified
    # exception is not a grounding miss, so the signed shape must not hide it.
    raised = False
    for attempt in (1, 2):
        try:
            with (
                timing.phase(clock, timing.MODEL),
                timing.phase(clock, timing.attempt_key(attempt)),
            ):
                output, facts = generate(request, retry_reason)
        except (ValueError, TypeError, RuntimeError) as error:
            raised = True
            # The live list first: a tool recorded its class, then a wrapper
            # may have raised a plain RuntimeError of the same sentence.
            _copy_call_failures(recorded, call_failures)
            failure = note(error)
            _remember(recorded, failure)
            last_failures = (failure.text,)
            retry_reason = failure.text
            last_facts = seeded
            last_citations = ()
            continue
        raised = False
        _copy_call_failures(recorded, call_failures)
        last_facts = merge([seeded, facts])
        with timing.phase(clock, timing.GROUND):
            result = check(output, last_facts, route)
        if not result.ok:
            last_failures = result.failures
            last_citations = result.citations
            for item in last_failures:
                _remember(recorded, RecordedFailure(item))
            if result.unbound_only and not _tool_failures(recorded):
                shipped = _ship_number_correction(
                    request,
                    output,
                    last_facts,
                    route,
                    expected,
                    commerce,
                    clock,
                    attempt,
                    last_failures,
                )
                if isinstance(shipped, TurnResult):
                    return shipped
                if shipped is not None:
                    last_failures = (shipped,)
                    last_citations = ()
                    _remember(recorded, RecordedFailure(shipped))
                    retry_reason = shipped
                    continue
            retry_reason = result.reason
            continue
        priced, priced_facts, missed = _hydrate_priced(
            output, last_facts, route, expected, commerce, clock
        )
        mismatch = language_failure(priced, expected, _cited_prose(priced_facts))
        if mismatch is not None:
            last_failures = (mismatch,)
            last_citations = ()
            _remember(recorded, RecordedFailure(mismatch))
            retry_reason = mismatch
            continue
        tool_failures = _tool_failures(recorded)
        # The recorded failure is the gate, not the block class (#410).
        # Hydration fills `{fact:handoff.sentence}` inside a TextBlock, and
        # the model can write that sentence literally, so a HandoffBlock
        # check still shipped the sales mailbox. A grounded product or
        # document sentence hides the same ability 5xx, timeout, or
        # retrieval failure. The template says the turn failed; qualified
        # cards and document links stay. A model failure this retry
        # replaced is not in `tool_failures`. Login still outranks this
        # inside the template, and a request for a person is answered
        # before `run`.
        if tool_failures:
            last_failures = tuple(item.text for item in tool_failures)
            retry_reason = last_failures[0]
            continue
        priced = _seal_and_finish(request, priced, priced_facts, route, expected)
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
        _copy_call_failures(recorded, call_failures)
        kind = _class_for_fallback(recorded, last_failures)
        rendered = fallback(
            last_facts,
            expected,
            route,
            exhausted=_tool_retries_exhausted(last_failures),
            failure_class=kind,
            raised=raised,
            invented_citation=cites_outside_turn(last_citations),
        )
    with timing.phase(clock, timing.HYDRATE):
        # Login stays the login sentence. A degraded sentence stays without
        # cards (#366, #396, #410). Any other pairing fallback keeps the
        # front of the released set, inside the template's six-card cap.
        if not _degraded_sentence(rendered):
            rendered = complete_pairing_cards(
                rendered, last_facts, route, card_limit=SEARCH_LIMIT
            )
        priced, priced_facts, price_missed = fill(rendered, last_facts, commerce)
        priced = finish(priced, priced_facts, route, customer_message(request))
    return TurnResult(
        output=priced,
        facts=priced_facts,
        grounded=False,
        failures=last_failures,
        fallback=True,
        attempts=2,
        retried=last_failures,
        price_failures=tuple(price_missed),
    )
