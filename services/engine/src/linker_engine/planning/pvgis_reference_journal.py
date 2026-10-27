"""Fenced private acquisition state, separate from a usable project asset.

The existing job output pointer retains bounded progress across leases. Only
Jobs.complete publishes a run result/project asset; pending or rejected originals
are never exposed as a prepared profile.
"""

import math
import sqlite3
from typing import cast

from .canonical import Object, encode
from .dependencies import verify_dependencies
from .errors import Conflict, InvalidInput, VersionUnavailable
from .frozen_run import frozen_manifest
from .jobs import Jobs
from .pvgis_reference_download import ReferenceCapture
from .pvgis_reference_plan import PvgisReferencePlan
from .pvgis_response import PvgisCapture, read_pvgis
from .records import Lease
from .weather_fetch_errors import WeatherResponseInvalid, WeatherResponseTooLarge
from .workspace import Workspace


class PvgisReferenceJournal:
    kind = "pvgis_roof_reference_acquisition_v1"

    def __init__(
        self, workspace: Workspace, lease: Lease, plan: PvgisReferencePlan
    ) -> None:
        self.workspace, self.lease, self.plan = workspace, lease, plan
        self.jobs = Jobs(workspace)
        self.plan_sha = workspace.blobs.put_object(plan.document())
        manifest_sha = lease.request.get("manifest_sha256")
        if lease.kind != "evaluate" or not isinstance(manifest_sha, str):
            raise InvalidInput("frozen roof reference lease required")
        self.manifest_sha = manifest_sha
        manifest = frozen_manifest(workspace, lease, manifest_sha)
        context = manifest.get("context")
        assets = context.get("assets") if isinstance(context, dict) else None
        if (
            not isinstance(assets, dict)
            or assets.get("pvgis_reference.plan") != self.plan_sha
        ):
            raise VersionUnavailable("roof acquisition plan was not frozen by this run")

    def _read(self, output: object) -> Object:
        if not isinstance(output, str):
            raise VersionUnavailable("roof reference acquisition state missing")
        state = self.workspace.blobs.object(output)
        started, deadline = state.get("started_at"), state.get("deadline_at")
        if (
            state.get("schema_version") != 1
            or state.get("kind") != self.kind
            or state.get("run_id") != self.lease.run_id
            or state.get("manifest_sha256") != self.manifest_sha
            or state.get("plan_sha256") != self.plan_sha
            or type(started) not in (int, float)
            or type(deadline) not in (int, float)
            or not math.isfinite(cast(float, started))
            or not math.isfinite(cast(float, deadline))
            or deadline != cast(float, started) + self.plan.limits.max_elapsed_seconds
            or not isinstance(state.get("arrays"), dict)
            or type(state.get("consumed_bytes")) is not int
        ):
            raise VersionUnavailable("roof reference acquisition binding changed")
        rows = cast(Object, state["arrays"])
        expected: Object = {"reference_plan": self.plan_sha}
        size = 0
        for key, value in rows.items():
            if key not in {
                str(i) for i in range(len(self.plan.arrays))
            } or not isinstance(value, dict):
                raise VersionUnavailable("roof reference acquisition array changed")
            raw, capture = value.get("raw_sha256"), value.get("capture_sha256")
            if (
                not isinstance(raw, str)
                or not isinstance(capture, str)
                or type(value.get("validated")) is not bool
            ):
                raise VersionUnavailable("roof reference acquisition capture missing")
            size += len(self.workspace.blobs.read(raw))
            expected[f"array.{key}.original"] = raw
            expected[f"array.{key}.capture"] = capture
        if (
            state.get("dependencies") != expected
            or size != state["consumed_bytes"]
            or size > self.plan.limits.max_response_bytes
        ):
            raise VersionUnavailable("roof reference cumulative byte budget changed")
        verify_dependencies(self.workspace.blobs, state)
        return state

    def begin(self) -> Object:
        with self.workspace.database.transaction() as db:
            now = self.workspace.clock()
            row = self.jobs.require_active(db, self.lease, now)
            if row["output_sha256"] is not None:
                return self._read(row["output_sha256"])
            deadline = now + self.plan.limits.max_elapsed_seconds
            if not math.isfinite(deadline) or deadline <= now:
                raise InvalidInput("roof reference deadline is not representable")
            state: Object = {
                "schema_version": 1,
                "kind": self.kind,
                "run_id": self.lease.run_id,
                "manifest_sha256": self.manifest_sha,
                "plan_sha256": self.plan_sha,
                "started_at": now,
                "deadline_at": deadline,
                "consumed_bytes": 0,
                "arrays": {},
                "dependencies": {"reference_plan": self.plan_sha},
            }
            self._write(db, state)
            return state

    def _write(self, db: sqlite3.Connection, state: Object) -> None:
        content = self.workspace.blobs.put_object(state)
        db.execute(
            "UPDATE jobs SET output_sha256=? WHERE id=?", (content, self.lease.id)
        )

    def current(self) -> Object:
        with self.workspace.database.read() as db:
            row = self.jobs.require_active(db, self.lease, self.workspace.clock())
            return self._read(row["output_sha256"])

    def captured(self, index: int) -> ReferenceCapture | None:
        state = self.current()
        row = cast(Object, state["arrays"]).get(str(index))
        if row is None:
            return None
        assert isinstance(row, dict)
        if row.get("failure") is not None:
            raise WeatherResponseInvalid("retained PVGIS original failed validation")
        return ReferenceCapture(
            self.workspace.blobs.read(str(row["raw_sha256"])),
            PvgisCapture.read(self.workspace.blobs.object(str(row["capture_sha256"]))),
        )

    def retain(self, index: int, source: ReferenceCapture) -> None:
        if not 0 <= index < len(self.plan.arrays):
            raise InvalidInput("roof reference array outside its frozen plan")
        raw_sha = self.workspace.blobs.put(source.content)
        capture_sha = self.workspace.blobs.put_object(source.capture.document())
        if (
            not source.content
            or len(encode(source.capture.document()))
            > self.plan.limits.max_metadata_bytes
        ):
            raise WeatherResponseTooLarge(
                "roof reference capture exceeds frozen budget"
            )
        with self.workspace.database.transaction() as db:
            row = self.jobs.require_active(db, self.lease, self.workspace.clock())
            state = self._read(row["output_sha256"])
            arrays = cast(Object, state["arrays"])
            previous = arrays.get(str(index))
            if previous is not None:
                if not isinstance(previous, dict) or (
                    previous.get("raw_sha256"),
                    previous.get("capture_sha256"),
                ) != (raw_sha, capture_sha):
                    raise Conflict(
                        "retained roof reference original cannot be replaced"
                    )
                return
            total = cast(int, state["consumed_bytes"]) + len(source.content)
            if total > self.plan.limits.max_response_bytes:
                raise WeatherResponseTooLarge(
                    "roof reference originals exceed fixed byte budget"
                )
            arrays[str(index)] = {
                "raw_sha256": raw_sha,
                "capture_sha256": capture_sha,
                "validated": False,
                "failure": None,
            }
            state["consumed_bytes"] = total
            dependencies = cast(Object, state["dependencies"])
            dependencies[f"array.{index}.original"] = raw_sha
            dependencies[f"array.{index}.capture"] = capture_sha
            self._write(db, state)

    def validate(self, index: int, source: ReferenceCapture) -> None:
        row = cast(Object, self.current()["arrays"]).get(str(index))
        if not isinstance(row, dict):
            raise VersionUnavailable("roof reference original was not retained")
        if row.get("validated") is True:
            return
        failure: str | None = None
        try:
            if (
                source.capture.capture_basis != "official_jrc_https_get_original_v1"
                or source.capture.source_identifiers
                != {"provider": "EC_JRC_PVGIS", "api_version": "5.3"}
            ):
                raise InvalidInput("managed capture identity required")
            read_pvgis(
                source.content,
                self.plan.arrays[index].request,
                source.capture,
                max_bytes=self.plan.limits.max_response_bytes,
                max_rows=self.plan.limits.max_weather_rows,
            )
        except InvalidInput:
            failure = "response_validation_failed"
        with self.workspace.database.transaction() as db:
            current = self.jobs.require_active(db, self.lease, self.workspace.clock())
            state = self._read(current["output_sha256"])
            item = cast(Object, cast(Object, state["arrays"])[str(index)])
            if (item["raw_sha256"], item["capture_sha256"]) != (
                row["raw_sha256"],
                row["capture_sha256"],
            ):
                raise Conflict("roof reference original changed during validation")
            item.update(validated=failure is None, failure=failure)
            self._write(db, state)
        if failure:
            raise WeatherResponseInvalid("retained PVGIS original failed validation")
