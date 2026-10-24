"""Bounded exact intervals from an owned frozen run; no resampling or rerun."""

from __future__ import annotations

import math

from .access import positive_integer
from .canonical import Json, Object
from .errors import InvalidInput, NotFound, VersionUnavailable
from .records import Actor
from .workspace import Workspace


class TraceWindow:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def page(self, actor: Actor, run_id: str, *, offset: int, page_size: int) -> Object:
        run = self.workspace.run(actor, run_id)
        positive_integer(page_size, "trace page size")
        if type(offset) is not int or offset < 0:
            raise InvalidInput("nonnegative trace page offset required")
        result = run.result
        trace_hash = result.get("trace_sha256") if result else None
        if not result or not isinstance(trace_hash, str):
            raise NotFound("trace not found")
        trace = self.workspace.blobs.object(trace_hash)
        flows = trace.get("flows")
        if (
            result.get("kind") != "single_ac_energy_replay_v1"
            or trace.get("kind") != result["kind"]
            or trace.get("manifest_sha256") != run.manifest_sha256
            or not isinstance(flows, list)
            or len(flows) != result.get("interval_count")
        ):
            raise VersionUnavailable("trace does not match its saved calculation")
        end = min(offset + page_size, len(flows))
        rows: list[Json] = []
        for index in range(offset, end):
            flow = flows[index]
            if not isinstance(flow, dict):
                raise VersionUnavailable("trace interval unavailable")
            frame, after = flow.get("frame"), flow.get("after")
            interval = frame.get("interval") if isinstance(frame, dict) else None
            if not isinstance(interval, dict) or not isinstance(after, dict):
                raise VersionUnavailable("trace interval axes unavailable")
            buckets = [
                after.get(name)
                for name in ("pv_kwh", "grid_kwh", "initial_unknown_kwh")
            ]
            if any(type(value) not in (int, float) for value in buckets):
                raise VersionUnavailable("stored energy origins unavailable")
            assert isinstance(frame, dict)
            rows.append(
                {
                    "interval_index": index,
                    "start_utc": interval["start_utc"],
                    "end_utc": interval["end_utc"],
                    "load_kw": frame["load_kw"],
                    "pv_kw": flow["pv_available_kw"],
                    "charge_kw": flow["charge_kw"],
                    "discharge_kw": flow["discharge_kw"],
                    "import_kw": flow["import_kw"],
                    "export_kw": flow["export_kw"],
                    "stored_kwh": math.fsum(
                        float(value)
                        for value in buckets
                        if isinstance(value, (int, float))
                    ),
                }
            )
        return {
            "schema_version": 1,
            "run_id": run.id,
            "manifest_sha256": run.manifest_sha256,
            "trace_sha256": trace_hash,
            "interval_count": len(flows),
            "offset": offset,
            "rows": rows,
            "next_offset": end if end < len(flows) else None,
        }
