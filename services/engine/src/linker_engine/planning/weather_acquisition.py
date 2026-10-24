"""One durable external operation; no owned source or task-success publication.

The journal, active task fence and existing TMY interpreter remain authorities.
Transient reads resume the acknowledged provider run; an uncertain POST never
repeats. Recovery is a private operator primitive, not a public RPC or restart.
"""

from __future__ import annotations

import logging

from .apify_run import TERMINAL, ApifyRun
from .apify_weather_client import ApifyWeatherClient
from .canonical import encode
from .errors import LeaseLost, PlanningError, VersionUnavailable
from .pv_source import PvSource
from .records import Lease
from .weather_fetch_errors import WeatherPollingLimit, WeatherRemoteFailed
from .weather_fetch_plan import WeatherFetchPlan
from .weather_intent import WeatherIntent
from .weather_journal import (
    WeatherDeadlineExceeded,
    WeatherJournal,
    WeatherStartUnknown,
)
from .worker import Control

LOG = logging.getLogger(__name__)


class WeatherAcquisition:
    def __init__(self, journal: WeatherJournal, client: ApifyWeatherClient) -> None:
        self.journal = journal
        self.client = client

    def _deadline(self, at: float) -> None:
        if self.journal.workspace.clock() >= at:
            raise WeatherDeadlineExceeded("weather acquisition deadline has passed")

    def _authority(self, lease: Lease, control: Control) -> None:
        control.checkpoint()
        with self.journal.workspace.database.read() as connection:
            self.journal.jobs.require_active(
                connection, lease, self.journal.workspace.clock()
            )

    def _active(self, lease: Lease, control: Control, at: float) -> None:
        self._authority(lease, control)
        self._deadline(at)

    def _limits(self, plan: WeatherFetchPlan) -> None:
        if encode(plan.limits.model_dump(mode="json")) != encode(
            self.client.transport.limits.model_dump(mode="json")
        ):
            raise VersionUnavailable("transport differs from the frozen weather limits")

    def _cancelled(self, lease: Lease) -> bool:
        with self.journal.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT state FROM jobs WHERE id=? AND run_id=?",
                (lease.id, lease.run_id),
            ).fetchone()
            return row is not None and row["state"] == "cancelled"

    def abort_known(self, intent: WeatherIntent) -> ApifyRun | None:
        """One bounded abort attempt; its response is evidence, not an assertion.

        A caller must already possess the private issued intent. This does not
        require the cancelled lease, grant publication rights or retry POST.
        """
        current = self.journal.current(intent)
        run = self.journal.observation(current)
        if run is None or run.status in TERMINAL:
            return run
        plan = self.journal.plan(current)
        self._limits(plan)
        # Cleanup is one call with the existing connection/read timeouts and a
        # separate checkpoint budget; it may start after the task's deadline.
        until = self.journal.workspace.clock() + min(
            plan.limits.max_elapsed_seconds,
            plan.limits.connect_timeout_seconds + plan.limits.read_timeout_seconds,
        )
        reply = self.client.abort(run.id, lambda: self._deadline(until))
        self.journal.abort_reply(current, reply)
        return reply

    def _cleanup(
        self, intent: WeatherIntent, *, cancelled_lease: Lease | None = None
    ) -> None:
        try:
            if cancelled_lease is not None and not self._cancelled(cancelled_lease):
                return
            self.abort_known(intent)
        except Exception as error:
            # A missing confirmation remains missing. Keep the known provider
            # identity for explicit recovery and never mask the original error.
            code = (
                error.code
                if isinstance(error, PlanningError)
                else "unexpected_cleanup_failure"
            )
            LOG.warning(
                "weather abort unconfirmed for task %s: %s", intent.run_id, code
            )

    def recover_acknowledgement(
        self, intent: WeatherIntent, provider_run_id: str
    ) -> WeatherIntent:
        """Adopt a known run only after its unique intent nonce is verified.

        May retain a late fact after cancellation/deadline. It cannot extend the
        original acquisition deadline or start/requeue/publish a local task.
        """
        current = self.journal.current(intent)
        if current.may_start:
            raise WeatherStartUnknown("no start permit was issued for recovery")
        plan = self.journal.plan(current)
        self._limits(plan)
        until = self.journal.workspace.clock() + plan.limits.max_elapsed_seconds

        def guard() -> None:
            self._deadline(until)

        run = self.client.read(provider_run_id, guard)
        self.client.verified_input(run, plan, current.nonce, guard)
        return self.journal.acknowledge(current, run)

    def acquire(
        self, lease: Lease, plan: WeatherFetchPlan, control: Control
    ) -> PvSource:
        self._limits(plan)
        intent = self.journal.begin(lease, plan)

        def guard() -> None:
            self._active(lease, control, intent.deadline_at)

        try:
            self._authority(lease, control)
            captured = self.journal.captured_source(intent)
            if captured is not None:
                self._authority(lease, control)
                return captured
            guard()
            observed = self.journal.observation(intent)
            if observed is None:
                if not intent.may_start:
                    raise WeatherStartUnknown(
                        "the issued start needs verified provider recovery"
                    )
                self.client.transport.ensure_credential()
                guard()
                self.journal.authorize_post(lease, intent)
                # Cancellation cannot discard a late acknowledgement. Deadline
                # checks and transport byte/inactivity bounds still apply.
                observed = self.client.start(
                    plan, intent.nonce, lambda: self._deadline(intent.deadline_at)
                )
                intent = self.journal.acknowledge(intent, observed)
            # The durable elapsed budget survives attempts. This explicit poll
            # count bounds each attempt; the task's max_attempts bounds retries.
            polls = 0
            while observed.status not in TERMINAL:
                guard()
                if polls >= plan.limits.max_polls:
                    raise WeatherPollingLimit("weather polling budget exhausted")
                observed = self.client.read(observed.id, guard)
                intent = self.journal.observe(intent, observed)
                polls += 1
                guard()
                if observed.status not in TERMINAL:
                    remaining = intent.deadline_at - self.journal.workspace.clock()
                    self._deadline(intent.deadline_at)
                    control.wait(min(plan.limits.poll_seconds, remaining))
            guard()
            if observed.status != "SUCCEEDED":
                raise WeatherRemoteFailed(
                    "the acknowledged weather run did not succeed"
                )
            downloaded = self.client.download(observed, plan, intent.nonce, guard)
            # Retaining verified late capture evidence grants no owned asset.
            intent = self.journal.retain_capture(
                intent,
                downloaded.source,
                downloaded.retain_evidence(self.journal.workspace.blobs),
            )
            guard()
            captured = self.journal.captured_source(intent)
            assert captured is not None
            return captured
        except LeaseLost:
            # A replacement lease may be resuming this same remote run. Only
            # confirmed local cancellation authorizes this old worker to abort.
            self._cleanup(intent, cancelled_lease=lease)
            raise
        except (WeatherDeadlineExceeded, WeatherPollingLimit):
            self._cleanup(intent)
            raise
