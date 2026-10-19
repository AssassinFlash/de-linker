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
rounded to three decimals — the resolution the Jev reading already logs (jev.py).

Phase keys are stable and additive; a phase that did not run is absent from the
record, never null, so a reader can tell "skipped" from "fast" (a phase that ran
under half a millisecond rounds to 0.0):

    total                      wall clock, handler entry → the record's moment
                               (the SSE meta shows it at the meta event; the turn
                               log's row is completed after the stream's `done`)
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
    model.tool.<ability>       a tool call the model itself made (agent.py)
    ground                     the grounding check
    hydrate                    placeholder hydration plus the cards' price
                               lookups (hydrate + prices.fill)
    template                   the fallback render; grounded turns skip it
    log                        the turn log write before the stream starts
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

# Seconds, three decimals — the resolution the Jev reading already logs (jev.py
# `Reading.as_log`); enough for phases of milliseconds, small next to a p95 gate
# of whole seconds (#329).
ROUNDING = 3


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
                self._phases.get(key, 0.0) + max(0.0, seconds), ROUNDING
            )

    def adopt(self, other: Timing) -> None:
        """Take another Timing's phases in (the understanding layer times itself
        and hands its clock over with the Prepared it returns)."""
        with self._lock, other._lock:
            for key, seconds in other._phases.items():
                self._phases[key] = round(
                    self._phases.get(key, 0.0) + seconds, ROUNDING
                )

    def first_event(self) -> None:
        """Mark the turn's first SSE event: the generator's first step, the
        earliest moment on the response path the mark exists (app._sse)."""
        with self._lock:
            if self._first_event is None:
                self._first_event = round(time.monotonic() - self._start, ROUNDING)

    def as_log(self) -> dict[str, float]:
        """The record for the turn log's `timing` column and the SSE meta
        `timing` object: every phase that ran, the first-event mark when it was
        set, and the wall clock to this moment (`total`)."""
        with self._lock:
            record = dict(self._phases)
            if self._first_event is not None:
                record["first_event"] = self._first_event
        record["total"] = round(time.monotonic() - self._start, ROUNDING)
        return record


@contextmanager
def phase(clock: Timing | None, key: str) -> Iterator[None]:
    """Time `key` on `clock`; without a clock, run untimed (every seam optional)."""
    if clock is None:
        yield
        return
    with clock.phase(key):
        yield
