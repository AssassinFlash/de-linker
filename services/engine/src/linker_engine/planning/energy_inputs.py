"""Strict versioned JSON contracts at the persisted energy-scenario boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .battery_model import BatteryModel
from .canonical import Json, Object
from .csv_mapping import CsvMapping
from .energy_origins import EnergyOrigins
from .errors import InvalidInput
from .interval import Interval
from .operating_limits import OperatingLimits
from .power_series import Measurement
from .series_source import Origin

type PositiveEfficiency = Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
type Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type Identifier = Annotated[str, Field(min_length=1)]


class Document(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    @classmethod
    def read(cls, value: Json) -> Self:
        try:
            return cls.model_validate(value)
        except ValidationError as error:
            # Keep structured field paths without echoing a private row/file
            # in an API-facing error string. HTTP later localizes these paths.
            fields = [
                ".".join(str(part) for part in item["loc"]) for item in error.errors()
            ]
            raise InvalidInput(
                "invalid scenario fields: " + ", ".join(fields)
            ) from error


class MappingDocument(Document):
    timestamp_column: str
    value_column: str
    measurement: Measurement
    value_kind: Literal["interval_average_kw", "interval_energy_kwh"]
    timestamp_role: Literal["start", "end"]
    timezone: str
    origin: Origin
    interval_seconds: float | None
    delimiter: str
    decimal: Literal[".", ","]
    end_timestamp_column: str | None
    fold_column: str | None
    end_fold_column: str | None
    offset_rule: Literal["explicit_offset_precedes_naive_timezone"]
    within_interval_assumption: Literal["constant_mean_no_new_observations"]

    def mapping(self) -> CsvMapping:
        return CsvMapping(
            self.timestamp_column,
            self.value_column,
            self.measurement,
            self.value_kind,
            self.timestamp_role,
            self.timezone,
            self.origin,
            self.interval_seconds,
            self.delimiter,
            self.decimal,
            self.end_timestamp_column,
            self.fold_column,
            self.end_fold_column,
        )


class BatteryParameters(Document):
    schema_version: Literal[1]
    model: Literal["constant_window_single_ac_bus_v1"]
    parameter_basis: Literal["explicit_scenario"]
    usable_window_kwh: Nonnegative
    charge_ac_kw: Nonnegative
    discharge_ac_kw: Nonnegative
    eta_charge: PositiveEfficiency
    eta_discharge: PositiveEfficiency
    internal_aux_kw: Nonnegative
    standing_loss_rate_per_hour: Nonnegative

    def battery(self, source_sha256: str) -> BatteryModel:
        return BatteryModel(
            self.usable_window_kwh,
            self.charge_ac_kw,
            self.discharge_ac_kw,
            self.eta_charge,
            self.eta_discharge,
            self.internal_aux_kw,
            self.standing_loss_rate_per_hour,
            source_sha256,
        )


class InitialInventory(Document):
    pv_kwh: Nonnegative
    grid_kwh: Nonnegative
    initial_unknown_kwh: Nonnegative
    basis: Literal["user_declared", "synthetic_fixture"]
    source_note: Identifier

    def energy(self) -> EnergyOrigins:
        return EnergyOrigins(self.pv_kwh, self.grid_kwh, self.initial_unknown_kwh)


class ScheduleSegment(Document):
    start_utc: str
    end_utc: str
    mode: Literal["connected", "outage"]
    reserve_kwh: Nonnegative
    import_cap_kw: Nonnegative | None
    export_cap_kw: Nonnegative | None
    pv_enabled: bool
    allow_grid_charge: bool

    def interval(self) -> Interval:
        try:
            return Interval(
                datetime.fromisoformat(self.start_utc),
                datetime.fromisoformat(self.end_utc),
            )
        except ValueError as error:
            raise InvalidInput("schedule requires explicit ISO timestamps") from error

    def limits(self) -> OperatingLimits:
        return OperatingLimits(
            self.mode,
            self.reserve_kwh,
            self.import_cap_kw,
            self.export_cap_kw,
            self.pv_enabled,
            self.allow_grid_charge,
        )


class EnergyInputs(Document):
    schema_version: Literal[1]
    gross_load_asset_id: Identifier
    critical_load_asset_id: Identifier | None
    pv_available_asset_id: Identifier
    aux_ac_asset_id: Identifier
    battery_parameters_asset_id: Identifier
    initial_inventory: InitialInventory
    schedule: Annotated[list[ScheduleSegment], Field(min_length=1)]
    controller: Literal["self_consumption_with_reserve_v1"]
    terminal_min_kwh: Nonnegative | None

    @classmethod
    def from_project(cls, inputs: Object) -> Self:
        return cls.read(inputs.get("energy_replay"))

    def profiles(self) -> dict[str, str]:
        result = {
            "gross_load": self.gross_load_asset_id,
            "pv_available_ac": self.pv_available_asset_id,
            "aux_ac": self.aux_ac_asset_id,
        }
        if self.critical_load_asset_id is not None:
            result["critical_load"] = self.critical_load_asset_id
        return result
