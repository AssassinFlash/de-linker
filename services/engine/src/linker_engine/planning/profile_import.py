"""Validate real CSV once, preserving raw bytes, mapping and exact TZif rules."""

from __future__ import annotations

from collections.abc import Callable

from .assets import Asset, Assets
from .canonical import Object, digest
from .csv_mapping import CsvMapping
from .profiles import read_profile
from .records import Actor
from .timezone_rules import TimezoneRules, load_timezone


class ProfileImport:
    def __init__(
        self,
        assets: Assets,
        *,
        timezone_loader: Callable[[str], TimezoneRules] = load_timezone,
    ) -> None:
        self.assets = assets
        self.timezone_loader = timezone_loader

    def csv(
        self,
        actor: Actor,
        project_id: str,
        content: bytes,
        mapping: CsvMapping,
        provenance: Object,
        *,
        key: str,
    ) -> Asset:
        # Ownership precedes parsing/auxiliary blob writes. Assets.add repeats
        # this under its transaction in case ownership changed meanwhile.
        self.assets.check_write(actor, project_id)
        logical: Object = {
            "schema": 1,
            "retention": "permanent",
            "provenance": provenance,
            "csv_mapping": mapping.document(),
        }
        previous = self.assets.receipt(
            actor,
            project_id,
            key,
            {
                "content_sha256": digest(content),
                "media_type": "text/csv; charset=utf-8",
                "purpose": "csv_profile_v1",
                "metadata": logical,
            },
        )
        if previous is not None:
            return previous
        rules = self.timezone_loader(mapping.timezone)
        series = read_profile(content, mapping, rules)
        rules_hash = self.assets.workspace.blobs.put(rules.content)
        return self.assets.add(
            actor,
            project_id,
            content,
            "text/csv; charset=utf-8",
            "csv_profile_v1",
            {
                "schema": 1,
                "retention": "permanent",
                "provenance": provenance,
                "csv_mapping": mapping.document(),
                "timezone_rules_sha256": rules_hash,
                "dependencies": {"timezone_rules": rules_hash},
                "interpretation": {
                    "start_utc": series.intervals[0].start.isoformat(),
                    "end_utc": series.intervals[-1].end.isoformat(),
                    "interval_count": len(series.intervals),
                    "energy_kwh": series.total_kwh,
                    "native_max_interval_seconds": series.source.native_max_interval_seconds,
                    "measurement": series.measurement,
                    "origin": series.source.origin,
                },
            },
            key=key,
            logical_metadata=logical,
        )
