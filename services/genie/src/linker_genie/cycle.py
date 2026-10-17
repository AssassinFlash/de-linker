"""One Genie turn: generate → ground → hydrate; retry once; then the template.

Grounding does not rewrite the model text (docs/specs/13-genie.md). A failed
check is a reason to ask the model again with the error list, then to fall
back to qualified cards plus one ask.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from linker_genie.facts import TurnFacts, merge
from linker_genie.ground import check
from linker_genie.hydrate import hydrate
from linker_genie.route import Route
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
    # The failures of an attempt the retry replaced, kept for the turn log.
    retried: tuple[str, ...] = ()


def run(
    request: TurnRequest,
    generate: Generate,
    route: Route | None = None,
    seed: TurnFacts | None = None,
) -> TurnResult:
    """Produce a grounded, hydrated turn. `generate` may call tools.

    `route` and `seed` are the understanding layer's (understand.py): the checks
    hold the answer to the route, and the facts of the route's own calls survive a
    model that fails twice, so the fallback still shows what code found.
    """
    retry_reason: str | None = None
    seeded = seed or TurnFacts()
    last_facts = seeded
    last_failures: tuple[str, ...] = ()
    for attempt in (1, 2):
        try:
            output, facts = generate(request, retry_reason)
        except (ValueError, TypeError, RuntimeError) as error:
            last_failures = (str(error),)
            retry_reason = last_failures[0]
            last_facts = seeded
            continue
        last_facts = merge([seeded, facts])
        result = check(output, last_facts, route)
        if result.ok:
            return TurnResult(
                output=hydrate(output, last_facts),
                facts=last_facts,
                grounded=True,
                failures=(),
                fallback=False,
                attempts=attempt,
                retried=last_failures,
            )
        last_failures = result.failures
        retry_reason = result.reason
    return TurnResult(
        output=fallback(last_facts, request.locale, route),
        facts=last_facts,
        grounded=False,
        failures=last_failures,
        fallback=True,
        attempts=2,
        retried=last_failures,
    )
