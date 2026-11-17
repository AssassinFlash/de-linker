"""A proposed topology uses Woo identities; customers supply no device facts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .energy_inputs import Document, Nonnegative, SchemaVersion
from .equipment_requirements import GridPhase

# Interoperable JSON integer ceiling, not a physical installation limit.
type Count = Annotated[int, Field(strict=True, gt=0, le=9007199254740991)]

# Procurement intent per primary device: a new installation, a retained
# existing device, or a replacement purchase. Absent means new.
type PartUse = Literal["new", "retain", "replace"]


class EquipmentUse(Document):
    inverter: PartUse
    battery: PartUse


class EquipmentSelection(Document):
    schema_version: SchemaVersion
    inverter_product_id: Count
    battery_product_id: Count | None
    modules_per_stack: Count | None
    parallel_stacks: Count | None
    accessory_product_ids: list[Count]
    grid_phase: GridPhase | None
    operating_mode: Literal["grid_connected", "backup"]
    # Installed-array STC nameplate rating, displayed in kWp, not AC demand.
    pv_dc_kw: Nonnegative | None
    required_usable_kwh: Nonnegative | None
    required_discharge_ac_kw: Nonnegative | None
    product_revisions: dict[str, Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]]
    # Procurement intent: retained and replaced devices keep the product
    # identity declared above and join physics and compatibility checks; only
    # the purchase list differs. Omit an unanswered field so retained
    # projects/candidates keep their original canonical representation.
    equipment_use: EquipmentUse | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def distinct_parts(self) -> EquipmentSelection:
        if len(self.accessory_product_ids) != len(set(self.accessory_product_ids)):
            raise ValueError("accessory product identities must be unique")
        if self.inverter_product_id in self.accessory_product_ids or (
            self.battery_product_id in self.accessory_product_ids
        ):
            raise ValueError("a primary device cannot also be its accessory")
        if (
            self.equipment_use is not None
            and self.battery_product_id is None
            and self.equipment_use.battery != "new"
        ):
            raise ValueError("a retained or replaced battery needs its product")
        selected = {self.inverter_product_id, *self.accessory_product_ids}
        if self.battery_product_id is not None:
            selected.add(self.battery_product_id)
        if set(self.product_revisions) != {str(pid) for pid in selected}:
            raise ValueError("each selected product needs its current Woo revision")
        if (
            self.modules_per_stack is not None
            and self.parallel_stacks is not None
            and self.modules_per_stack * self.parallel_stacks > 9007199254740991
        ):
            raise ValueError("module count exceeds interoperable integers")
        return self
