"""Project demand for a search; manufacturer quantities remain Woo-owned."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, ValidationError

from .backup_demand import BackupDemand
from .canonical import Object
from .energy_inputs import Document, Nonnegative, SchemaVersion, storage_only_project
from .errors import InvalidInput


def _phase(value: object) -> int:
    if type(value) is not int or value not in (1, 3):
        raise ValueError("grid phase requires integer 1 or 3")
    return value


type GridPhase = Annotated[Literal[1, 3], BeforeValidator(_phase)]

# The customer's stated project application; Woo products carry the
# manufacturer's own `pa_application` facet (`home`/`commercial`).
type Application = Literal["residential", "commercial"]


class DeclaredEquipmentRequirements(Document):
    schema_version: SchemaVersion
    grid_phase: GridPhase | None
    operating_mode: Literal["grid_connected", "backup"] | None
    # Installed-array STC nameplate rating, displayed in kWp, not AC demand.
    pv_dc_kw: Nonnegative | None
    # Sizing values are lower bounds, independent of the project's storage scope.
    # None leaves the corresponding demand unevaluated; zero is a known bound.
    required_usable_kwh: Nonnegative | None
    required_discharge_ac_kw: Nonnegative | None
    # None leaves the search unrestricted. A product whose application is
    # unknown is never excluded; only a contradicting named application is.
    application: Application | None = None

    @classmethod
    def effective(
        cls,
        setup: Object,
        *,
        inputs: Object,
        path: str,
        connection: DeclaredEquipmentRequirements | None = None,
        whole_plant: bool = False,
    ) -> Self:
        """Derive search demand without changing the customer's declarations."""
        values = {key: setup.get(key) for key in cls.model_fields}
        if connection is not None:
            values.update(
                grid_phase=connection.grid_phase,
                operating_mode=connection.operating_mode,
            )
        if storage_only_project(inputs):
            values["pv_dc_kw"] = 0
        backup = BackupDemand.from_inputs(inputs, complete=True)
        if backup is not None:
            values.update(schema_version=1, operating_mode="backup")
            if connection is None and not whole_plant:
                values["required_discharge_ac_kw"] = backup.load_kw
        try:
            return cls.model_validate(values)
        except ValidationError as error:
            fields = tuple(
                path + "." + ".".join(str(part) for part in item["loc"])
                for item in error.errors()
            )
            raise InvalidInput(
                "complete the declared equipment demand", fields=fields
            ) from error


class EquipmentRequirements(DeclaredEquipmentRequirements):
    grid_phase: GridPhase
    operating_mode: Literal["grid_connected", "backup"]

    @classmethod
    def from_inputs(cls, inputs: Object) -> EquipmentRequirements:
        prepared = cls.read(inputs.get("equipment_requirements"))
        setup = inputs.get("equipment_setup")
        if isinstance(setup, dict):
            # Earlier setups omit application; compare only authored fields.
            current = cls.effective(
                {**prepared.model_dump(mode="json"), **setup},
                inputs=inputs,
                path="equipment_setup",
            )
            for name in cls.model_fields:
                if name in setup and getattr(current, name) != getattr(prepared, name):
                    raise InvalidInput(
                        "equipment search requirements need preparation",
                        fields=(f"equipment_setup.{name}",),
                    )
        return prepared
