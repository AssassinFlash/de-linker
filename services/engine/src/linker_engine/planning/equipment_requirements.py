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

# The customer's stated project application; Woo products carry the
# manufacturer's own `pa_application` facet (`home`/`commercial`).
type Application = Literal["residential", "commercial"]


# Declarations the requirements own and a setup cannot carry: the selection
# schema has no such property, so comparing them would always mismatch.
_REQUIREMENTS_ONLY = frozenset({"application"})


class EquipmentRequirements(Document):
    schema_version: SchemaVersion
    grid_phase: GridPhase
    operating_mode: Literal["grid_connected", "backup"]
    # Installed-array STC nameplate rating, displayed in kWp, not AC demand.
    pv_dc_kw: Nonnegative | None
    required_usable_kwh: Nonnegative
    required_discharge_ac_kw: Nonnegative
    # None leaves the search unrestricted. A product whose application is
    # unknown is never excluded; only a contradicting named application is.
    application: Application | None = None

    @classmethod
    def from_inputs(cls, inputs: Object) -> EquipmentRequirements:
        prepared = cls.read(inputs.get("equipment_requirements"))
        setup = inputs.get("equipment_setup")
        if isinstance(setup, dict):
            # A setup cannot restate `application`: it is a declaration about the
            # project, held by the requirements, and the selection schema has no
            # such property. Compare only the fields both documents own, and
            # compare their values rather than two populated models — a model
            # read from the setup would fill the absent `application` with its
            # default and differ from every prepared requirement.
            for name in cls.model_fields:
                if name in _REQUIREMENTS_ONLY or name not in setup:
                    continue
                if setup[name] != getattr(prepared, name):
                    raise InvalidInput(
                        "equipment search requirements need preparation",
                        fields=(f"equipment_setup.{name}",),
                    )
        return prepared
