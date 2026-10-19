"""One Genie turn: generate → ground → hydrate; retry once; then the template.

Grounding does not rewrite the model text (docs/specs/13-genie.md). A failed
check is a reason to ask the model again with the error list, then to fall
back to qualified cards plus one ask. A fatal failure (model 5xx/429/empty
stream, a missing or corrupt index, an encoder error, an ability 5xx or
timeout) is classified and the template says so with the reviewed degraded
sentence (#410). A page outage is not one of these.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from linker_genie import timing
from linker_genie.facts import TurnFacts, merge
from linker_genie.ground import check
from linker_genie.hydrate import complete_pairing_cards, hydrate
from linker_genie.language import (
    LANGUAGE_RETRY_PREFIX,
    language_failure,
    turn_language,
)
from linker_genie.prices import Lookup, fill
from linker_genie.route import SEARCH_LIMIT, Route
from linker_genie.schema import HandoffBlock, TextBlock, TurnOutput, TurnRequest
from linker_genie.template import (
    LOGIN_PLACEHOLDER,
    LOGIN_REQUIRED,
    FailureClass,
    fallback,
)
from linker_genie.tools import READ_PAGE

# pydantic-ai tool_manager._check_max_retries, on UnexpectedModelBehavior
# after AgentRetries.tools is spent. Output retries use a different sentence
# ("Exceeded maximum output retries"), so this phrase is the tool budget only.
_TOOL_RETRIES_EXHAUSTED = "exceeded max retries count of"
# ModelHTTPError.__str__ (`status_code: 500, model_name: deepseek-flash, body: …`).
# An ability 5xx is `returned 500`, so the model_name marker keeps the two apart.
_MODEL_HTTP = re.compile(r"status_code: (?:429|5\d\d)\b")
# AbilityError after the client's own retries (abilities.py).
_ABILITY_5XX = re.compile(r"returned 5\d\d\b")
# GeminiEmbedder._embed (embedding.py). knowledge.py re-raises EmbeddingError
# with these sentences; understand records `linker/search-knowledge: …`.
_ENCODER_HTTP = re.compile(r"HTTP \d+ on attempt \d+ of \d+")
_ENCODER_TRANSPORT = re.compile(
    r"(?:URLError|TimeoutError|ConnectionError) after \d+ attempts"
)

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


def fatal_class(failures: tuple[str, ...]) -> FailureClass | None:
    """The fatal class of this turn, or None for an ordinary grounding miss.

    `model`: a chat 5xx, a 429, or an empty stream (ChatCompletion `model`
    is None). `retrieval`: the document index is missing or not a database
    (`document index unavailable`), or the encoder failed (`EmbeddingError`:
    `HTTP 502 on attempt 2 of 2`, `URLError after 2 attempts`). `ability`:
    an ability 5xx, a timeout, or the retries giving up (`returned 5xx`,
    `could not be reached`, `did not answer after`). A page read's 500 is
    not an ability failure: the answer goes on without the page. A grounding
    sentence such as "a products turn is not a question for the team" is
    none of these (#410, #332 D1/D2).
    """
    found: FailureClass | None = None
    rank = {"ability": 1, "retrieval": 2, "model": 3}
    for failure in failures:
        kind = _one_failure(failure)
        if kind is not None and (found is None or rank[kind] > rank[found]):
            found = kind
            if found == "model":
                return found
    return found


def _one_failure(failure: str) -> FailureClass | None:
    if _is_model_failure(failure):
        return "model"
    if _is_retrieval_failure(failure):
        return "retrieval"
    if _is_ability_failure(failure):
        return "ability"
    return None


def _is_retrieval_failure(failure: str) -> bool:
    """The index could not be read, or the query could not be encoded."""
    if "document index unavailable" in failure:
        return True
    # understand._run_calls records `f"{ability}: {error}"`, so the class
    # name is not in the string. The encoder's own sentences are
    # (embedding.GeminiEmbedder._embed, knowledge.py re-raises them).
    if "EmbeddingError" in failure or "KnowledgeUnavailable" in failure:
        return True
    return (
        _ENCODER_HTTP.search(failure) is not None
        or _ENCODER_TRANSPORT.search(failure) is not None
    )


def _is_model_failure(failure: str) -> bool:
    if _MODEL_HTTP.search(failure) and "model_name:" in failure:
        return True
    lowered = failure.lower()
    if "chatcompletion" in lowered and "input_value=none" in lowered:
        return True
    return "invalid response from" in lowered and "chat completions" in lowered


def _is_page_failure(failure: str) -> bool:
    """A page read failed. The turn continues without it (page.py, #234)."""
    return f"{READ_PAGE}:" in failure


def _is_ability_failure(failure: str) -> bool:
    # `returned 500` is also how a page names its own outage. The page is
    # not an ability, and a recoverable turn must not become DEGRADED.
    if _is_page_failure(failure):
        return False
    return (
        _ABILITY_5XX.search(failure) is not None
        or "could not be reached" in failure
        or "did not answer after" in failure
    )


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


def _absorb(noted: list[str], call_failures: Sequence[str]) -> None:
    """Copy failures recorded while `generate` ran into `noted`.

    `call_failures` is the live log list. A model tool appends to it during
    `generate` (agent._note_call_failure), after `noted` was copied.
    """
    for failure in call_failures:
        if failure not in noted:
            noted.append(failure)


def _class_for_fallback(
    noted: list[str], last_failures: tuple[str, ...]
) -> FailureClass | None:
    """The class the template should say, or None for a normal fallback.

    A language miss is repaired in the required language (#374). That repair
    drops a model failure the retry already replaced. It does not drop an
    ability or retrieval failure still in `noted`: a route 500 must not
    ship the matching-products sentence because the last line is a language
    re-ask.
    """
    relevant = noted
    if any(failure.startswith(LANGUAGE_RETRY_PREFIX) for failure in last_failures):
        relevant = [failure for failure in noted if not _is_model_failure(failure)]
    return fatal_class(tuple(relevant))


def _tool_failures(noted: list[str]) -> tuple[str, ...]:
    """Ability and retrieval failures. A recovered chat 500 is not one."""
    return tuple(
        failure
        for failure in noted
        if _one_failure(failure) in ("ability", "retrieval")
    )


def _handoff_hides_tool_failure(output: TurnOutput, noted: list[str]) -> bool:
    """A grounded handoff after a tool failure is the sales deflection.

    The model route allows handoff, so a search-products 500 and a later
    handoff-team would otherwise ship the mailbox with an empty meta (#410).
    """
    if not _tool_failures(noted):
        return False
    return any(isinstance(block, HandoffBlock) for block in output.blocks)


def run(
    request: TurnRequest,
    generate: Generate,
    route: Route | None = None,
    seed: TurnFacts | None = None,
    commerce: Lookup | None = None,
    clock: timing.Timing | None = None,
    *,
    call_failures: Sequence[str] = (),
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

    `call_failures` are the understanding layer's route-call failures
    (`prepared.log["call_failures"]`), and the same list when a model tool
    appends during `generate`. A products search that returned 500 is
    recorded there. On a products route the model's later handoff fails
    grounding; on a model route it would ground. Either way the fallback
    has to see the ability failure (#410, AB-500).
    """
    expected = turn_language(request)
    retry_reason: str | None = None
    seeded = seed or TurnFacts()
    last_facts = seeded
    last_failures: tuple[str, ...] = ()
    # Every failed attempt, plus the route's own call failures. The shipped
    # `failures` stay the last attempt; this list only classifies the turn.
    noted: list[str] = list(call_failures)
    for attempt in (1, 2):
        try:
            with (
                timing.phase(clock, timing.MODEL),
                timing.phase(clock, timing.attempt_key(attempt)),
            ):
                output, facts = generate(request, retry_reason)
        except (ValueError, TypeError, RuntimeError) as error:
            last_failures = (str(error),)
            noted.extend(last_failures)
            _absorb(noted, call_failures)
            retry_reason = last_failures[0]
            last_facts = seeded
            continue
        _absorb(noted, call_failures)
        last_facts = merge([seeded, facts])
        with timing.phase(clock, timing.GROUND):
            result = check(output, last_facts, route)
        if not result.ok:
            last_failures = result.failures
            noted.extend(last_failures)
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
            noted.extend(last_failures)
            retry_reason = mismatch
            continue
        hidden = _tool_failures(noted)
        if hidden and _handoff_hides_tool_failure(priced, noted):
            # The handoff grounded, so nothing else would record the tool
            # failure. Meta's `failures` are this tuple (#410).
            last_failures = hidden
            retry_reason = hidden[0]
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
        _absorb(noted, call_failures)
        kind = _class_for_fallback(noted, last_failures)
        rendered = fallback(
            last_facts,
            expected,
            route,
            exhausted=_tool_retries_exhausted(last_failures),
            failure_class=kind,
        )
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
