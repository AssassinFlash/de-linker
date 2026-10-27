"""Half-open real-time intervals; UTC, never a presumed 24-hour calendar day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .errors import InvalidInput


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidInput("an explicit offset or resolved local timezone is required")
    try:
        return value.astimezone(UTC)
    except (OverflowError, ValueError) as error:
        raise InvalidInput(
            "instant is outside the supported UTC date/time domain"
        ) from error


def microseconds(value: timedelta) -> int:
    # datetime's exact integer resolution; no floating coverage/gap tolerance.
    return (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start, end = utc(self.start), utc(self.end)
        if end <= start:
            raise InvalidInput("interval end must follow its start")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    @property
    def duration_us(self) -> int:
        return microseconds(self.end - self.start)

    @property
    def hours(self) -> float:
        # A unit conversion, not a calendar assumption: 3600 SI seconds/hour.
        return self.duration_us / 3_600_000_000


def regular_intervals(
    start: datetime, end: datetime, step: timedelta
) -> tuple[Interval, ...]:
    start, end = utc(start), utc(end)
    duration, step_us = microseconds(end - start), microseconds(step)
    if step_us <= 0 or duration <= 0 or duration % step_us:
        raise InvalidInput("positive horizon must be an exact multiple of the step")
    return tuple(
        Interval(start + index * step, start + (index + 1) * step)
        for index in range(duration // step_us)
    )
