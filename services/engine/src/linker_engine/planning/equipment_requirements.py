"""Project demand for a search; manufacturer quantities remain Woo-owned."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator

from .canonical import Object
from .energy_inputs import Document, Nonnegative, SchemaVersion
from .errors import InvalidInput


def _phase(value: object) -> int:
    if type(value) is not int or value not in (1, 3):
        raise ValueError("grid phase requires integer 1 or 3")
    return value


type GridPhase = Annotated[Literal[1, 3], BeforeValidator(_phase)]


class EquipmentRequirements(Document):
    schema_version: SchemaVersion
    grid_phase: GridPhase
    operating_mode: Literal["grid_connected", "backup"]
    # Installed-array STC nameplate rating, displayed in kWp, not AC demand.
    pv_dc_kw: Nonnegative | None
    required_usable_kwh: Nonnegative
    required_discharge_ac_kw: Nonnegative

    @classmethod
    def from_inputs(cls, inputs: Object) -> EquipmentRequirements:
        prepared = cls.read(inputs.get("equipment_requirements"))
        setup = inputs.get("equipment_setup")
        if isinstance(setup, dict):
            current = cls.read({key: setup.get(key) for key in cls.model_fields})
            if current != prepared:
                raise InvalidInput("equipment search requirements need preparation")
        return prepared
