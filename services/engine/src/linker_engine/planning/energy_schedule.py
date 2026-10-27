"""The time-alignment boundary shared by single-unit and plant executors."""

from typing import Protocol

from .energy_inputs import ScheduleSegment


class EnergySchedule(Protocol):
    @property
    def coupling(self) -> str: ...

    @property
    def schedule(self) -> list[ScheduleSegment]: ...
