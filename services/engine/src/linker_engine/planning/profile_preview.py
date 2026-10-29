"""Owned profile interpretation and paged intervals, independent of run fitness."""

from __future__ import annotations

from .access import positive_integer
from .assets import Assets
from .canonical import Json, Object
from .errors import InvalidInput, VersionUnavailable
from .frozen_profiles import frozen_profile
from .geometric_pv_inputs import PROFILE_PURPOSE as GEOMETRIC_PV_PURPOSE
from .interval import microseconds
from .pv_profile import PURPOSE
from .pv_profile_artifacts import prepared_profile
from .records import Actor
from .wire_numbers import check_wire_numbers


class ProfilePreview:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets

    def page(
        self,
        actor: Actor,
        project_id: str,
        asset_id: str,
        *,
        offset: int,
        page_size: int,
    ) -> Object:
        # Ownership precedes CSV/TZif parsing or any source-dependent response.
        # The native HTTP adapter adds its declared response page cap.
        asset = self.assets.get(actor, project_id, asset_id)
        positive_integer(page_size, "profile page size")
        if type(offset) is not int or offset < 0:
            raise InvalidInput("nonnegative profile page offset required")
        expected_type = {
            "csv_profile_v1": None,
            "pvgis_system_profile_v1": "pvgis_system_profile_v1",
            PURPOSE: PURPOSE,
            GEOMETRIC_PV_PURPOSE: GEOMETRIC_PV_PURPOSE,
            "pvgis_roof_ac_reference_profile_v1": "pvgis_roof_ac_reference_profile_v1",
        }
        if (
            asset.purpose not in expected_type
            or asset.metadata.get("profile_type") != expected_type[asset.purpose]
        ):
            raise VersionUnavailable("unsupported profile asset purpose or metadata")
        timezone = asset.metadata.get("timezone_rules_sha256")
        if timezone is not None and not isinstance(timezone, str):
            raise VersionUnavailable("invalid pinned profile timezone reference")
        if asset.purpose == PURPOSE:
            series = prepared_profile(
                self.assets.workspace.blobs, asset.content_sha256, asset.metadata
            )
        else:
            series = frozen_profile(
                self.assets.workspace.blobs,
                asset.content_sha256,
                asset.metadata_sha256,
                timezone,
            )
        covered_us = sum(interval.duration_us for interval in series.intervals)
        span_us = microseconds(series.intervals[-1].end - series.intervals[0].start)
        gaps: list[Json] = []
        gap_count = 0
        for previous, current in zip(
            series.intervals, series.intervals[1:], strict=False
        ):
            if current.start > previous.end:
                gap_count += 1
                if len(gaps) < page_size:
                    gaps.append(
                        {
                            "start_utc": previous.end.isoformat(),
                            "end_utc": current.start.isoformat(),
                        }
                    )
        end = min(offset + page_size, len(series.intervals))
        rows: list[Json] = [
            {
                "interval_index": index,
                "start_utc": series.intervals[index].start.isoformat(),
                "end_utc": series.intervals[index].end.isoformat(),
                "interval_mean_kw": series.values_kw[index],
            }
            for index in range(offset, end)
        ]
        result: Object = {
            "schema_version": 1,
            "project_id": project_id,
            "asset_id": asset.id,
            "content_sha256": asset.content_sha256,
            "metadata_sha256": asset.metadata_sha256,
            "evaluation_scope": "profile_interpretation",
            "measurement": series.measurement,
            "source": series.source.document(),
            "transformations": [item.document() for item in series.transformations],
            "summary": {
                "start_utc": series.intervals[0].start.isoformat(),
                "end_utc": series.intervals[-1].end.isoformat(),
                "interval_count": len(series.intervals),
                # datetime uses exact integer microseconds: 1e6 per SI second.
                "covered_seconds": covered_us / 1_000_000,
                "span_seconds": span_us / 1_000_000,
                "gap_seconds": (span_us - covered_us) / 1_000_000,
                "gap_count": gap_count,
                "energy_kwh": series.total_kwh,
                "min_interval_mean_kw": min(series.values_kw),
                "max_interval_mean_kw": max(series.values_kw),
                "native_max_interval_seconds": series.source.native_max_interval_seconds,
                "effective_max_interval_seconds": series.effective_max_interval_seconds,
                "reconstructed_means": series.reconstructed_means,
            },
            "first_gaps": gaps,
            "gaps_truncated": gap_count > len(gaps),
            "offset": offset,
            "rows": rows,
            "next_offset": end if end < len(series.intervals) else None,
        }
        try:
            check_wire_numbers(result)
        except ValueError as error:
            raise InvalidInput(
                "profile preview exceeds the interoperable numeric range"
            ) from error
        return result
