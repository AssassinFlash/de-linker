"""Buildings and roof planes from official LoD2 CityGML (CityGML 1.0 and 2.0).

The state surveying offices publish LoD2 building models as CityGML tiles in
ETRS89 / UTM (docs/research of the old repository, 2026-08-29: "Canvas
imagery + LOD2 investigation", part 2, section 1). Each building (or building
part) carries its ground surface and its roof surfaces as 3D polygons; this
module reads them as a stream, so a 120 MB tile never sits in memory whole.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from typing import IO

GML = "{http://www.opengis.net/gml}"
BUILDING_NAMESPACES = (
    "{http://www.opengis.net/citygml/building/1.0}",
    "{http://www.opengis.net/citygml/building/2.0}",
)
XAL = "{urn:oasis:names:tc:ciq:xsdschema:xAL:2.0}"

Point3 = tuple[float, float, float]
Ring2 = list[tuple[float, float]]


@dataclass(frozen=True)
class RoofPlane:
    ring: Ring2  # exterior ring in projected metres (x east, y north)
    tilt_deg: float
    azimuth_deg: float  # direction the plane faces: north 0, east 90, south 180
    area_m2: float  # true (sloped) area


@dataclass(frozen=True)
class Building:
    id: str
    address: str | None
    footprint: list[Ring2]
    planes: list[RoofPlane]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _rings(element: ET.Element) -> Iterator[list[Point3]]:
    for poslist in element.iter(f"{GML}posList"):
        values = [float(v) for v in (poslist.text or "").split()]
        dimension = int(poslist.get("srsDimension") or 3)
        if dimension != 3 or len(values) < 9:
            continue
        yield [
            (values[i], values[i + 1], values[i + 2])
            for i in range(0, len(values) - 2, 3)
        ]


def newell_normal(ring: list[Point3]) -> tuple[float, float, float]:
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(ring, ring[1:] + ring[:1], strict=True):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return nx, ny, nz


def plane_of(ring: list[Point3]) -> RoofPlane | None:
    """Tilt, facing and true area of one planar roof polygon; None for a degenerate one."""
    nx, ny, nz = newell_normal(ring)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-6:
        return None
    if nz < 0:  # orient the normal upwards whatever the ring direction
        nx, ny, nz = -nx, -ny, -nz
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, nz / length))))
    azimuth = (math.degrees(math.atan2(nx, ny)) + 360) % 360
    return RoofPlane(
        ring=[(x, y) for x, y, _ in ring],
        tilt_deg=round(tilt, 1),
        azimuth_deg=round(azimuth, 1),
        area_m2=round(length / 2, 2),
    )


def _address(element: ET.Element) -> str | None:
    street = element.find(f".//{XAL}ThoroughfareName")
    number = element.find(f".//{XAL}ThoroughfareNumber")
    if street is None or not street.text:
        return None
    text = street.text.strip()
    if number is not None and number.text:
        text = f"{text} {number.text.strip()}"
    return text


def _surfaces(element: ET.Element, kind: str) -> list[list[Point3]]:
    out: list[list[Point3]] = []
    for namespace in BUILDING_NAMESPACES:
        for surface in element.iter(f"{namespace}{kind}"):
            out.extend(_rings(surface))
    return out


def read_buildings(source: IO[bytes] | str) -> Iterator[Building]:
    """Every building of a CityGML document, with building parts merged into it."""
    building_tags = {f"{ns}Building" for ns in BUILDING_NAMESPACES}
    for _event, element in ET.iterparse(source, events=("end",)):
        if element.tag not in building_tags:
            continue
        planes = [
            p for p in (plane_of(r) for r in _surfaces(element, "RoofSurface")) if p
        ]
        ground = [
            [(x, y) for x, y, _ in ring] for ring in _surfaces(element, "GroundSurface")
        ]
        yield Building(
            id=element.get(f"{GML}id") or "",
            address=_address(element),
            footprint=ground,
            planes=planes,
        )
        element.clear()
