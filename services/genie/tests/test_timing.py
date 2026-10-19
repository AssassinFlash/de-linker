"""The passive turn clock: phases accumulate, records stay non-negative.

Durations come from `time.monotonic()`, so these tests drive that clock through
a fixed tick sequence instead of sleeping: every assertion is exact, never a
race with the machine's timer. `_ticks(monkeypatch, *reads)` fixes the reads a
`Timing()` makes after its constructor's own (which reads 0.0); monkeypatch
restores the real clock after each test.
"""

import time

import pytest

from linker_genie import timing
from linker_genie.timing import Timing, phase


def _ticks(monkeypatch: pytest.MonkeyPatch, *reads: float) -> None:
    values = iter((0.0, *reads))
    monkeypatch.setattr(time, "monotonic", lambda: next(values))


def test_the_phase_keys_are_built_in_one_place() -> None:
    """#336 review: a key is spelled once (timing.py), so a typo cannot invent a
    phase no reader knows."""
    assert timing.TOTAL == "total"
    assert timing.FIRST_EVENT == "first_event"
    assert timing.VOCABULARY == "understand.vocabulary"
    assert timing.attempt_key(2) == "model.attempt_2"
    assert timing.call_key("linker/read-page") == "understand.call.linker/read-page"
    assert timing.tool_key("linker/read-page") == "model.tool.linker/read-page"


def test_phase_durations_are_recorded_and_non_negative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 2.0, 3.0, 4.0)
    clock = Timing()
    with phase(clock, timing.UNDERSTAND):
        pass
    assert clock.as_log() == {"understand": 1.0, "total": 4.0}


def test_a_phase_that_raises_is_still_timed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 4.5, 5.0)
    clock = Timing()
    with pytest.raises(RuntimeError):
        with phase(clock, timing.attempt_key(1)):
            raise RuntimeError("the model endpoint exploded")
    # The failed attempt is exactly the duration latency work is after.
    assert clock.as_log() == {"model.attempt_1": 3.5, "total": 5.0}


def test_re_entered_phases_accumulate_instead_of_overwriting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0, 4.5, 5.0)
    clock = Timing()
    with phase(clock, timing.GROUND):
        pass  # 1.0 s
    with phase(clock, timing.GROUND):
        pass  # 1.5 s
    assert clock.as_log() == {"ground": 2.5, "total": 5.0}


def test_observe_adds_durations_measured_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0)
    clock = Timing()
    clock.observe(timing.call_key("linker/read-page"), 0.25)
    clock.observe(timing.call_key("linker/read-page"), 0.5)
    assert clock.as_log()["understand.call.linker/read-page"] == 0.75


def test_adopt_takes_another_timings_phases_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0, 4.0)
    layer = Timing()  # the understanding layer's own clock
    with phase(layer, timing.JEV):
        pass  # 1.0 s
    turn = Timing()
    turn.observe(timing.MODEL, 0.5)
    turn.adopt(layer)
    record = turn.as_log()
    assert record["understand.jev"] == 1.0
    assert record["model"] == 0.5


def test_adopting_the_clock_into_itself_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The review's deadlock case: a non-reentrant lock must not be taken twice."""
    _ticks(monkeypatch, 1.0)
    clock = Timing()
    clock.observe(timing.MODEL, 0.5)
    clock.adopt(clock)
    assert clock.as_log() == {"model": 0.5, "total": 1.0}


def test_the_first_event_mark_is_set_once_and_the_total_never_shrinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0)
    clock = Timing()
    clock.mark_first_event()  # at 1.0
    clock.mark_first_event()  # a second mark (no second event exists) changes nothing
    assert clock.as_log() == {"first_event": 1.0, "total": 2.0}
    assert clock.as_log() == {"first_event": 1.0, "total": 3.0}


def test_the_partial_record_carries_the_phases_but_no_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The INSERT shape (#336 review): no `total` before the stream ran, so a
    turn that never streamed can never be read as a fast one."""
    _ticks(monkeypatch, 2.0, 3.0)  # every tick is consumed: no read may remain
    clock = Timing()
    with phase(clock, timing.UNDERSTAND):
        pass
    assert clock.as_log(complete=False) == {"understand": 1.0}


def test_the_partial_record_keeps_a_first_event_mark_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0)
    clock = Timing()
    clock.mark_first_event()
    assert clock.as_log(complete=False) == {"first_event": 1.0}


def test_skipped_phases_are_absent_never_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0)
    clock = Timing()
    with phase(clock, timing.UNDERSTAND):
        pass
    record = clock.as_log()
    assert "model" not in record
    assert timing.FIRST_EVENT not in record
    assert record == {"understand": 1.0, "total": 3.0}


def test_without_a_clock_the_phase_seam_runs_untimed() -> None:
    with phase(None, timing.MODEL):  # the seam every caller may leave out
        pass
