"""Durable start/capture evidence, separate from a task's publication authority.

Only a current lease can consume the one POST permit. Late provider facts may
still be retained using its issued private intent; they grant no new lease and
cannot publish a project asset or change the task's terminal state.
"""

from __future__ import annotations

import math
import sqlite3
from typing import cast
from uuid import uuid4

from .apify_run import TERMINAL, ApifyRun
from .canonical import Object, encode
from .dependencies import verify_dependencies
from .errors import Conflict, InvalidInput, NotFound, PlanningError, VersionUnavailable
from .frozen_run import frozen_manifest
from .jobs import Jobs
from .pv_source import PvSource
from .pvgis_tmy import tmy_weather
from .records import Actor, Lease
from .weather_fetch_plan import WeatherFetchPlan
from .weather_intent import WeatherIntent
from .workspace import Workspace


class WeatherStartUnknown(PlanningError):
    """The single POST was issued; do not infer whether a remote run was created."""

    code = "weather_start_unknown"


class WeatherDeadlineExceeded(PlanningError):
    code = "weather_deadline_exceeded"


class WeatherJournal:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.jobs = Jobs(workspace)

    @staticmethod
    def _intent(row: sqlite3.Row) -> WeatherIntent:
        return WeatherIntent(
            row["run_id"],
            row["manifest_sha256"],
            row["plan_sha256"],
            row["nonce"],
            row["deadline_at"],
            not row["post_claimed"],
            row["remote_run_id"],
            row["acknowledgement_sha256"],
            row["observation_sha256"],
            row["capture_sha256"],
            row["abort_sha256"],
        )

    @staticmethod
    def _row(connection: sqlite3.Connection, intent: WeatherIntent) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM weather_acquisitions WHERE run_id=?", (intent.run_id,)
        ).fetchone()
        if row is None or any(
            row[name] != getattr(intent, name)
            for name in ("manifest_sha256", "plan_sha256", "nonce", "deadline_at")
        ):
            raise Conflict("weather intent does not match the durable operation")
        return cast(sqlite3.Row, row)

    def begin(self, lease: Lease, plan: WeatherFetchPlan) -> WeatherIntent:
        plan = WeatherFetchPlan.from_document(plan.document())
        manifest_hash = lease.request.get("manifest_sha256")
        if lease.kind != "evaluate" or not isinstance(manifest_hash, str):
            raise InvalidInput("a frozen evaluation lease is required")
        manifest = frozen_manifest(self.workspace, lease, manifest_hash)
        plan_hash = self.workspace.blobs.put_object(plan.document())
        context = manifest.get("context")
        pinned = context.get("assets") if isinstance(context, dict) else None
        if (
            not isinstance(pinned, dict)
            or pinned.get("weather_acquisition.plan") != plan_hash
        ):
            raise VersionUnavailable(
                "weather acquisition plan was not frozen by this run"
            )
        with self.workspace.database.transaction() as connection:
            now = self.workspace.clock()
            self.jobs.require_active(connection, lease, now)
            row = connection.execute(
                "SELECT * FROM weather_acquisitions WHERE run_id=?", (lease.run_id,)
            ).fetchone()
            if row is not None:
                if (row["manifest_sha256"], row["plan_sha256"]) != (
                    manifest_hash,
                    plan_hash,
                ):
                    raise Conflict(
                        "weather operation already has a different frozen plan"
                    )
                return self._intent(row)
            deadline = now + plan.limits.max_elapsed_seconds
            if not math.isfinite(deadline) or deadline <= now:
                raise InvalidInput("weather acquisition deadline is not representable")
            connection.execute(
                "INSERT INTO weather_acquisitions "
                "(run_id,schema_version,manifest_sha256,plan_sha256,nonce,post_claimed,started_at,deadline_at) "
                "VALUES (?,1,?,?,?,0,?,?)",
                (lease.run_id, manifest_hash, plan_hash, uuid4().hex, now, deadline),
            )
            row = connection.execute(
                "SELECT * FROM weather_acquisitions WHERE run_id=?", (lease.run_id,)
            ).fetchone()
            assert row is not None
            return self._intent(row)

    def authorize_post(self, lease: Lease, intent: WeatherIntent) -> None:
        """Commit immediately before the one POST, never in its network transaction."""
        if lease.run_id != intent.run_id:
            raise Conflict("weather intent belongs to another task")
        with self.workspace.database.transaction() as connection:
            now = self.workspace.clock()
            self.jobs.require_active(connection, lease, now)
            row = self._row(connection, intent)
            if row["post_claimed"]:
                raise WeatherStartUnknown(
                    "the weather start outcome needs provider evidence"
                )
            if row["deadline_at"] <= now:
                raise WeatherDeadlineExceeded("weather acquisition deadline has passed")
            connection.execute(
                "UPDATE weather_acquisitions SET post_claimed=1 WHERE run_id=?",
                (intent.run_id,),
            )

    def current(self, intent: WeatherIntent) -> WeatherIntent:
        with self.workspace.database.read() as connection:
            return self._intent(self._row(connection, intent))

    def require_issued(
        self, connection: sqlite3.Connection, intent: WeatherIntent
    ) -> WeatherIntent:
        """Bind private admission to the existing consumed start in its transaction."""
        current = self._intent(self._row(connection, intent))
        if current.may_start:
            raise Conflict("weather start permit was never consumed")
        return current

    def for_run(self, run_id: str) -> WeatherIntent:
        """Private worker/operator lookup; customer reads must use owned view."""
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM weather_acquisitions WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is None:
                raise NotFound("weather acquisition not found")
            return self._intent(row)

    def plan(self, intent: WeatherIntent) -> WeatherFetchPlan:
        current = self.current(intent)
        return WeatherFetchPlan.from_document(
            self.workspace.blobs.object(current.plan_sha256)
        )

    def observation(self, intent: WeatherIntent) -> ApifyRun | None:
        current = self.current(intent)
        if current.observation_sha256 is None:
            return None
        return ApifyRun.read(self.workspace.blobs.object(current.observation_sha256))

    def _record(
        self, intent: WeatherIntent, run: ApifyRun, *, kind: str
    ) -> WeatherIntent:
        run = ApifyRun.read(run.document())
        document_hash = self.workspace.blobs.put_object(run.document())
        with self.workspace.database.transaction() as connection:
            row = self._row(connection, intent)
            if not row["post_claimed"]:
                raise Conflict("weather operation has not issued a start permit")
            acknowledgement = row["acknowledgement_sha256"]
            if acknowledgement is None:
                if kind != "acknowledgement":
                    raise Conflict("weather provider run has not been acknowledged")
                connection.execute(
                    "UPDATE weather_acquisitions SET remote_run_id=?,acknowledgement_sha256=? WHERE run_id=?",
                    (run.id, document_hash, intent.run_id),
                )
            else:
                previous = ApifyRun.read(self.workspace.blobs.object(acknowledgement))
                if (
                    previous.identity() != run.identity()
                    or previous.started_at != run.started_at
                ):
                    raise Conflict("weather provider run identity or storage changed")
            observation = row["observation_sha256"]
            if observation is not None:
                previous = ApifyRun.read(self.workspace.blobs.object(observation))
                if previous.status in TERMINAL:
                    if run.status in TERMINAL and run.status != previous.status:
                        raise Conflict("weather provider terminal status changed")
                    # Late nonterminal replies cannot erase a terminal fact.
                    document_hash_for_progress = observation
                else:
                    document_hash_for_progress = document_hash
            else:
                document_hash_for_progress = document_hash
            connection.execute(
                "UPDATE weather_acquisitions SET observation_sha256=? WHERE run_id=?",
                (document_hash_for_progress, intent.run_id),
            )
            if kind == "abort":
                connection.execute(
                    "UPDATE weather_acquisitions SET abort_sha256=? WHERE run_id=?",
                    (document_hash, intent.run_id),
                )
            return self._intent(self._row(connection, intent))

    def acknowledge(self, intent: WeatherIntent, run: ApifyRun) -> WeatherIntent:
        return self._record(intent, run, kind="acknowledgement")

    def observe(self, intent: WeatherIntent, run: ApifyRun) -> WeatherIntent:
        return self._record(intent, run, kind="observation")

    def abort_reply(self, intent: WeatherIntent, run: ApifyRun) -> WeatherIntent:
        return self._record(intent, run, kind="abort")

    def retain_capture(
        self, intent: WeatherIntent, source: PvSource, evidence: Object
    ) -> WeatherIntent:
        plan = self.plan(intent)
        if encode(source.request.model_dump(mode="json")) != encode(
            plan.request.model_dump(mode="json")
        ) or encode(source.interpretation.model_dump(mode="json")) != encode(
            plan.interpretation.model_dump(mode="json")
        ):
            raise Conflict(
                "captured weather does not match the frozen request or interpretation"
            )
        # The one original-TMY interpreter validates complete data before any
        # journal reference is published. This runs outside a write transaction.
        tmy_weather(
            source.content,
            source.request,
            source.capture,
            source.interpretation,
            max_bytes=plan.limits.max_response_bytes,
            max_rows=plan.limits.max_weather_rows,
        )
        verify_dependencies(self.workspace.blobs, evidence)
        raw_hash = self.workspace.blobs.put(source.content)
        evidence_hash = self.workspace.blobs.put_object(evidence)
        evidence_children = evidence.get("dependencies", {})
        if not isinstance(evidence_children, dict):
            raise VersionUnavailable("invalid capture evidence dependencies")
        current = self.current(intent)
        if current.observation_sha256 is None or current.acknowledgement_sha256 is None:
            raise Conflict("weather provider run has not been acknowledged")
        observed = ApifyRun.read(
            self.workspace.blobs.object(current.observation_sha256)
        )
        if (
            observed.status != "SUCCEEDED"
            or source.capture.source_identifiers.get("apify_run_id") != observed.id
        ):
            raise Conflict(
                "only the acknowledged succeeded run may supply captured weather"
            )
        capture_hash = self.workspace.blobs.put_object(
            {
                "schema_version": 1,
                "kind": "retained_apify_tmy_capture_v1",
                **source.metadata(),
                "dependencies": {
                    "weather_original": raw_hash,
                    "acquisition_plan": current.plan_sha256,
                    "start_acknowledgement": current.acknowledgement_sha256,
                    "final_observation": current.observation_sha256,
                    "capture_evidence": evidence_hash,
                    **{
                        "capture." + name: value
                        for name, value in evidence_children.items()
                    },
                },
            }
        )
        with self.workspace.database.transaction() as connection:
            row = self._row(connection, intent)
            if (
                row["capture_sha256"] is not None
                and row["capture_sha256"] != capture_hash
            ):
                raise Conflict(
                    "weather operation already retained a different original capture"
                )
            connection.execute(
                "UPDATE weather_acquisitions SET capture_sha256=? WHERE run_id=?",
                (capture_hash, intent.run_id),
            )
            return self._intent(self._row(connection, intent))

    def captured_source(self, intent: WeatherIntent) -> PvSource | None:
        current = self.current(intent)
        if current.capture_sha256 is None:
            return None
        metadata = self.workspace.blobs.object(current.capture_sha256)
        verify_dependencies(self.workspace.blobs, metadata)
        dependencies = metadata.get("dependencies")
        raw_hash = (
            dependencies.get("weather_original")
            if isinstance(dependencies, dict)
            else None
        )
        if not isinstance(raw_hash, str):
            raise VersionUnavailable("retained weather capture has no original")
        return PvSource.read(self.workspace.blobs, raw_hash, metadata)

    def view(
        self, actor: Actor, run_id: str, *, allow_not_started: bool = False
    ) -> Object:
        local = self.workspace.run(actor, run_id)
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM weather_acquisitions WHERE run_id=?", (run_id,)
            ).fetchone()
            if row is None:
                if allow_not_started:
                    return {
                        "schema_version": 1,
                        "run_id": run_id,
                        "task_state": local.state,
                        "acquisition_state": "not_started",
                    }
                raise NotFound("weather acquisition not found")
            intent = self._intent(row)
            cleanup = connection.execute(
                "SELECT state,attempt,max_attempts,error_sha256 FROM jobs WHERE run_id=? AND kind='abort_weather'",
                (run_id,),
            ).fetchone()
            reconciliation = connection.execute(
                "SELECT id,state,attempt,max_attempts,error_sha256,output_sha256 FROM jobs "
                "WHERE run_id=? AND kind='reconcile_weather' ORDER BY created_at DESC,id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
        status = "ready_to_start" if intent.may_start else "start_outcome_unknown"
        observed: Object | None = None
        if intent.observation_sha256 is not None:
            observed = self.workspace.blobs.object(intent.observation_sha256)
            status = str(observed.get("status"))
        if intent.capture_sha256 is not None:
            status = "captured"
        return {
            "schema_version": 1,
            "run_id": run_id,
            "task_state": local.state,
            "acquisition_state": status,
            "plan_sha256": intent.plan_sha256,
            "observation": observed,
            "capture_sha256": intent.capture_sha256,
            "abort_sha256": intent.abort_sha256,
            "reconciliation": None
            if reconciliation is None
            else {
                "id": reconciliation["id"],
                "state": reconciliation["state"],
                "attempt": reconciliation["attempt"],
                "max_attempts": reconciliation["max_attempts"],
                "error": self.workspace.blobs.object(reconciliation["error_sha256"])
                if reconciliation["error_sha256"]
                else None,
                "output_sha256": reconciliation["output_sha256"],
            },
            "cleanup": None
            if cleanup is None
            else {
                "state": cleanup["state"],
                "attempt": cleanup["attempt"],
                "max_attempts": cleanup["max_attempts"],
                "error": self.workspace.blobs.object(cleanup["error_sha256"])
                if cleanup["error_sha256"]
                else None,
            },
        }
