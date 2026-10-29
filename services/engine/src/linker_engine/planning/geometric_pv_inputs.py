"""Explicit direct-only geometry scenario; no inferred submodule circuit."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from .canonical import Object
from .direct_beam_inputs import DirectBeamSampling
from .energy_inputs import Document, SchemaVersion
from .geometric_pv_limits import GeometricPvLimits as GeometricPvLimits
from .pv_parameters import PvGenerationParameters

MODEL = "opaque_direct_uniform_pvlib_reference_v1"
KIND = "prepare_geometric_pv_reference_v1"
PROFILE_PURPOSE = "geometric_pv_reference_profile_v1"


class GeometricPvInputs(Document):
    schema_version: SchemaVersion
    model: Literal["opaque_direct_uniform_pvlib_reference_v1"]
    weather_asset_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    sampling: DirectBeamSampling
    diffuse_policy: Literal["retain_unobstructed_sky_and_ground_components_v1"]
    thermal_policy: Literal["sapm_from_module_mean_poa_v1"]
    electrical_policy: Literal["uniform_module_pvwatts_independent_mpp_sum_v1"]
    # These are the existing explicit coefficients/converter assumptions. Their
    # nested reference identity does not give this new result an unshaded label.
    parameters: PvGenerationParameters

    def product_inputs(self, inputs: Object) -> Object:
        return {**inputs, "pv_generation": self.parameters.model_dump(mode="json")}
