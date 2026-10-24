"""A proposed topology uses Woo identities; customers supply no device facts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from .energy_inputs import Document, Nonnegative, SchemaVersion

# Interoperable JSON integer ceiling, not a physical installation limit.
type Count = Annotated[int, Field(strict=True, gt=0, le=9007199254740991)]


class EquipmentSelection(Document):
    schema_version: SchemaVersion
    inverter_product_id: Count
    battery_product_id: Count | None
    modules_per_stack: Count | None
    parallel_stacks: Count | None
    accessory_product_ids: list[Count]
    grid_phase: Literal[1, 3] | None
    operating_mode: Literal["grid_connected", "backup"]
    pv_dc_kw: Nonnegative | None
    required_usable_kwh: Nonnegative | None
    required_discharge_ac_kw: Nonnegative | None
    product_revisions: dict[str, Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]]

    @model_validator(mode="after")
    def distinct_parts(self) -> EquipmentSelection:
        if len(self.accessory_product_ids) != len(set(self.accessory_product_ids)):
            raise ValueError("accessory product identities must be unique")
        if self.inverter_product_id in self.accessory_product_ids or (
            self.battery_product_id in self.accessory_product_ids
        ):
            raise ValueError("a primary device cannot also be its accessory")
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
