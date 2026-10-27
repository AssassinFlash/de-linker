"""Local idempotent-download evidence, separate from fenced source publication."""

from __future__ import annotations

import math
import sqlite3

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
            row["deadline_at"],
            row["capture_sha256"],
        )

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
            raise VersionUnavailable("weather plan was not frozen by this run")
        with self.workspace.database.transaction() as connection:
            now = self.workspace.clock()
            self.jobs.require_active(connection, lease, now)
            row = connection.execute(
                "SELECT * FROM weather_downloads WHERE run_id=?", (lease.run_id,)
            ).fetchone()
            if row is not None:
                if (row["manifest_sha256"], row["plan_sha256"]) != (
                    manifest_hash,
                    plan_hash,
                ):
                    raise Conflict("weather operation has a different frozen plan")
                return self._intent(row)
            deadline = now + plan.limits.max_elapsed_seconds
            if not math.isfinite(deadline) or deadline <= now:
                raise InvalidInput("weather acquisition deadline is not representable")
            connection.execute(
                "INSERT INTO weather_downloads (run_id,schema_version,manifest_sha256,plan_sha256,started_at,deadline_at) VALUES (?,1,?,?,?,?)",
                (lease.run_id, manifest_hash, plan_hash, now, deadline),
            )
            row = connection.execute(
                "SELECT * FROM weather_downloads WHERE run_id=?", (lease.run_id,)
            ).fetchone()
            assert row is not None
            return self._intent(row)

    def current(self, intent: WeatherIntent) -> WeatherIntent:
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM weather_downloads WHERE run_id=?", (intent.run_id,)
            ).fetchone()
            if row is None or any(
                row[name] != getattr(intent, name)
                for name in ("manifest_sha256", "plan_sha256", "deadline_at")
            ):
                raise Conflict("weather intent differs from its durable operation")
            return self._intent(row)

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

    def retain_capture(
        self, lease: Lease, intent: WeatherIntent, source: PvSource, evidence: Object
    ) -> WeatherIntent:
        current = self.current(intent)
        plan = WeatherFetchPlan.from_document(
            self.workspace.blobs.object(current.plan_sha256)
        )
        if encode(source.request.model_dump(mode="json")) != encode(
            plan.request.model_dump(mode="json")
        ) or encode(source.interpretation.model_dump(mode="json")) != encode(
            plan.interpretation.model_dump(mode="json")
        ):
            raise Conflict("captured weather differs from the frozen request")
        tmy_weather(
            source.content,
            source.request,
            source.capture,
            source.interpretation,
            max_bytes=plan.limits.max_response_bytes,
            max_rows=plan.limits.max_weather_rows,
        )
        verify_dependencies(self.workspace.blobs, evidence)
        evidence_children = evidence.get("dependencies")
        if not isinstance(evidence_children, dict):
            raise VersionUnavailable("weather transport evidence is incomplete")
        capture_hash = self.workspace.blobs.put_object(
            {
                "schema_version": 1,
                "kind": "retained_official_jrc_tmy_capture_v1",
                **source.metadata(),
                "dependencies": {
                    "weather_original": self.workspace.blobs.put(source.content),
                    "acquisition_plan": current.plan_sha256,
                    "capture_evidence": self.workspace.blobs.put_object(evidence),
                    **{
                        "capture." + name: value
                        for name, value in evidence_children.items()
                    },
                },
            }
        )
        with self.workspace.database.transaction() as connection:
            self.jobs.require_active(connection, lease, self.workspace.clock())
            if lease.run_id != intent.run_id:
                raise Conflict("weather capture belongs to another task")
            row = connection.execute(
                "SELECT capture_sha256 FROM weather_downloads WHERE run_id=?",
                (intent.run_id,),
            ).fetchone()
            if row is None or row["capture_sha256"] not in (None, capture_hash):
                raise Conflict("weather operation already retained a different capture")
            connection.execute(
                "UPDATE weather_downloads SET capture_sha256=? WHERE run_id=?",
                (capture_hash, intent.run_id),
            )
        return self.current(intent)

    def view(
        self, actor: Actor, run_id: str, *, allow_not_started: bool = False
    ) -> Object:
        local = self.workspace.run(actor, run_id)
        with self.workspace.database.read() as connection:
            row = connection.execute(
                "SELECT * FROM weather_downloads WHERE run_id=?", (run_id,)
            ).fetchone()
        if row is None:
            if not allow_not_started:
                raise NotFound("weather download not found")
            return {
                "schema_version": 1,
                "run_id": run_id,
                "task_state": local.state,
                "acquisition_state": "not_started",
            }
        return {
            "schema_version": 1,
            "run_id": run_id,
            "task_state": local.state,
            "acquisition_state": "captured" if row["capture_sha256"] else "fetching",
            "plan_sha256": row["plan_sha256"],
            "capture_sha256": row["capture_sha256"],
        }
