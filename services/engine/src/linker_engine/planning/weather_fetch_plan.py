"""One server-owned Apify/PVGIS request and explicit operational budgets.

Provider facts and pinned schema: 2026-10-24-pv-managed-intake/FINDINGS.md.
Counts of one constrain this operation to its single official weather URL;
they are application resource policy, not weather-accuracy thresholds.
"""

from __future__ import annotations

import calendar
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Json, Object, encode
from .energy_inputs import Document, SchemaVersion
from .errors import VersionUnavailable
from .pvgis_tmy_request import PvgisTmyInterpretation, PvgisTmyRequest

ACTOR_ID = "aYG0l9s7dbB7j3gbS"
BUILD_NUMBER = "0.3.101"
BUILD_ID = "bsZdc9Cal4wAwV0VW"

type PositiveInteger = Annotated[int, Field(strict=True, gt=0)]
type PositiveNumber = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class WeatherFetchLimits(Document):
    max_response_bytes: PositiveInteger
    max_metadata_bytes: PositiveInteger
    max_weather_rows: PositiveInteger
    connect_timeout_seconds: PositiveNumber
    read_timeout_seconds: PositiveNumber
    max_elapsed_seconds: PositiveNumber
    poll_seconds: PositiveNumber
    max_polls: PositiveInteger
    actor_timeout_seconds: PositiveInteger
    actor_memory_mb: Annotated[int, Field(strict=True, ge=128)]
    max_total_charge_usd: PositiveNumber
    # Pinned Actor schema bounds, not scientific or site limits.
    request_timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=600)]
    request_retries: Annotated[int, Field(strict=True, ge=0, le=20)]
    minimum_download_kb_per_second: PositiveInteger

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.actor_memory_mb & (self.actor_memory_mb - 1):
            raise ValueError("Actor memory must be a power of two")
        if self.request_timeout_seconds > self.actor_timeout_seconds:
            raise ValueError("crawler request timeout exceeds Actor timeout")
        if self.max_metadata_bytes > self.max_response_bytes:
            raise ValueError("metadata response budget exceeds weather response budget")
        if self.poll_seconds > self.max_elapsed_seconds:
            raise ValueError("poll interval exceeds the overall acquisition deadline")
        return self


class WeatherFetchPlan(Document):
    schema_version: SchemaVersion
    kind: Literal["pvgis_tmy_apify_acquisition_v1"]
    request: PvgisTmyRequest
    interpretation: PvgisTmyInterpretation
    limits: WeatherFetchLimits

    @model_validator(mode="after")
    def nonleap_axis(self) -> Self:
        if calendar.isleap(self.interpretation.synthetic_energy_year):
            raise ValueError("TMY reconstruction requires a non-leap scenario year")
        return self

    def actor_input(self) -> Object:
        return {
            "startUrls": [{"url": self.request.url}],
            "crawlerType": "cheerio",
            "maxCrawlDepth": 0,
            "maxCrawlPages": 1,
            "maxResults": 1,
            "saveMarkdown": True,
            "saveText": True,
            "saveHtml": True,
            "saveContentTypes": "application/json",
            "htmlTransformer": "none",
            "respectRobotsTxtFile": False,
            "maxConcurrency": 1,
            "requestTimeoutSecs": self.limits.request_timeout_seconds,
            "maxRequestRetries": self.limits.request_retries,
            "minFileDownloadSpeedKBps": self.limits.minimum_download_kb_per_second,
            "customHttpHeaders": {"Accept": "application/json"},
        }

    def document(self) -> Object:
        return {
            **self.model_dump(mode="json"),
            "provider": {
                "actor_id": ACTOR_ID,
                "build_number": BUILD_NUMBER,
                "build_id": BUILD_ID,
                "input": self.actor_input(),
            },
        }

    @classmethod
    def from_document(cls, value: Json) -> WeatherFetchPlan:
        if not isinstance(value, dict):
            raise VersionUnavailable("pinned weather acquisition plan required")
        plan = cls.read(
            {name: item for name, item in value.items() if name != "provider"}
        )
        if encode(value) != encode(plan.document()):
            raise VersionUnavailable(
                "weather acquisition provider differs from its plan"
            )
        return plan
