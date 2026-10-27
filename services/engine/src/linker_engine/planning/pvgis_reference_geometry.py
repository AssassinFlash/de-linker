"""Project included module poses without inventing weather or device parameters."""

import math

from .canonical import Object, digest, encode
from .errors import InvalidInput
from .geometry import panel_poses, read_geometry
from .geometry_review import review_geometry
from .pvgis_reference_array import PvgisReferenceArray
from .pvgis_reference_inputs import PvgisReferenceInputs
from .pvgis_reference_plan import PvgisReferencePlan
from .pvgis_request import PvgisRequest
from .weather_fetch_plan import WeatherFetchLimits


def reference_plan(
    inputs: Object,
    module_basis_sha256: str,
    limits: WeatherFetchLimits,
    max_array_steps: int,
) -> PvgisReferencePlan:
    parameters = PvgisReferenceInputs.read(inputs.get("pvgis_reference"))
    geometry = read_geometry(inputs.get("geometry"))
    anchor = geometry.coordinate_system.anchor
    if anchor is None or geometry.coordinate_system.north_reference == "unreferenced":
        raise InvalidInput(
            "PVGIS roof reference requires a geographic anchor and north"
        )
    review = review_geometry(inputs.get("geometry"))
    if not review["review_complete"] or review["conflict_count"]:
        raise InvalidInput(
            "PVGIS roof reference requires a complete conflict-free layout"
        )
    poses = panel_poses(geometry)
    arrays = []
    for array in geometry.arrays:
        included = [p for p in poses if p.array_id == array.id and p.included]
        if not included:
            continue
        normal = included[0].normal_enu
        if any(p.normal_enu != normal for p in included):
            raise InvalidInput("a PVGIS array must have one actual module orientation")
        horizontal = math.hypot(normal[0], normal[1])
        tilt = math.degrees(math.atan2(horizontal, normal[2]))
        if not 0 <= tilt <= 90:
            raise InvalidInput("PVGIS fixed-plane inclination is outside its domain")
        azimuth = (
            math.degrees(math.atan2(normal[0], normal[1])) % 360 if horizontal else 0.0
        )
        power = math.fsum(p.stc_power_w for p in included)
        arrays.append(
            PvgisReferenceArray(
                id=array.id,
                module_spec_id=array.module_spec_id,
                module_ids=[p.id for p in included],
                module_count=len(included),
                stc_power_w=power,
                normal_enu=list(normal),
                tilt_deg=tilt,
                azimuth_north_clockwise_deg=azimuth,
                azimuth_basis="project_enu_normal"
                if horizontal
                else "horizontal_orientation_invariant",
                request=PvgisRequest(
                    schema_version=1,
                    api_version="5.3",
                    radiation_database=parameters.radiation_database,
                    latitude_deg=anchor.latitude_deg,
                    longitude_deg=anchor.longitude_deg,
                    start_year=parameters.year,
                    end_year=parameters.year,
                    peak_power_kwp=power / 1000,
                    system_loss_percent=parameters.system_loss_percent,
                    pv_technology=parameters.pv_technology,
                    mounting_place=parameters.mounting_place,
                    tilt_deg=tilt,
                    azimuth_north_clockwise_deg=azimuth,
                    use_terrain_horizon=parameters.use_terrain_horizon,
                ),
            )
        )
    if not arrays:
        raise InvalidInput("PVGIS roof reference requires included modules")
    return PvgisReferencePlan.read(
        {
            "schema_version": 1,
            "kind": "pvgis_5_3_roof_ac_reference_plan_v1",
            "parameters": parameters.model_dump(mode="json"),
            "geometry_sha256": digest(encode(inputs.get("geometry"))),
            "parameters_sha256": digest(encode(inputs.get("pvgis_reference"))),
            "module_basis_sha256": module_basis_sha256,
            "limits": limits.model_dump(mode="json"),
            "max_array_steps": max_array_steps,
            "arrays": [a.model_dump(mode="json") for a in arrays],
        }
    )
