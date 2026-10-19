"""The passive turn clock: phases accumulate, records stay non-negative.

Durations come from `time.monotonic()`, so these tests drive that clock through
a fixed tick sequence instead of sleeping: every assertion is exact, never a
race with the machine's timer. `_ticks(monkeypatch, *reads)` fixes the reads a
`Timing()` makes after its constructor's own (which reads 0.0); monkeypatch
restores the real clock after each test.
"""

import time

import pytest

from linker_genie.timing import Timing, phase


def _ticks(monkeypatch: pytest.MonkeyPatch, *reads: float) -> None:
    values = iter((0.0, *reads))
    monkeypatch.setattr(time, "monotonic", lambda: next(values))


def test_phase_durations_are_recorded_and_non_negative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 2.0, 3.0, 4.0)
    clock = Timing()
    with phase(clock, "understand"):
        pass
    assert clock.as_log() == {"understand": 1.0, "total": 4.0}


def test_a_phase_that_raises_is_still_timed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 4.5, 5.0)
    clock = Timing()
    with pytest.raises(RuntimeError):
        with phase(clock, "model.attempt_1"):
            raise RuntimeError("the model endpoint exploded")
    # The failed attempt is exactly the duration latency work is after.
    assert clock.as_log() == {"model.attempt_1": 3.5, "total": 5.0}


def test_re_entered_phases_accumulate_instead_of_overwriting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0, 4.5, 5.0)
    clock = Timing()
    with phase(clock, "ground"):
        pass  # 1.0 s
    with phase(clock, "ground"):
        pass  # 1.5 s
    assert clock.as_log() == {"ground": 2.5, "total": 5.0}


def test_observe_adds_durations_measured_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0)
    clock = Timing()
    clock.observe("understand.call.linker/read-page", 0.25)
    clock.observe("understand.call.linker/read-page", 0.5)
    assert clock.as_log()["understand.call.linker/read-page"] == 0.75


def test_adopt_takes_another_timings_phases_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0, 4.0)
    layer = Timing()  # the understanding layer's own clock
    with phase(layer, "understand.jev"):
        pass  # 1.0 s
    turn = Timing()
    turn.observe("model", 0.5)
    turn.adopt(layer)
    record = turn.as_log()
    assert record["understand.jev"] == 1.0
    assert record["model"] == 0.5


def test_the_first_event_mark_is_set_once_and_the_total_never_shrinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0)
    clock = Timing()
    clock.first_event()  # at 1.0
    clock.first_event()  # a second call (no second event exists) changes nothing
    assert clock.as_log() == {"first_event": 1.0, "total": 2.0}
    assert clock.as_log() == {"first_event": 1.0, "total": 3.0}


def test_skipped_phases_are_absent_never_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ticks(monkeypatch, 1.0, 2.0, 3.0)
    clock = Timing()
    with phase(clock, "understand"):
        pass
    record = clock.as_log()
    assert "model" not in record
    assert "first_event" not in record
    assert record == {"understand": 1.0, "total": 3.0}


def test_without_a_clock_the_phase_seam_runs_untimed() -> None:
    with phase(None, "model"):  # the seam every caller may leave out
        pass
