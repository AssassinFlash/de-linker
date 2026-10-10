"""POST /roof/outline: the official outline and roof planes at a clicked position.

The postcode gives the state, the state its LoD2 source; the building whose
footprint contains the position (or the nearest one within CLICK_TOLERANCE_M)
is returned with every roof plane, its tilt and facing, and how many
reference modules fit on it.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from shapely.geometry import Point, Polygon
from shapely.geometry.base import BaseGeometry

from .. import geo
from ..catalog import PvModule
from ..models import RoofPackRequest, RoofPlaneResult, RoofRequest, RoofResult
from ..texts import t
from . import lod2
from .citygml import RoofPlane
from .packing import pack

# A click on the eaves overhang or the roof edge of the aerial image still
# selects the building: LoD2 footprints follow the walls, roofs reach beyond them.
CLICK_TOLERANCE_M = 3.0

# WGS84 coordinates are rounded to 7 decimals (about 1 cm): the projection
# library's last bits differ between platforms, and a map has no use for more.
COORD_DECIMALS = 7


def _ring(zone: int, ring: list[list[float]]) -> list[tuple[float, float]]:
    return [
        (round(lon, COORD_DECIMALS), round(lat, COORD_DECIMALS))
        for lon, lat in (lod2.to_wgs84(zone, x, y) for x, y in ring)
    ]


def _shape(building: dict[str, Any]) -> BaseGeometry:
    rings = building["footprint"] or [plane["ring"] for plane in building["planes"]]
    polygons = [Polygon(ring) for ring in rings if len(ring) >= 3]
    valid = [p if p.is_valid else p.buffer(0) for p in polygons]
    union: BaseGeometry = valid[0]
    for polygon in valid[1:]:
        union = union.union(polygon)
    return union


class RoofService:
    def __init__(
        self, cache_dir: Path, module: PvModule, index: lod2.TileIndex | None = None
    ) -> None:
        self._index = index or lod2.TileIndex(cache_dir)
        self._module = module

    def outline(self, request: RoofRequest) -> RoofResult:
        locale = request.locale
        place = geo.lookup(request.plz)
        if place is None:
            raise lod2.Lod2Unavailable(f"unknown postcode {request.plz}")
        latitude, longitude = request.location.latitude, request.location.longitude
        tile = lod2.tile_for(place.state, latitude, longitude)
        index = self._index.load(tile)
        x, y = lod2.to_utm(tile.zone, latitude, longitude)
        point = Point(x, y)
        best: tuple[float, dict[str, Any]] | None = None
        for building in index["buildings"]:
            distance = _shape(building).distance(point)
            if distance <= CLICK_TOLERANCE_M and (best is None or distance < best[0]):
                best = (distance, building)
        module = self._module
        name = f"{module.brand} {module.model}"
        source = f"LoD2 {place.state}"
        assumptions = [
            t(f"assume.{key}", locale)
            for key in (
                "roof_flat",
                "roof_max_tilt",
                "roof_north",
                "roof_edge_inset",
                "module_gap",
            )
        ]
        if best is None:
            return RoofResult(
                found=False,
                building_id=None,
                address=None,
                distance_m=None,
                outline=[],
                planes=[],
                modules=0,
                kwp=0.0,
                module=name,
                module_wp=module.pmax_w,
                source=source,
                licence=tile.licence,
                assumptions=assumptions,
            )
        distance, building = best
        planes: list[RoofPlaneResult] = []
        for number, raw in enumerate(building["planes"], start=1):
            plane = RoofPlane(
                ring=[(float(px), float(py)) for px, py in raw["ring"]],
                tilt_deg=raw["tilt"],
                azimuth_deg=raw["azimuth"],
                area_m2=raw["area"],
            )
            packed = pack(plane, module)
            count = len(packed.modules)
            planes.append(
                RoofPlaneResult(
                    id=number,
                    polygon=_ring(tile.zone, raw["ring"]),
                    tilt_deg=plane.tilt_deg,
                    azimuth_deg=plane.azimuth_deg,
                    area_m2=plane.area_m2,
                    usable=packed.usable,
                    excluded_reason=packed.reason,
                    modules=count,
                    kwp=round(count * module.pmax_w / 1000, 2),
                    module_polygons=[
                        _ring(tile.zone, [list(p) for p in ring])
                        for ring in packed.modules
                    ],
                )
            )
        total = sum(p.modules for p in planes)
        return RoofResult(
            found=True,
            building_id=building["id"],
            address=building["address"],
            distance_m=round(distance, 1),
            outline=[_ring(tile.zone, ring) for ring in building["footprint"]],
            planes=planes,
            modules=total,
            kwp=round(total * module.pmax_w / 1000, 2),
            module=name,
            module_wp=module.pmax_w,
            source=source,
            licence=tile.licence,
            assumptions=assumptions,
        )


def _zone(longitude: float) -> int:
    """UTM zone of a German longitude (32 west of 12° E, 33 east of it)."""
    return 32 if longitude < 12 else 33


def pack_drawn(request: RoofPackRequest, module: PvModule) -> RoofPlaneResult:
    """Modules on a plane the user drew on the aerial image, at the tilt and facing they give."""
    zone = _zone(request.polygon[0][0])
    ring = [
        lod2.to_utm(zone, latitude, longitude)
        for longitude, latitude in request.polygon
    ]
    horizontal = Polygon(ring)
    area = horizontal.area / max(math.cos(math.radians(request.tilt_deg)), 1e-6)
    plane = RoofPlane(
        ring=ring,
        tilt_deg=request.tilt_deg,
        azimuth_deg=request.azimuth_deg,
        area_m2=round(area, 2),
    )
    packed = pack(plane, module)
    count = len(packed.modules)
    return RoofPlaneResult(
        id=1,
        polygon=[(float(lon), float(lat)) for lon, lat in request.polygon],
        tilt_deg=plane.tilt_deg,
        azimuth_deg=plane.azimuth_deg,
        area_m2=plane.area_m2,
        usable=packed.usable,
        excluded_reason=packed.reason,
        modules=count,
        kwp=round(count * module.pmax_w / 1000, 2),
        module_polygons=[
            _ring(zone, [list(p) for p in ring]) for ring in packed.modules
        ],
    )
