"""Explicit geometric PV scenarios; no inferred submodule circuit."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from .canonical import Object
from .direct_beam_inputs import DirectBeamSampling
from .energy_inputs import Document, SchemaVersion
from .geometric_pv_limits import GeometricPvLimits as GeometricPvLimits
from .pv_parameters import PvGenerationParameters

MODEL_V1 = "opaque_direct_uniform_pvlib_reference_v1"
POLICY_V1 = "retain_unobstructed_sky_and_ground_components_v1"
MODEL_V2 = "opaque_perez_component_visibility_pvlib_reference_v1"
POLICY_V2 = "cosine_weighted_perez_component_visibility_v1"
# Retained name of the immutable direct-only request. New requests use MODEL_V2.
MODEL = MODEL_V1
KIND = "prepare_geometric_pv_reference_v1"
PROFILE_PURPOSE = "geometric_pv_reference_profile_v1"
MODEL_ROLES = {
    MODEL_V1: "direct_only_geometry_uniform_module_reference_scenario",
    MODEL_V2: "perez_component_visibility_uniform_module_reference_scenario",
}
SHADING_STATUS = {
    MODEL_V1: "direct_only_scenario_not_complete_assessment",
    MODEL_V2: "perez_component_visibility_not_complete_assessment",
}
_PAIRS = {(MODEL_V1, POLICY_V1), (MODEL_V2, POLICY_V2)}


class GeometricPvInputs(Document):
    schema_version: SchemaVersion
    model: Literal[
        "opaque_direct_uniform_pvlib_reference_v1",
        "opaque_perez_component_visibility_pvlib_reference_v1",
    ]
    weather_asset_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    sampling: DirectBeamSampling
    diffuse_policy: Literal[
        "retain_unobstructed_sky_and_ground_components_v1",
        "cosine_weighted_perez_component_visibility_v1",
    ]
    thermal_policy: Literal["sapm_from_module_mean_poa_v1"]
    electrical_policy: Literal["uniform_module_pvwatts_independent_mpp_sum_v1"]
    # These are the existing explicit coefficients/converter assumptions. Their
    # nested reference identity does not give this new result an unshaded label.
    parameters: PvGenerationParameters

    @model_validator(mode="after")
    def paired_policy(self) -> Self:
        if (self.model, self.diffuse_policy) not in _PAIRS:
            raise ValueError(
                "geometric PV model and diffuse policy must be a declared pair"
            )
        if self.model == MODEL_V2 and any(
            item.transposition != "perez" for item in self.parameters.arrays
        ):
            raise ValueError(
                "Perez component visibility requires the declared Perez transposition"
            )
        return self

    def product_inputs(self, inputs: Object) -> Object:
        return {**inputs, "pv_generation": self.parameters.model_dump(mode="json")}
