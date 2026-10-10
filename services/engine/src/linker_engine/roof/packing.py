"""How many reference modules fit on a roof plane.

A plane from LoD2 is a horizontal ring with a tilt and a facing. In a frame
turned to the facing (u along the eave, w up the slope) and with the slope
stretched by 1/cos(tilt), the ring has its true shape; after an edge inset,
portrait modules are placed in rows along the eave and only whole modules
inside the plane count. The count is an estimate with a reference module,
which the report discloses as a design assumption.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from shapely import affinity
from shapely.geometry import Polygon, box

from .. import rules
from ..catalog import PvModule
from .citygml import Ring2, RoofPlane


@dataclass(frozen=True)
class PackedPlane:
    plane: RoofPlane
    usable: bool
    reason: str | None  # why an unusable plane is skipped
    modules: list[
        Ring2
    ]  # module rectangles, horizontal projection, same frame as the plane


def _facing(plane: RoofPlane) -> float:
    """Facing used for the rows: flat planes get rows facing south."""
    if plane.tilt_deg < rules.ROOF_FLAT_TILT_DEG.value:
        return 180.0
    return plane.azimuth_deg


def usable(plane: RoofPlane) -> str | None:
    """None when the plane can carry modules, else the rule that excludes it."""
    if plane.tilt_deg > rules.ROOF_MAX_TILT_DEG.value:
        return "roof_too_steep"
    if plane.tilt_deg >= rules.ROOF_FLAT_TILT_DEG.value:
        off_north = min(plane.azimuth_deg, 360 - plane.azimuth_deg)
        if off_north < rules.ROOF_NORTH_EXCLUSION_DEG.value:
            return "roof_faces_north"
    return None


def pack(plane: RoofPlane, module: PvModule) -> PackedPlane:
    reason = usable(plane)
    if reason:
        return PackedPlane(plane, False, reason, [])
    facing = math.radians(_facing(plane))
    tilt = math.radians(
        plane.tilt_deg if plane.tilt_deg >= rules.ROOF_FLAT_TILT_DEG.value else 0
    )
    horizontal = Polygon(plane.ring)
    if not horizontal.is_valid or horizontal.area <= 0:
        return PackedPlane(plane, False, "roof_geometry", [])
    origin = horizontal.centroid
    # Turn so that the facing points to -y (down the slope), then stretch the slope.
    turned = affinity.rotate(
        horizontal, math.degrees(facing) - 180, origin=origin, use_radians=False
    )
    stretch = 1 / math.cos(tilt)
    true_shape = affinity.scale(turned, xfact=1, yfact=stretch, origin=origin)
    inner = true_shape.buffer(-rules.ROOF_EDGE_INSET_M.value)
    if inner.is_empty:
        return PackedPlane(plane, True, None, [])
    width = module.width_m + rules.MODULE_GAP_M.value
    height = module.length_m + rules.MODULE_GAP_M.value
    min_x, min_y, max_x, max_y = inner.bounds
    placed: list[Polygon] = []
    y = min_y
    while y + module.length_m <= max_y + 1e-9:
        x = min_x
        while x + module.width_m <= max_x + 1e-9:
            cell = box(x, y, x + module.width_m, y + module.length_m)
            if inner.contains(cell):
                placed.append(cell)
            x += width
        y += height
    rings: list[Ring2] = []
    for cell in placed:
        flat = affinity.scale(cell, xfact=1, yfact=1 / stretch, origin=origin)
        back = affinity.rotate(
            flat, 180 - math.degrees(facing), origin=origin, use_radians=False
        )
        rings.append([(float(x), float(y)) for x, y in back.exterior.coords])
    return PackedPlane(plane, True, None, rings)
