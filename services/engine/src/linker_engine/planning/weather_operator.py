"""Private operator admission; all provider work remains in leased jobs."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from . import commands
from .canonical import Object
from .errors import Conflict, InvalidInput, NotFound, VersionUnavailable
from .execution_control import require_accepting
from .execution_identity import request_execution_key
from .records import Actor
from .weather_journal import WeatherJournal
from .weather_reconcile_request import WeatherAction, WeatherReconcileRequest
from .workspace import Workspace

if TYPE_CHECKING:
    from .weather_kernel import WeatherKernel


class WeatherOperator:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.journal = WeatherJournal(workspace)

    def inspect(self, run_id: str) -> Object:
        intent = self.journal.for_run(run_id)
        with self.workspace.database.read() as connection:
            rows = connection.execute(
                "SELECT id,kind,state,attempt,max_attempts,error_sha256,output_sha256 "
                "FROM jobs WHERE run_id=? ORDER BY created_at,id",
                (run_id,),
            ).fetchall()
        observed = self.journal.observation(intent)
        return {
            "schema_version": 1,
            "run_id": run_id,
            "manifest_sha256": intent.manifest_sha256,
            "plan_sha256": intent.plan_sha256,
            "deadline_at": intent.deadline_at,
            "start_permit_consumed": not intent.may_start,
            "provider": None if observed is None else observed.document(),
            "capture_sha256": intent.capture_sha256,
            "abort_sha256": intent.abort_sha256,
            "jobs": [{**dict(row)} for row in rows],
        }

    def admit(
        self,
        actor: Actor,
        run_id: str,
        action: WeatherAction,
        *,
        provider_run_id: str | None = None,
        key: str,
    ) -> Object:
        if actor.kind != "team":
            raise InvalidInput("private operator identity required")
        intent = self.journal.for_run(run_id)
        request = WeatherReconcileRequest.read(
            {
                "schema_version": 1,
                "kind": "reconcile_weather_v1",
                "manifest_sha256": intent.manifest_sha256,
                "weather_plan_sha256": intent.plan_sha256,
                "action": action,
                "provider_run_id": provider_run_id,
            }
        ).document()
        command: Object = {"run_id": run_id, "request": request}
        command_hash = commands.command_hash(command, key)
        scope = "weather-reconcile:" + run_id
        with self.workspace.database.transaction() as connection:
            replay = commands.replay(
                connection, self.workspace.blobs, actor, scope, key, command_hash
            )
            if replay is not None:
                return replay
            current = self.journal.require_issued(connection, intent)
            producer = connection.execute(
                "SELECT state,max_attempts FROM jobs WHERE run_id=? AND kind='evaluate'",
                (run_id,),
            ).fetchone()
            if producer is None:
                raise NotFound("weather evaluation is absent")
            if action in ("capture", "stop") and producer["state"] not in (
                "failed",
                "cancelled",
            ):
                raise Conflict("capture or stop requires an inactive terminal producer")
            if action != "acknowledge" and current.remote_run_id is None:
                raise Conflict("known provider identity required; acknowledge first")
            if action == "acknowledge" and current.remote_run_id not in (
                None,
                provider_run_id,
            ):
                raise Conflict("a different provider identity is already acknowledged")
            if (
                connection.execute(
                    "SELECT 1 FROM jobs WHERE run_id=? AND kind='reconcile_weather' "
                    "AND state IN ('queued','running','retry_wait')",
                    (run_id,),
                ).fetchone()
                is not None
            ):
                raise Conflict("a weather reconciliation is already pending")
            job_id = uuid4().hex
            now = self.workspace.clock()
            connection.execute(
                "INSERT INTO jobs (id,run_id,kind,request_sha256,state,max_attempts,available_at,created_at,updated_at) "
                "VALUES (?,?,'reconcile_weather',?,'queued',?,?,?,?)",
                (
                    job_id,
                    run_id,
                    self.workspace.blobs.put_object(request),
                    producer["max_attempts"],
                    now,
                    now,
                    now,
                ),
            )
            receipt: Object = {
                "schema_version": 1,
                "run_id": run_id,
                "job_id": job_id,
                "action": action,
            }
            commands.remember(
                connection,
                self.workspace.blobs,
                actor,
                scope,
                key,
                command_hash,
                receipt,
                now,
            )
            return receipt

    def resume(
        self, actor: Actor, run_id: str, kernel: WeatherKernel | None, *, key: str
    ) -> Object:
        """Spend a remaining original attempt; never reset its manifest or budget."""
        if actor.kind != "team":
            raise InvalidInput("private operator identity required")
        intent = self.journal.for_run(run_id)
        command: Object = {
            "schema_version": 1,
            "run_id": run_id,
            "action": "resume",
            "manifest_sha256": intent.manifest_sha256,
        }
        command_hash = commands.command_hash(command, key)
        scope = "weather-resume:" + run_id
        with self.workspace.database.transaction() as connection:
            replay = commands.replay(
                connection, self.workspace.blobs, actor, scope, key, command_hash
            )
            if replay is not None:
                return replay
            require_accepting(connection)
            current = self.journal.require_issued(connection, intent)
            if kernel is None or kernel.workspace is not self.workspace:
                raise VersionUnavailable("matching weather executor required")
            producer = connection.execute(
                "SELECT * FROM jobs WHERE run_id=? AND kind='evaluate'", (run_id,)
            ).fetchone()
            if producer is None or producer["state"] != "failed":
                raise Conflict("only a failed original weather evaluation may resume")
            if producer["attempt"] >= producer["max_attempts"]:
                raise Conflict("original weather attempt budget is exhausted")
            if (
                connection.execute(
                    "SELECT 1 FROM jobs WHERE run_id=? AND kind IN ('abort_weather','reconcile_weather') "
                    "AND state IN ('queued','running','retry_wait')",
                    (run_id,),
                ).fetchone()
                is not None
            ):
                raise Conflict("weather maintenance is still pending")
            if current.remote_run_id is None:
                raise Conflict(
                    "a verified provider identity is required before resuming"
                )
            if (
                current.capture_sha256 is None
                and self.workspace.clock() >= current.deadline_at
            ):
                raise Conflict(
                    "original acquisition deadline expired; recover its capture first"
                )
            request = self.workspace.blobs.object(producer["request_sha256"])
            manifest = self.workspace.blobs.object(current.manifest_sha256)
            if (
                request_execution_key(request, manifest, current.manifest_sha256)
                != kernel.execution_key()
            ):
                raise VersionUnavailable(
                    "executor differs from the original weather runtime"
                )
            now = self.workspace.clock()
            receipt: Object = {
                "schema_version": 1,
                "run_id": run_id,
                "job_id": producer["id"],
                "action": "resume",
                "previous_attempt": producer["attempt"],
                "max_attempts": producer["max_attempts"],
                "dependencies": {
                    "original_manifest": current.manifest_sha256,
                    "acquisition_plan": current.plan_sha256,
                    **(
                        {"previous_failure": producer["error_sha256"]}
                        if producer["error_sha256"]
                        else {}
                    ),
                    **(
                        {"weather_capture": current.capture_sha256}
                        if current.capture_sha256
                        else {}
                    ),
                },
            }
            connection.execute(
                "UPDATE jobs SET state='queued',available_at=?,worker=NULL,lease_token=NULL,lease_until=NULL,updated_at=? WHERE id=?",
                (now, now, producer["id"]),
            )
            commands.remember(
                connection,
                self.workspace.blobs,
                actor,
                scope,
                key,
                command_hash,
                receipt,
                now,
            )
            return receipt
