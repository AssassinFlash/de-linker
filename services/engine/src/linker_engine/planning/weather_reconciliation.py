"""Leased private recovery changes provider evidence, never a project/result."""

from __future__ import annotations

from collections.abc import Callable

from .apify_transport import ApifyTransport
from .apify_weather_client import ApifyWeatherClient
from .canonical import Object
from .errors import Conflict, InvalidInput, VersionUnavailable
from .frozen_run import frozen_manifest
from .records import Lease
from .weather_connection import weather_connection
from .weather_fetch_plan import WeatherFetchLimits
from .weather_journal import WeatherJournal
from .weather_known_run import KnownWeatherRun
from .weather_reconcile_request import WeatherReconcileRequest
from .weather_task import WeatherTask
from .worker import Control
from .workspace import Workspace


class WeatherReconciliation:
    def __init__(
        self,
        workspace: Workspace,
        *,
        connection: Callable[[WeatherFetchLimits], ApifyTransport] = weather_connection,
    ) -> None:
        self.workspace, self.connection = workspace, connection

    def __call__(self, lease: Lease, control: Control) -> Object:
        if lease.kind != "reconcile_weather":
            raise InvalidInput("weather reconciliation lease required")
        request = WeatherReconcileRequest.read(lease.request)
        journal = WeatherJournal(self.workspace)
        intent = journal.for_run(lease.run_id)
        if (request.manifest_sha256, request.weather_plan_sha256) != (
            intent.manifest_sha256,
            intent.plan_sha256,
        ):
            raise VersionUnavailable("reconciliation differs from the original intent")
        frozen_manifest(self.workspace, lease, intent.manifest_sha256)
        plan = journal.plan(intent)
        with self.workspace.database.read() as connection:
            journal.require_issued(connection, intent)
            job = connection.execute(
                "SELECT created_at FROM jobs WHERE id=?", (lease.id,)
            ).fetchone()
            producer = connection.execute(
                "SELECT state FROM jobs WHERE run_id=? AND kind='evaluate'",
                (lease.run_id,),
            ).fetchone()
        if job is None or producer is None:
            raise VersionUnavailable("reconciliation or original evaluation is missing")
        if request.action in ("capture", "stop") and producer["state"] not in (
            "failed",
            "cancelled",
        ):
            raise Conflict("capture or stop requires an inactive terminal producer")
        task = WeatherTask(
            self.workspace,
            lease,
            control,
            job["created_at"] + plan.limits.max_elapsed_seconds,
        )
        task.check()
        transport = self.connection(plan.limits)
        try:
            client = ApifyWeatherClient(transport)
            remote = KnownWeatherRun(journal, client, task, intent)
            if request.action == "acknowledge":
                assert request.provider_run_id is not None
                observed = client.read(request.provider_run_id, task.check)
                client.verified_input(observed, plan, intent.nonce, task.check)
                # Keep a verified late fact; this cannot complete an old task.
                intent = journal.acknowledge(intent, observed)
            elif request.action == "observe":
                remote.refresh()
            elif request.action == "capture":
                remote.capture()
            else:
                remote.stop()
        finally:
            transport.close()
        task.check()
        current = journal.current(intent)
        final = journal.observation(current)
        dependencies: Object = {
            "acquisition_plan": current.plan_sha256,
            "original_manifest": current.manifest_sha256,
            **(
                {"start_acknowledgement": current.acknowledgement_sha256}
                if current.acknowledgement_sha256
                else {}
            ),
            **(
                {"provider_observation": current.observation_sha256}
                if current.observation_sha256
                else {}
            ),
            **(
                {"weather_capture": current.capture_sha256}
                if current.capture_sha256
                else {}
            ),
            **({"abort_reply": current.abort_sha256} if current.abort_sha256 else {}),
        }
        return {
            "schema_version": 1,
            "kind": "reconcile_weather_v1",
            "run_id": lease.run_id,
            "action": request.action,
            "provider": None if final is None else final.document(),
            "capture_sha256": current.capture_sha256,
            "dependencies": dependencies,
        }
