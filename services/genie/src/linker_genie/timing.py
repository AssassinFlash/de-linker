"""Passive per-turn timing: how long each phase of a Genie turn took.

The owner ruled out backend streaming (docs/research/2026-10-18-genie-reply-design/
REFERENCES.md "业主最后确认的实施边界"), so a turn has no first token to measure; what
latency work needs — dossier docs/research/2026-10-19-genie-campaign-gaps/DOSSIER.md
§1.14: no public competitor SLO exists, the numbers are ours to design — is the
turn's wall clock, the time until the first SSE event, and a phase breakdown of the
pipeline, because the campaign's gate reads a p95 over turns (#329: p95 ≤ 30 s,
target ≤ 15 s) and §1.14 names the serial stack (Jev + read-page + tool calls +
deepseek-flash) as the first place to look.

Measurement is passive: nothing here changes a decision, a retry, a prompt or an
order, adds a model call (AGENTS.md §5, the four channels are untouched) or waits
on anything outside the process. Every duration is `time.monotonic()` seconds,
rounded to three decimal places — the resolution the Jev reading already logs
(jev.py).

A record comes in two shapes. `as_log()` is the complete record: the phases, the
first-event mark when it was set, and `total` (the wall clock to that moment).
`as_log(complete=False)` is the partial record the turn log's row is inserted
with, before the stream runs: the phases only, no `total`. Only the stream's end
writes the complete record (app._sse; ops/turn_latency.py counts a record without
`total` as incomplete). The partial record is also a deliberate additive surface
in the SSE meta: the #336B baseline harness reads each question's per-turn timing
from the meta, without VPS log access; the shell ignores fields it does not know.

The phase keys are constants (and prefix builders) below, spelled once, so a typo
cannot invent a phase. A phase that did not run is absent from the record, never
null, so a reader can tell "skipped" from "fast" (a phase that ran under half a
millisecond rounds to 0.0):

    total                      wall clock, handler entry → the record's moment
                               (only in the complete record; the SSE meta shows
                               it at the meta event, after the turn is computed)
    first_event                handler entry → the first SSE event (app._sse)
    understand                 the whole understanding layer (understand.prepare)
    understand.vocabulary      the Store API vocabulary
    understand.attachments     this turn's files read (vision.py)
    understand.jev             the Jev read, retries and backoff included; the
                               successful call's own seconds stay where they
                               already were (understanding.jev.seconds)
    understand.parts           a parts list matched into products
    understand.calls           the route's calls side by side (the block's wall)
    understand.call.<ability>  one route call: the page read, the document
                               search, an ability
    model                      the chat model, every attempt together
    model.attempt_1/2          one model attempt (2 only after a retry)
    model.tool.<ability>       a tool call the model itself made (agent.py); a
                               refused call (budget, no page reader) never enters
                               its phase, so it is absent, not timed as instant
    ground                     the grounding check
    hydrate                    placeholder hydration plus the cards' price
                               lookups (hydrate + prices.fill)
    template                   the fallback render; grounded turns skip it
    log                        the turn log write and the start row's removal
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

# Three decimals — the resolution the Jev reading already logs (jev.py
# `Reading.as_log`); enough for phases of milliseconds, small next to a p95 gate
# of whole seconds (#329).
ROUNDING_PLACES = 3

# The stable phase keys, in the shape the record carries them.
TOTAL = "total"
FIRST_EVENT = "first_event"
UNDERSTAND = "understand"
VOCABULARY = f"{UNDERSTAND}.vocabulary"
ATTACHMENTS = f"{UNDERSTAND}.attachments"
JEV = f"{UNDERSTAND}.jev"
PARTS = f"{UNDERSTAND}.parts"
CALLS = f"{UNDERSTAND}.calls"
CALL = f"{UNDERSTAND}.call"
MODEL = "model"
GROUND = "ground"
HYDRATE = "hydrate"
TEMPLATE = "template"
LOG = "log"


def attempt_key(number: int) -> str:
    """A model attempt's key (`model.attempt_1`, `model.attempt_2`)."""
    return f"{MODEL}.attempt_{number}"


def call_key(ability: str) -> str:
    """A route call's key (`understand.call.<ability>`), ability as tools name it."""
    return f"{CALL}.{ability}"


def tool_key(ability: str) -> str:
    """A model tool call's key (`model.tool.<ability>`), ability as tools name it."""
    return f"{MODEL}.tool.{ability}"


class Timing:
    """One turn's phase durations, accumulated from any thread.

    The route's calls run side by side (understand._run_calls) and each observes
    its own duration, so sums share a lock; a phase entered twice (a retried
    model attempt, grounding after each) accumulates instead of overwriting.
    """

    def __init__(self) -> None:
        self._start = time.monotonic()
        self._lock = threading.Lock()
        self._phases: dict[str, float] = {}
        self._first_event: float | None = None

    @contextmanager
    def phase(self, key: str) -> Iterator[None]:
        started = time.monotonic()
        try:
            yield
        finally:
            # The finally keeps a failed phase timed: a model attempt that
            # raised, or Jev's retries, are exactly the durations latency work
            # is after.
            self.observe(key, time.monotonic() - started)

    def observe(self, key: str, seconds: float) -> None:
        """Add a duration measured elsewhere (a worker thread's route call)."""
        with self._lock:
            self._phases[key] = round(
                self._phases.get(key, 0.0) + max(0.0, seconds), ROUNDING_PLACES
            )

    def adopt(self, other: Timing) -> None:
        """Take another Timing's phases in (the understanding layer times itself
        and hands its clock over with the Prepared it returns)."""
        if other is self:
            return
        with self._lock, other._lock:
            for key, seconds in other._phases.items():
                self._phases[key] = round(
                    self._phases.get(key, 0.0) + seconds, ROUNDING_PLACES
                )

    def mark_first_event(self) -> None:
        """Mark the turn's first SSE event: the generator's first step, the
        earliest moment on the response path the mark exists (app._sse)."""
        with self._lock:
            if self._first_event is None:
                self._first_event = round(
                    time.monotonic() - self._start, ROUNDING_PLACES
                )

    def as_log(self, *, complete: bool = True) -> dict[str, float]:
        """The record for the SSE meta `timing` object and the turn log's
        `timing` column.

        With `complete` (the default), the record ends with `total` — the wall
        clock to this moment. Without it, the phases (plus the first-event mark
        when set) alone: the shape the turn log's row is inserted with, before
        the stream runs. Only the complete record of a served stream counts as a
        measured turn (ops/turn_latency.py); the partial shape of a turn that
        never streamed is reported as incomplete, never fed into a percentile.
        """
        with self._lock:
            record = dict(self._phases)
            if self._first_event is not None:
                record[FIRST_EVENT] = self._first_event
        if complete:
            record[TOTAL] = round(time.monotonic() - self._start, ROUNDING_PLACES)
        return record


@contextmanager
def phase(clock: Timing | None, key: str) -> Iterator[None]:
    """Time `key` on `clock`; without a clock, run untimed (every seam optional)."""
    if clock is None:
        yield
        return
    with clock.phase(key):
        yield
