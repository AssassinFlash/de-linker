"""Capture IANA TZif bytes at intake; a run replays the captured rules.

Loading from the host happens only in this intake adapter. The CSV interpreter
uses ZoneInfo.from_file on immutable bytes and records their SHA-256 instead
of assuming that this machine and a future worker have identical zone tables.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import TZPATH, ZoneInfo

from .canonical import digest
from .errors import InvalidInput, VersionUnavailable


def validate_zone_name(name: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.+-]+(?:/[A-Za-z0-9_.+-]+)*", name) or any(
        part in (".", "..") for part in name.split("/")
    ):
        raise InvalidInput("a valid IANA timezone key is required")


@dataclass(frozen=True)
class TimezoneRules:
    name: str
    content: bytes

    def __post_init__(self) -> None:
        validate_zone_name(self.name)
        self.zone()

    @property
    def sha256(self) -> str:
        return digest(self.content)

    def zone(self) -> ZoneInfo:
        try:
            return ZoneInfo.from_file(io.BytesIO(self.content), key=self.name)
        except (ValueError, EOFError) as error:
            raise VersionUnavailable(
                "pinned timezone rules are not a valid TZif"
            ) from error


def load_timezone(name: str) -> TimezoneRules:
    """Trusted intake: capture the exact installed OS tzdata file or fail."""
    validate_zone_name(name)
    for root in TZPATH:
        path = Path(root) / name
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise VersionUnavailable(
                "installed timezone rules cannot be read"
            ) from error
        return TimezoneRules(name, content)
    raise VersionUnavailable("timezone rules are not installed on this host")
