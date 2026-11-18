"""Photovoltaic inputs and evidence for the durable equipment comparison."""

from __future__ import annotations

import math
from datetime import datetime
from typing import cast

from .assets import Asset, Assets
from .canonical import Json, Object, digest, encode
from .energy_inputs import storage_only_project
from .errors import InvalidInput
from .geometry import panel_poses, read_geometry
from .product_sources import ProductSources
from .profile_assets import profile_dependencies
from .profile_selections import ProfileSelections
from .pvgis_known_inputs import MODEL as KNOWN_MODEL
from .pvgis_known_inputs import PROFILE_PURPOSE as KNOWN_PURPOSE
from .pvgis_reference_kernel import PvgisRoofReferenceKernel
from .pvgis_reference_profile import PROFILE_PURPOSE as ROOF_PURPOSE
from .records import Actor
from .workspace import Workspace


class ComparisonPvNoCommonPeriod(InvalidInput):
    code = "comparison_pv_no_common_period"


class ComparisonPv:
    def __init__(
        self,
        workspace: Workspace,
        products: ProductSources,
        reference: PvgisRoofReferenceKernel,
    ) -> None:
        self.workspace = workspace
        self.products = products
        self.reference = reference

    def declarations(self, inputs: Object) -> Object:
        brief = inputs.get("brief")
        if not isinstance(brief, dict) or brief.get("system_scope") not in (
            "new_pv_storage",
            "pv_only",
        ):
            return inputs
        parameters = inputs.get("pvgis_reference")
        if isinstance(parameters, dict) and parameters.get("model") == KNOWN_MODEL:
            arrays = cast(list[Object], parameters["arrays"])
            power = math.fsum(cast(float, a["peak_power_kwp"]) for a in arrays)
        else:
            power = roof_power(inputs)
        if not power:
            return inputs
        plant = inputs.get("equipment_plant_setup")
        if isinstance(plant, dict):
            requirements = plant.get("requirements")
            if isinstance(requirements, dict):
                return {
                    **inputs,
                    "equipment_plant_setup": {
                        **plant,
                        "requirements": {**requirements, "pv_dc_kw": power},
                    },
                }
        setup = inputs.get("equipment_setup")
        if isinstance(setup, dict):
            return {**inputs, "equipment_setup": {**setup, "pv_dc_kw": power}}
        return inputs

    def context(
        self, actor: Actor, project_id: str, inputs: Object
    ) -> tuple[dict[str, str], bool]:
        if storage_only_project(inputs):
            return {}, False
        raw = inputs.get("profile_selections")
        selected = ProfileSelections.read(raw).selected if raw is not None else {}
        asset = (
            Assets(self.workspace).get(actor, project_id, selected["pv_available_ac"])
            if "pv_available_ac" in selected
            else None
        )
        parameters = inputs.get("pvgis_reference")
        setup = inputs.get("pvgis_reference_setup", parameters)
        known = isinstance(setup, dict) and setup.get("model") == KNOWN_MODEL
        placed = not known and roof_power(inputs) > 0
        managed = asset is not None and asset.purpose in (KNOWN_PURPOSE, ROOF_PURPOSE)
        if asset is not None and not managed:
            self.products.check_profile(asset.metadata)
            return profile_dependencies(
                asset, "pv_available_ac", inputs, self.workspace.blobs
            ), False
        brief = inputs.get("brief")
        if (
            not known
            and placed
            and asset is None
            and "gross_load" not in selected
            and isinstance(brief, dict)
            and brief.get("system_scope") == "pv_only"
        ):
            return {}, False
        if not (known or placed or managed or setup is not None):
            return {}, False
        if parameters is None:
            raise InvalidInput(
                "complete the PVGIS reference settings",
                fields=("pvgis_reference_setup",),
            )
        single = inputs.get("energy_scenario", inputs.get("energy_replay"))
        plant = inputs.get("energy_plant_setup", inputs.get("energy_plant"))
        if (
            isinstance(single, dict)
            and single.get("coupling") == "shared_dc"
            or isinstance(plant, dict)
            and plant.get("coupling") == "plant_shared_dc"
            or "pv_reference" in selected
        ):
            raise InvalidInput(
                "an AC reference cannot replace the selected DC PV source",
                fields=("profile_selections.selected.pv_reference",),
            )
        if asset is not None and self.matches(inputs, asset, known):
            self.products.check_profile(asset.metadata)
            return profile_dependencies(
                asset, "pv_available_ac", inputs, self.workspace.blobs
            ), False
        context = self.reference.context(inputs)
        return dict(context.assets), True

    @staticmethod
    def matches(inputs: Object, asset: Asset, known: bool) -> bool:
        if asset.purpose != (
            KNOWN_PURPOSE if known else ROOF_PURPOSE
        ) or asset.metadata.get("parameters_sha256") != digest(
            encode(inputs.get("pvgis_reference"))
        ):
            return False
        if known:
            from .brief import PlanningBrief

            site = PlanningBrief.read(inputs.get("brief")).site.model_dump(mode="json")
            return asset.metadata.get("site_sha256") == digest(encode(site))
        return asset.metadata.get("geometry_sha256") == digest(
            encode(inputs.get("geometry"))
        )


def roof_power(inputs: Object) -> float:
    if "geometry" not in inputs:
        return 0
    return math.fsum(
        pose.stc_power_w / 1000
        for pose in panel_poses(read_geometry(inputs["geometry"]))
        if pose.included
    )


def comparison_horizon(inputs: Object, metadata: Object) -> Object:
    scenario = inputs.get("energy_scenario")
    if not isinstance(scenario, dict) or "backup_demand" in inputs:
        return inputs
    periods = scenario.get("schedule")
    if (
        not isinstance(periods, list)
        or not periods
        or not any(isinstance(p, dict) and p.get("pv_enabled") is True for p in periods)
    ):
        return inputs
    interpretation = metadata.get("interpretation")
    if (
        not isinstance(interpretation, dict)
        or "start_utc" not in interpretation
        or "end_utc" not in interpretation
    ):
        return inputs
    axis_start = datetime.fromisoformat(cast(str, interpretation["start_utc"]))
    axis_end = datetime.fromisoformat(cast(str, interpretation["end_utc"]))
    schedule: list[Json] = []
    for period in cast(list[Object], periods):
        start = max(axis_start, datetime.fromisoformat(cast(str, period["start_utc"])))
        end = min(axis_end, datetime.fromisoformat(cast(str, period["end_utc"])))
        if start < end:
            schedule.append(
                {**period, "start_utc": start.isoformat(), "end_utc": end.isoformat()}
            )
    if not schedule:
        raise ComparisonPvNoCommonPeriod("the load and PV periods do not overlap")
    return {**inputs, "energy_scenario": {**scenario, "schedule": schedule}}
