"""Acquire only the official source; retries are bounded idempotent GETs."""

from .pv_source import PvSource
from .pvgis_transport import PvgisTransport
from .records import Lease
from .weather_fetch_plan import WeatherFetchPlan
from .weather_journal import WeatherJournal
from .weather_task import WeatherTask
from .worker import Control


class WeatherAcquisition:
    def __init__(self, journal: WeatherJournal, transport: PvgisTransport) -> None:
        self.journal, self.transport = journal, transport

    def acquire(
        self, lease: Lease, plan: WeatherFetchPlan, control: Control
    ) -> PvSource:
        intent = self.journal.begin(lease, plan)
        # Reuse a complete validated original even after the network deadline.
        # Publication authority is still checked independently by Jobs.complete.
        control.checkpoint()
        captured = self.journal.captured_source(intent)
        if captured is not None:
            return captured
        task = WeatherTask(self.journal.workspace, lease, control, intent.deadline_at)
        downloaded = self.transport.download(
            plan,
            deadline=intent.deadline_at,
            clock=self.journal.workspace.clock,
            guard=task.check,
        )
        task.check()
        self.journal.retain_capture(
            lease,
            intent,
            downloaded.source,
            downloaded.retain_evidence(self.journal.workspace.blobs),
        )
        return downloaded.source
