"""One Genie turn: generate → ground → hydrate; retry once; then the template.

Grounding does not rewrite the model text (docs/specs/13-genie.md). A failed
check is a reason to ask the model again with the error list, then to fall
back to qualified cards plus one ask.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from linker_genie.facts import TurnFacts
from linker_genie.ground import check
from linker_genie.hydrate import hydrate
from linker_genie.schema import TurnOutput, TurnRequest
from linker_genie.template import fallback

Generate = Callable[[TurnRequest, str | None], tuple[TurnOutput, TurnFacts]]


@dataclass
class TurnResult:
    output: TurnOutput
    facts: TurnFacts
    grounded: bool
    failures: tuple[str, ...]
    fallback: bool
    attempts: int


def run(
    request: TurnRequest,
    generate: Generate,
) -> TurnResult:
    """Produce a grounded, hydrated turn. `generate` may call tools."""
    retry_reason: str | None = None
    last_facts = TurnFacts()
    last_failures: tuple[str, ...] = ()
    for attempt in (1, 2):
        try:
            output, facts = generate(request, retry_reason)
        except (ValueError, TypeError, RuntimeError) as error:
            last_failures = (str(error),)
            retry_reason = last_failures[0]
            last_facts = TurnFacts()
            continue
        last_facts = facts
        result = check(output, facts)
        if result.ok:
            return TurnResult(
                output=hydrate(output, facts),
                facts=facts,
                grounded=True,
                failures=(),
                fallback=False,
                attempts=attempt,
            )
        last_failures = result.failures
        retry_reason = result.reason
    return TurnResult(
        output=fallback(last_facts, request.locale),
        facts=last_facts,
        grounded=False,
        failures=last_failures,
        fallback=True,
        attempts=2,
    )
