"""Explicit scenario parameters, not a manufacturer or country qualification."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .energy_inputs import Document, SchemaVersion
from .geometry_documents import Identifier, ModuleSource, Text

type Number = Annotated[float, Field(allow_inf_nan=False)]
type Positive = Annotated[Number, Field(gt=0)]
type Fraction = Annotated[Number, Field(ge=0, le=1)]
type Efficiency = Annotated[Number, Field(gt=0, le=1)]


class PvModuleParameters(Document):
    module_spec_id: Identifier
    gamma_pdc_per_c: Number
    source: ModuleSource


class SapmParameters(Document):
    model: Literal["sapm_cell"]
    a: Number
    b: Number
    delta_t_c: Annotated[Number, Field(ge=0)]
    source_note: Text


class PvArrayParameters(Document):
    array_id: Identifier
    transposition: Literal["isotropic", "haydavies", "perez", "perez-driesse"]
    albedo: Fraction
    thermal: SapmParameters
    beam_iam_model: Literal["ashrae"]
    beam_iam_b: Annotated[Number, Field(ge=0)]
    sky_diffuse_iam_factor: Fraction
    ground_diffuse_iam_factor: Fraction
    spectral_factor: Fraction
    soiling_factor: Fraction
    dc_wiring_factor: Fraction
    dc_mismatch_factor: Fraction
    source_note: Text


class PvConversionParameters(Document):
    id: Identifier
    array_ids: Annotated[list[Identifier], Field(min_length=1)]
    model: Literal["pvwatts"]
    input_assumption: Literal[
        "independent_mppt_array_mpp_sum",
        "one_string_per_tracker_independent_mpp_sum",
    ]
    # PVWatts pdc0, not a module's STC rating or a hardware-port limit.
    reference_dc_power_w: Positive
    eta_nominal: Efficiency
    eta_reference: Efficiency
    source_note: Text


class PvGenerationParameters(Document):
    schema_version: SchemaVersion
    model: Literal["uniform_unshaded_pvlib_reference_v1"]
    pvlib_version: Literal["0.16.1"]
    temporal_policy: Literal["representative_pv_output_over_declared_intervals_v1"]
    shading_policy: Literal["explicit_unshaded_reference"]
    modules: Annotated[list[PvModuleParameters], Field(min_length=1)]
    arrays: Annotated[list[PvArrayParameters], Field(min_length=1)]
    converters: Annotated[list[PvConversionParameters], Field(min_length=1)]
    source_note: Text


class PvGenerationLimits(Document):
    max_weather_bytes: Annotated[int, Field(strict=True, gt=0)]
    max_weather_rows: Annotated[int, Field(strict=True, gt=0)]
    max_array_steps: Annotated[int, Field(strict=True, gt=0)]
