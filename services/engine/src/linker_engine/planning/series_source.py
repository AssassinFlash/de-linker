"""The immutable provenance and original temporal resolution of a power series."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from .canonical import Object, decode_object, encode
from .errors import InvalidInput
from .timezone_rules import validate_zone_name

type Origin = Literal["measured", "modelled", "template", "synthetic"]


@dataclass(frozen=True)
class SeriesSource:
    raw_sha256: str
    origin: Origin
    timezone: str
    native_max_interval_seconds: float
    details_json: bytes

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", self.raw_sha256):
            raise InvalidInput("original time-series asset hash required")
        if self.origin not in ("measured", "modelled", "template", "synthetic"):
            raise InvalidInput("time-series origin must be explicit")
        if (
            not math.isfinite(self.native_max_interval_seconds)
            or self.native_max_interval_seconds <= 0
        ):
            raise InvalidInput("native interval resolution must be positive")
        validate_zone_name(self.timezone)
        # Immutable bytes prevent later caller edits changing provenance.
        object.__setattr__(
            self, "details_json", encode(decode_object(self.details_json))
        )

    def document(self) -> Object:
        return {
            "raw_sha256": self.raw_sha256,
            "origin": self.origin,
            "timezone": self.timezone,
            "native_max_interval_seconds": self.native_max_interval_seconds,
            "details": decode_object(self.details_json),
        }
