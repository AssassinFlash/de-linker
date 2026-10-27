"""Read only profile bytes/TZif pinned by a frozen run, never the OS's latest."""

from __future__ import annotations

from .energy_inputs import MappingDocument
from .errors import VersionUnavailable
from .power_series import PowerSeries
from .profiles import read_profile
from .pv_profile import PURPOSE, frozen_reference_profile
from .pvgis_import import PvgisParseLimits
from .pvgis_profile import PvgisInterpretation, pvgis_profile
from .pvgis_request import PvgisRequest
from .pvgis_response import PvgisCapture, read_pvgis
from .storage import Blobs
from .timezone_rules import TimezoneRules


def frozen_profile(
    blobs: Blobs, raw_sha256: str, metadata_sha256: str, timezone_sha256: str | None
) -> PowerSeries:
    metadata = blobs.object(metadata_sha256)
    if (
        type(metadata.get("schema")) is not int
        or metadata.get("schema") != 1
        or metadata.get("retention") != "permanent"
    ):
        raise VersionUnavailable("unsupported pinned profile metadata")
    if metadata.get("profile_type") == PURPOSE:
        if timezone_sha256 is not None or "csv_mapping" in metadata:
            raise VersionUnavailable("mixed profile formats are not supported")
        return frozen_reference_profile(blobs, raw_sha256, metadata)
    if metadata.get("profile_type") == "pvgis_system_profile_v1":
        if timezone_sha256 is not None or "csv_mapping" in metadata:
            raise VersionUnavailable("mixed profile formats are not supported")
        request = PvgisRequest.read(metadata.get("pvgis_request"))
        capture = PvgisCapture.read(metadata.get("pvgis_capture"))
        interpretation = PvgisInterpretation.read(metadata.get("pvgis_interpretation"))
        limits = PvgisParseLimits.read(metadata.get("pvgis_parse_limits"))
        return pvgis_profile(
            read_pvgis(
                blobs.read(raw_sha256),
                request,
                capture,
                max_bytes=limits.max_bytes,
                max_rows=limits.max_rows,
            ),
            interpretation,
        )
    if (
        metadata.get("timezone_rules_sha256") != timezone_sha256
        or timezone_sha256 is None
        or "pvgis_request" in metadata
        or metadata.get("profile_type") is not None
    ):
        raise VersionUnavailable("profile has no matching pinned timezone rules")
    mapping = MappingDocument.read(metadata.get("csv_mapping")).mapping()
    rules = TimezoneRules(mapping.timezone, blobs.read(timezone_sha256))
    return read_profile(blobs.read(raw_sha256), mapping, rules)
