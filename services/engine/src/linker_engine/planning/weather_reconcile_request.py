"""Private recovery choices refer to an existing issued acquisition only."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .apify_run import ProviderId
from .canonical import Object
from .energy_inputs import Document, SchemaVersion

type WeatherAction = Literal["acknowledge", "observe", "capture", "stop"]
type ContentHash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class WeatherReconcileRequest(Document):
    schema_version: SchemaVersion
    kind: Literal["reconcile_weather_v1"]
    manifest_sha256: ContentHash
    weather_plan_sha256: ContentHash
    action: WeatherAction
    provider_run_id: ProviderId | None

    @model_validator(mode="after")
    def known_id(self) -> Self:
        if (self.action == "acknowledge") != (self.provider_run_id is not None):
            raise ValueError("only acknowledgement requires a supplied provider ID")
        return self

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}
