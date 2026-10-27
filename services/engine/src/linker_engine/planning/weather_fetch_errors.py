"""Named provider failures; private response bodies never become user errors."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Literal, cast

from .canonical import Object
from .errors import InvalidInput, PlanningError
from .worker import RetryableExecution


class WeatherProviderUnavailable(RetryableExecution):
    code = "weather_provider_unavailable"


class WeatherProviderRejected(PlanningError):
    code = "weather_provider_rejected"


class WeatherResponseInvalid(InvalidInput):
    code = "weather_response_invalid"


type SourceQualityReason = Literal["negative_wind", "negative_irradiance"]
type SourceQualityField = Literal["WS10m", "G(h)", "Gb(n)", "Gd(h)"]


class WeatherSourceQualityInvalid(WeatherResponseInvalid):
    """Only finite physical values and a validated source instant are public."""

    code = "weather_source_quality_invalid"

    def __init__(
        self,
        reason: SourceQualityReason,
        field: SourceQualityField,
        row_index: int,
        source_timestamp_utc: str,
        value: float,
    ) -> None:
        if (
            (reason == "negative_wind" and field != "WS10m")
            or (
                reason == "negative_irradiance"
                and field not in {"G(h)", "Gb(n)", "Gd(h)"}
            )
            or reason not in {"negative_wind", "negative_irradiance"}
            or type(row_index) is not int
            or row_index < 0
            or type(value) not in (int, float)
            or not math.isfinite(value)
            or value >= 0
            or not isinstance(source_timestamp_utc, str)
        ):
            raise ValueError("invalid public weather source-quality detail")
        instant = datetime.fromisoformat(source_timestamp_utc)
        if (
            instant.utcoffset() != timedelta(0)
            or instant.isoformat() != source_timestamp_utc
        ):
            raise ValueError(
                "weather source-quality detail requires a canonical UTC instant"
            )
        super().__init__(
            "official weather response failed the physical source-quality check"
        )
        self.public_details: Object = {
            "reason": reason,
            "field": field,
            "row_index": row_index,
            "source_timestamp_utc": source_timestamp_utc,
            "value": value,
        }

    @classmethod
    def from_details(cls, details: Object) -> WeatherSourceQualityInvalid:
        if set(details) != {
            "reason",
            "field",
            "row_index",
            "source_timestamp_utc",
            "value",
        }:
            raise ValueError("unexpected public weather source-quality detail")
        return cls(
            cast(SourceQualityReason, details["reason"]),
            cast(SourceQualityField, details["field"]),
            cast(int, details["row_index"]),
            cast(str, details["source_timestamp_utc"]),
            cast(float, details["value"]),
        )


class WeatherResponseTooLarge(InvalidInput):
    code = "weather_response_too_large"


class WeatherRemoteFailed(PlanningError):
    code = "weather_remote_failed"


class WeatherPollingLimit(PlanningError):
    code = "weather_polling_limit"
