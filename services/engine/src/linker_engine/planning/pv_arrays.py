"""Derive PV geometry from the actual included project module poses."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .canonical import Json, Object
from .errors import InvalidInput
from .geometry import panel_poses, read_geometry
from .geometry_review import review_geometry
from .pv_parameters import PvGenerationParameters
from .pv_weather import WeatherSeries


@dataclass(frozen=True)
class GenerationArray:
    id: str
    module_spec_id: str
    module_ids: tuple[str, ...]
    stc_power_w: float
    normal_enu: tuple[float, float, float]
    tilt_deg: float
    azimuth_deg: float
    azimuth_basis: str

    def document(self) -> Object:
        return {
            "id": self.id,
            "module_spec_id": self.module_spec_id,
            "module_ids": list(self.module_ids),
            "module_count": len(self.module_ids),
            "stc_power_w": self.stc_power_w,
            "normal_enu": list(self.normal_enu),
            "tilt_deg": self.tilt_deg,
            "azimuth_north_clockwise_deg": self.azimuth_deg,
            "azimuth_basis": self.azimuth_basis,
        }


def generation_arrays(
    value: Json, weather: WeatherSeries, parameters: PvGenerationParameters
) -> tuple[GenerationArray, ...]:
    geometry = read_geometry(value)
    anchor = geometry.coordinate_system.anchor
    if anchor is None or geometry.coordinate_system.north_reference == "unreferenced":
        raise InvalidInput(
            "PV generation requires geographic anchor and declared north"
        )
    if (anchor.latitude_deg, anchor.longitude_deg) != (
        weather.latitude_deg,
        weather.longitude_deg,
    ):
        raise InvalidInput("weather location differs from project geometry anchor")
    review = review_geometry(value)
    if not review["review_complete"] or review["conflict_count"]:
        raise InvalidInput(
            "PV generation requires a complete conflict-free layout review"
        )
    poses = panel_poses(geometry)
    result = []
    for array in geometry.arrays:
        included = [p for p in poses if p.array_id == array.id and p.included]
        if not included:
            continue
        normal = included[0].normal_enu
        horizontal = math.hypot(normal[0], normal[1])
        # atan2 retains the actual composed roof/mount normal, including >90°.
        tilt = math.degrees(math.atan2(horizontal, normal[2]))
        azimuth = (
            math.degrees(math.atan2(normal[0], normal[1])) % 360 if horizontal else 0.0
        )
        result.append(
            GenerationArray(
                array.id,
                array.module_spec_id,
                tuple(p.id for p in included),
                math.fsum(p.stc_power_w for p in included),
                normal,
                tilt,
                azimuth,
                "project_enu_normal"
                if horizontal
                else "horizontal_orientation_invariant",
            )
        )
    if not result:
        raise InvalidInput("PV generation requires included modules")
    actual = {item.id for item in result}
    configured = [item.array_id for item in parameters.arrays]
    module_ids = [item.module_spec_id for item in parameters.modules]
    if set(configured) != actual or len(configured) != len(set(configured)):
        raise InvalidInput(
            "PV parameters must match every actual active array exactly once"
        )
    if set(module_ids) != {item.module_spec_id for item in result} or len(
        module_ids
    ) != len(set(module_ids)):
        raise InvalidInput("PV module parameters must match the actual module specs")
    assignments = [i for group in parameters.converters for i in group.array_ids]
    groups = [group.id for group in parameters.converters]
    if (
        set(assignments) != actual
        or len(assignments) != len(actual)
        or len(groups) != len(set(groups))
    ):
        raise InvalidInput(
            "PV conversion groups must partition the actual arrays exactly once"
        )
    return tuple(result)
