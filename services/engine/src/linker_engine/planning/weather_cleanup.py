"""Durable cancellation cleanup uses the existing leased job queue.

It is attached to the original run, has one unique job, and cannot turn its
cancelled evaluation into success or publish a source. Unknown starts need
provider evidence; no cleanup path repeats the Actor start.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from uuid import uuid4

from .apify_transport import ApifyTransport
from .apify_weather_client import ApifyWeatherClient
from .canonical import Object, encode
from .errors import InvalidInput, VersionUnavailable
from .frozen_run import frozen_manifest
from .records import Lease
from .weather_connection import weather_connection
from .weather_fetch_plan import WeatherFetchLimits
from .weather_journal import WeatherJournal, WeatherStartUnknown
from .weather_known_run import KnownWeatherRun
from .weather_task import WeatherTask
from .worker import Control
from .workspace import Workspace


def cleanup_request(manifest_sha256: str, plan_sha256: str) -> Object:
    return {
        "schema_version": 1,
        "kind": "abort_weather_acquisition_v1",
        "manifest_sha256": manifest_sha256,
        "weather_plan_sha256": plan_sha256,
    }


def enqueue_cleanup(
    workspace: Workspace, connection: sqlite3.Connection, run_id: str
) -> None:
    intent = connection.execute(
        "SELECT * FROM weather_acquisitions WHERE run_id=? AND post_claimed=1 AND capture_sha256 IS NULL",
        (run_id,),
    ).fetchone()
    if intent is None:
        return
    job = connection.execute(
        "SELECT max_attempts FROM jobs WHERE run_id=? AND kind='evaluate'", (run_id,)
    ).fetchone()
    if job is None:
        raise VersionUnavailable("weather evaluation is missing")
    request = workspace.blobs.put_object(
        cleanup_request(intent["manifest_sha256"], intent["plan_sha256"])
    )
    now = workspace.clock()
    connection.execute(
        "INSERT INTO jobs (id,run_id,kind,request_sha256,state,max_attempts,available_at,created_at,updated_at) "
        "VALUES (?,?,'abort_weather',?,'queued',?,?,?,?) "
        "ON CONFLICT(run_id) WHERE kind='abort_weather' DO NOTHING",
        (uuid4().hex, run_id, request, job["max_attempts"], now, now, now),
    )


class WeatherCleanup:
    def __init__(
        self,
        workspace: Workspace,
        *,
        connection: Callable[[WeatherFetchLimits], ApifyTransport] = weather_connection,
    ) -> None:
        self.workspace, self.connection = workspace, connection

    def __call__(self, lease: Lease, control: Control) -> Object:
        if lease.kind != "abort_weather":
            raise InvalidInput("weather cleanup lease required")
        journal = WeatherJournal(self.workspace)
        intent = journal.for_run(lease.run_id)
        if encode(lease.request) != encode(
            cleanup_request(intent.manifest_sha256, intent.plan_sha256)
        ):
            raise VersionUnavailable(
                "cleanup request differs from the retained weather intent"
            )
        frozen_manifest(self.workspace, lease, intent.manifest_sha256)
        plan = journal.plan(intent)
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT created_at FROM jobs WHERE id=?", (lease.id,)
            ).fetchone()
        if row is None:
            raise VersionUnavailable("weather cleanup job is absent")
        task = WeatherTask(
            self.workspace,
            lease,
            control,
            row["created_at"] + plan.limits.max_elapsed_seconds,
        )
        task.check()
        transport = self.connection(plan.limits)
        try:
            KnownWeatherRun(journal, ApifyWeatherClient(transport), task, intent).stop()
        finally:
            transport.close()
        task.check()
        current = journal.current(intent)
        final = journal.observation(intent)
        if final is None:
            raise WeatherStartUnknown("weather cleanup has no provider observation")
        if current.observation_sha256 is None or current.acknowledgement_sha256 is None:
            raise VersionUnavailable(
                "weather cleanup has no retained provider evidence"
            )
        return {
            "schema_version": 1,
            "kind": "abort_weather_acquisition_v1",
            "run_id": lease.run_id,
            "provider": final.document(),
            "dependencies": {
                "weather_plan": intent.plan_sha256,
                "start_acknowledgement": current.acknowledgement_sha256,
                "provider_observation": current.observation_sha256,
                **(
                    {"abort_reply": current.abort_sha256}
                    if current.abort_sha256
                    else {}
                ),
            },
        }
