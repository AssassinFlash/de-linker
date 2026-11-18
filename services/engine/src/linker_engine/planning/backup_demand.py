"""Customer-authored constant backup load; energy is AC demand before losses."""

from __future__ import annotations

import math
from typing import Annotated

from pydantic import Field

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput

type PositiveDemand = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class BackupDemand(Document):
    schema_version: SchemaVersion
    load_kw: PositiveDemand | None
    duration_hours: PositiveDemand | None

    @classmethod
    def from_inputs(
        cls, inputs: Object, *, complete: bool = False
    ) -> BackupDemand | None:
        if "backup_demand" not in inputs:
            return None
        demand = cls.read(inputs["backup_demand"])
        if complete:
            missing = [
                "backup_demand." + key
                for key in ("load_kw", "duration_hours")
                if getattr(demand, key) is None
            ]
            if missing:
                raise InvalidInput(
                    "complete the backup load and duration", fields=missing
                )
            demand.summary()
        return demand

    def summary(self) -> Object:
        assert self.load_kw is not None and self.duration_hours is not None
        energy = self.load_kw * self.duration_hours
        if not math.isfinite(energy):
            raise InvalidInput(
                "backup load energy must be finite",
                fields=("backup_demand.load_kw", "backup_demand.duration_hours"),
            )
        return {
            **self.model_dump(mode="json"),
            "ac_load_energy_kwh": energy,
            "energy_basis": "ac_load_before_losses",
        }
