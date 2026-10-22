"""Read only profile bytes/TZif pinned by a frozen run, never the OS's latest."""

from __future__ import annotations

from .energy_inputs import MappingDocument
from .errors import VersionUnavailable
from .power_series import PowerSeries
from .profiles import read_profile
from .storage import Blobs
from .timezone_rules import TimezoneRules


def frozen_profile(
    blobs: Blobs, raw_sha256: str, metadata_sha256: str, timezone_sha256: str
) -> PowerSeries:
    metadata = blobs.object(metadata_sha256)
    if (
        type(metadata.get("schema")) is not int
        or metadata.get("schema") != 1
        or metadata.get("timezone_rules_sha256") != timezone_sha256
        or metadata.get("retention") != "permanent"
    ):
        raise VersionUnavailable("unsupported pinned profile metadata")
    mapping = MappingDocument.read(metadata.get("csv_mapping")).mapping()
    rules = TimezoneRules(mapping.timezone, blobs.read(timezone_sha256))
    return read_profile(blobs.read(raw_sha256), mapping, rules)
