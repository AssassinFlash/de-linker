"""Validate actual provider bytes and retain their native temporal meaning.

The native SARAH observations deliberately have no interval-energy property.
The generic response label 'hourly averages' is not authoritative for SARAH:
JRC's timestamp method and the selected radiation database take precedence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .access import positive_integer
from .canonical import Object, decode_object, digest, encode
from .energy_inputs import Document, Identifier, SchemaVersion
from .errors import InvalidInput
from .interval import utc
from .pvgis_document import number as _number
from .pvgis_document import read_object
from .pvgis_metadata import at, check_metadata
from .pvgis_request import PvgisRequest


class PvgisCapture(Document):
    schema_version: SchemaVersion
    requested_url: Identifier
    loaded_url: Identifier
    status: Annotated[int, Field(strict=True, ge=100, le=599)]
    content_type: Identifier
    received_at_utc: str
    capture_basis: Identifier
    source_identifiers: dict[str, str]

    @model_validator(mode="after")
    def explicit_instant(self) -> PvgisCapture:
        # A capture time is provenance, never the model's simulated weather year.
        utc(datetime.fromisoformat(self.received_at_utc))
        return self

    def document(self) -> Object:
        return {**self.model_dump(mode="json")}


@dataclass(frozen=True)
class PvgisHour:
    timestamp: datetime
    power_w: float
    radiation_reconstructed: bool


@dataclass(frozen=True)
class PvgisSeries:
    raw_sha256: str
    request: PvgisRequest
    capture_json: bytes
    hours: tuple[PvgisHour, ...]
    provider_metadata_json: bytes
    value_semantics: Literal["centered_hourly_mean", "instantaneous_sample"]

    def source_document(self) -> Object:
        return {
            "adapter": "pvgis_5_3_fixed_plane_system_output_v1",
            "request": self.request.document(),
            "capture": decode_object(self.capture_json),
            "raw_sha256": self.raw_sha256,
            "native_value_semantics": self.value_semantics,
            "native_unit": "W",
            "output_boundary": "provider_modelled_system_output_including_system_loss",
            "losses": [
                {
                    "stage": "pvgis_system_model",
                    "system_loss_percent": self.request.system_loss_percent,
                    "already_applied": True,
                    "basis": "explicit_request_and_verified_provider_echo",
                }
            ],
            "radiation_reconstructed_rows": sum(
                item.radiation_reconstructed for item in self.hours
            ),
            "not_modelled": [
                "specific_module_and_inverter_electrical_release",
                "shared_inverter_and_hybrid_port_constraints",
                "near_field_and_inter_row_shading",
                "site_meter_export_curtailment_and_storage_dispatch",
            ],
        }


def read_pvgis(
    content: bytes,
    request: PvgisRequest,
    capture: PvgisCapture,
    *,
    max_bytes: int,
    max_rows: int,
) -> PvgisSeries:
    positive_integer(max_bytes, "PVGIS response byte limit")
    positive_integer(max_rows, "PVGIS response row limit")
    if not content or len(content) > max_bytes:
        raise InvalidInput("PVGIS response is empty or exceeds the configured limit")
    if (
        capture.status != 200
        or capture.content_type.split(";", 1)[0].strip().lower() != "application/json"
        or not request.matches_url(capture.requested_url)
        or not request.matches_url(capture.loaded_url)
    ):
        # A real 200 text/html 'Request Rejected' was captured in research.
        # It must not become zero PV, valid JSON, or a successful source asset.
        raise InvalidInput("PVGIS capture is not the requested JSON response")
    document = read_object(content)
    check_metadata(document, request)
    rows = at(document, "outputs", "hourly")
    expected_rows = (request.end - request.start).days * 24
    if not isinstance(rows, list) or len(rows) > max_rows or len(rows) != expected_rows:
        raise InvalidInput("complete requested PVGIS years are required")
    hours: list[PvgisHour] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise InvalidInput("PVGIS hourly row must be an object")
        text = row.get("time")
        if not isinstance(text, str) or not re.fullmatch(r"[0-9]{8}:[0-9]{4}", text):
            raise InvalidInput("PVGIS UTC timestamp required")
        try:
            timestamp = datetime.strptime(text, "%Y%m%d:%H%M").replace(tzinfo=UTC)
        except ValueError as error:
            raise InvalidInput("invalid PVGIS UTC timestamp") from error
        containing_hour = timestamp.replace(minute=0)
        if containing_hour != request.start + timedelta(hours=index):
            raise InvalidInput("PVGIS hours are missing, duplicated or out of order")
        if request.radiation_database == "PVGIS-ERA5" and timestamp.minute != 30:
            raise InvalidInput("ERA5 must use the verified centered-hour timestamp")
        power_w, flag = _number(row, "P"), _number(row, "Int")
        if power_w < 0 or flag not in (0, 1):
            raise InvalidInput("invalid PVGIS power or radiation reconstruction flag")
        hours.append(PvgisHour(timestamp, power_w, flag == 1))
    return PvgisSeries(
        digest(content),
        request,
        encode(capture.document()),
        tuple(hours),
        encode({"inputs": document["inputs"], "meta": document["meta"]}),
        "centered_hourly_mean"
        if request.radiation_database == "PVGIS-ERA5"
        else "instantaneous_sample",
    )
