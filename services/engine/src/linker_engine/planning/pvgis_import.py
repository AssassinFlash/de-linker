"""Owned PVGIS intake; the server supplies acquisition and retention evidence."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .assets import Asset, Assets
from .canonical import Object, digest
from .energy_inputs import Document
from .pvgis_profile import PvgisInterpretation, pvgis_profile
from .pvgis_request import PvgisRequest
from .pvgis_response import PvgisCapture, read_pvgis
from .records import Actor


class PvgisParseLimits(Document):
    # Operational resource limits are supplied by deployment, not physics.
    max_bytes: Annotated[int, Field(strict=True, gt=0)]
    max_rows: Annotated[int, Field(strict=True, gt=0)]

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}


class PvgisImport:
    def __init__(self, assets: Assets, limits: PvgisParseLimits) -> None:
        self.assets = assets
        self.limits = limits

    def system_profile(
        self,
        actor: Actor,
        project_id: str,
        content: bytes,
        request: PvgisRequest,
        capture: PvgisCapture,
        interpretation: PvgisInterpretation,
        provenance: Object,
        *,
        key: str,
    ) -> Asset:
        self.assets.check_write(actor, project_id)
        logical: Object = {
            "schema": 1,
            "profile_type": "pvgis_system_profile_v1",
            "retention": "permanent",
            "provenance": provenance,
            "pvgis_request": request.document(),
            "pvgis_capture": capture.document(),
            "pvgis_interpretation": interpretation.document(),
        }
        previous = self.assets.receipt(
            actor,
            project_id,
            key,
            {
                "content_sha256": digest(content),
                "media_type": "application/json",
                "purpose": "pvgis_system_profile_v1",
                "metadata": logical,
            },
        )
        if previous is not None:
            return previous
        native = read_pvgis(
            content,
            request,
            capture,
            max_bytes=self.limits.max_bytes,
            max_rows=self.limits.max_rows,
        )
        profile = pvgis_profile(native, interpretation)
        return self.assets.add(
            actor,
            project_id,
            content,
            "application/json",
            "pvgis_system_profile_v1",
            {
                **logical,
                "pvgis_parse_limits": self.limits.document(),
                "interpretation": {
                    "start_utc": profile.intervals[0].start.isoformat(),
                    "end_utc": profile.intervals[-1].end.isoformat(),
                    "interval_count": len(profile.intervals),
                    "energy_kwh": profile.total_kwh,
                    "measurement": profile.measurement,
                    "origin": profile.source.origin,
                    "native_max_interval_seconds": 3600,
                    "native_value_semantics": native.value_semantics,
                    "reconstructed_means": profile.reconstructed_means,
                    "transformations": [
                        item.document() for item in profile.transformations
                    ],
                },
            },
            key=key,
            logical_metadata=logical,
        )
