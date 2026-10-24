"""One weather job's lease fence and explicit elapsed budget."""

from __future__ import annotations

import math

from .errors import InvalidInput
from .jobs import Jobs
from .records import Lease
from .weather_journal import WeatherDeadlineExceeded
from .worker import Control
from .workspace import Workspace


class WeatherTask:
    def __init__(
        self, workspace: Workspace, lease: Lease, control: Control, deadline: float
    ) -> None:
        if not math.isfinite(deadline):
            raise InvalidInput("finite weather job deadline required")
        self.workspace, self.lease, self.control, self.deadline = (
            workspace,
            lease,
            control,
            deadline,
        )

    def elapsed(self) -> None:
        if self.workspace.clock() >= self.deadline:
            raise WeatherDeadlineExceeded("weather job deadline has passed")

    def check(self) -> None:
        self.control.checkpoint()
        with self.workspace.database.read() as connection:
            Jobs(self.workspace).require_active(
                connection, self.lease, self.workspace.clock()
            )
        self.elapsed()

    def wait(self, seconds: float) -> None:
        self.check()
        self.control.wait(min(seconds, self.deadline - self.workspace.clock()))
        self.check()
