"""Project wiring choices refer to real roof objects, never device limits."""

from __future__ import annotations

from typing import Annotated, Self

from pydantic import Field, model_validator

from .energy_inputs import Document, SchemaVersion
from .equipment_inputs import Count
from .geometry_documents import Identifier


class PvString(Document):
    id: Identifier
    mppt: Count
    input: Count
    module_ids: Annotated[
        list[Annotated[str, Field(min_length=1)]], Field(min_length=1)
    ]


class PvStringPlan(Document):
    schema_version: SchemaVersion
    inverter_product_id: Count
    # Absolute zero is a physical input boundary, not a location default.
    minimum_ambient_c: Annotated[float, Field(ge=-273.15, allow_inf_nan=False)] | None
    temperature_source: Annotated[str, Field(min_length=1, max_length=4096)] | None
    strings: list[PvString]

    @model_validator(mode="after")
    def unique_connections(self) -> Self:
        ids = [item.id for item in self.strings]
        ports = [(item.mppt, item.input) for item in self.strings]
        modules = [mid for item in self.strings for mid in item.module_ids]
        if any(len(rows) != len(set(rows)) for rows in (ids, ports, modules)):
            raise ValueError(
                "strings, physical inputs and assigned modules must be unique"
            )
        return self
