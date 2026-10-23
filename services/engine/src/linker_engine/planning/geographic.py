"""WGS84/ENU boundary; source quality and a roof's relative height stay separate.

The operation is PROJ cart -> topocentric with explicit WGS84, not Web Mercator
or an empirical latitude scale. See the map-workbench-integration dossier.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal, Self

import pyproj
from pydantic import Field, model_validator
from pyproj import Transformer
from pyproj.enums import TransformDirection
from pyproj.exceptions import ProjError

from .canonical import Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput
from .geometry import cross, dot, sin_cos_degrees
from .geometry_documents import PlaneFrame
from .geometry_numerics import MAX_UV_RESOLUTION_M
from .wire_numbers import MAX_WIRE_NUMBER

type Finite = Annotated[float, Field(allow_inf_nan=False)]

# A round-trip branch/convergence check, not source or measurement accuracy.
# Metric representability is checked separately; an angular residual alone
# cannot establish local metre precision, especially near the horizon.
MAX_DIRECTION_RESIDUAL = 2e-12


class GeographicReference(Document):
    schema_version: SchemaVersion
    method: Literal["wgs84_cart_topocentric_v1"]
    longitude_deg: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]
    latitude_deg: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
    ellipsoid_height_m: Finite
    height_basis: Literal["known_wgs84_ellipsoid", "zero_height_horizontal_convention"]

    @model_validator(mode="after")
    def horizontal_zero(self) -> Self:
        if (
            self.height_basis == "zero_height_horizontal_convention"
            and self.ellipsoid_height_m != 0
        ):
            raise ValueError(
                "horizontal-only reference requires its explicit zero convention"
            )
        return self


class GeographicBridge:
    """A fixed operation, never an inferred source CRS or vertical datum."""

    def __init__(self, reference: GeographicReference) -> None:
        self.reference = reference
        self.pipeline = (
            "+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad "
            "+step +proj=cart +ellps=WGS84 "
            "+step +proj=topocentric +ellps=WGS84 "
            f"+lon_0={reference.longitude_deg!r} "
            f"+lat_0={reference.latitude_deg!r} "
            f"+h_0={reference.ellipsoid_height_m!r}"
        )
        self.transformer = Transformer.from_pipeline(self.pipeline)

    def manifest(self) -> Object:
        return {
            "schema_version": 1,
            "reference": self.reference.model_dump(mode="json"),
            "input_crs": "EPSG:4979",
            "input_axis_order": "longitude_latitude_ellipsoid_height",
            "output_axes": "east_north_up_metres",
            "operation": self.pipeline,
            "pyproj": pyproj.__version__,
            "proj": pyproj.proj_version_str,
            # This fixed ellipsoid operation uses no external datum/grid file.
            "grid_dependencies": [],
        }

    def forward(
        self, longitude_deg: float, latitude_deg: float, ellipsoid_height_m: float
    ) -> tuple[float, float, float]:
        if (
            not -180 <= longitude_deg <= 180
            or not -90 <= latitude_deg <= 90
            or not math.isfinite(ellipsoid_height_m)
        ):
            raise InvalidInput("invalid geographic position")
        if (
            self.reference.height_basis == "zero_height_horizontal_convention"
            and ellipsoid_height_m != 0
        ):
            raise InvalidInput(
                "horizontal-only coordinates cannot declare measured elevation"
            )
        return self._transform(longitude_deg, latitude_deg, ellipsoid_height_m)

    def inverse(
        self, east_m: float, north_m: float, up_m: float
    ) -> tuple[float, float, float]:
        """Inverse of the full ENU point; callers must not drop/guess its Up."""
        if not all(math.isfinite(v) for v in (east_m, north_m, up_m)):
            raise InvalidInput("invalid local metric position")
        return self._transform(east_m, north_m, up_m, inverse=True)

    def up_at(
        self, longitude_deg: float, latitude_deg: float
    ) -> tuple[float, float, float]:
        """Geodetic vertical direction at a position, expressed in anchor ENU."""
        if not -180 <= longitude_deg <= 180 or not -90 <= latitude_deg <= 90:
            raise InvalidInput("invalid geographic position")
        slon, clon = sin_cos_degrees(longitude_deg - self.reference.longitude_deg)
        slat, clat = sin_cos_degrees(latitude_deg)
        slat0, clat0 = sin_cos_degrees(self.reference.latitude_deg)
        return (
            clat * slon,
            clat0 * slat - slat0 * clat * clon,
            slat0 * slat + clat0 * clat * clon,
        )

    def _transform(
        self, a: float, b: float, c: float, *, inverse: bool = False
    ) -> tuple[float, float, float]:
        try:
            x, y, z = self.transformer.transform(
                a,
                b,
                c,
                direction=TransformDirection.INVERSE
                if inverse
                else TransformDirection.FORWARD,
                errcheck=True,
            )
        except ProjError as error:
            raise InvalidInput("geographic operation could not be resolved") from error
        if not all(math.isfinite(v) and abs(v) <= MAX_WIRE_NUMBER for v in (x, y, z)):
            raise InvalidInput("geographic operation exceeds numeric support")
        return float(x), float(y), float(z)


def horizontal_on_roof(
    roof: PlaneFrame, east_m: float, north_m: float
) -> tuple[float, float]:
    """Intersect an E/N vertical line with the declared plane before UV projection.

    Curvature Up from a horizontal geographic transform is not a roof height.
    Setting input Z=0 and dot-projecting a pitched roof would shorten its slope.
    """
    normal = cross(roof.u_axis_enu, roof.v_axis_enu)
    if not math.isfinite(normal[2]) or normal[2] <= 0:
        raise InvalidInput("roof horizontal projection is not invertible")
    # Solve the horizontal 2x2 system in the local chart. Constructing an
    # absolute Up and then subtracting a large origin loses small slope detail.
    east, north = east_m - roof.origin_enu[0], north_m - roof.origin_enu[1]
    u, v = roof.u_axis_enu, roof.v_axis_enu
    uv = (
        (east * v[1] - north * v[0]) / normal[2],
        (u[0] * north - u[1] * east) / normal[2],
    )
    if not all(math.isfinite(value) and abs(value) <= MAX_WIRE_NUMBER for value in uv):
        raise InvalidInput("roof projection exceeds numeric support")
    return uv


def geographic_on_roof(
    bridge: GeographicBridge,
    roof: PlaneFrame,
    longitude_deg: float,
    latitude_deg: float,
) -> tuple[float, float]:
    """Intersect a geodetic vertical line with the declared ENU roof plane.

    The full zero-height position is retained. Dropping its curvature Up would
    orthographically fold the far hemisphere into the local roof. Negative
    derived ellipsoid heights are allowed: the zero convention is not ground.
    """
    base = bridge.forward(longitude_deg, latitude_deg, 0)
    vertical = bridge.up_at(longitude_deg, latitude_deg)
    u, v = roof.u_axis_enu, roof.v_axis_enu
    normal = cross(u, v)
    denominator = dot(normal, vertical)
    if not math.isfinite(denominator) or denominator <= 0:
        raise InvalidInput("geographic roof intersection is not forward-facing")
    relative = (
        base[0] - roof.origin_enu[0],
        base[1] - roof.origin_enu[1],
        base[2] - roof.origin_enu[2],
    )
    uv = (
        dot(cross(v, vertical), relative) / denominator,
        dot(cross(vertical, u), relative) / denominator,
    )
    point = tuple(
        roof.origin_enu[axis] + u[axis] * uv[0] + v[axis] * uv[1] for axis in range(3)
    )
    # Reuse the accepted chart's binary64 granularity policy, also for the ENU
    # point that crosses the geodetic boundary. This is not a radius/roof limit.
    if any(
        not math.isfinite(value)
        or abs(value) > MAX_WIRE_NUMBER
        or math.ulp(value) > MAX_UV_RESOLUTION_M
        for value in (*uv, *point)
    ):
        raise InvalidInput("geographic roof intersection exceeds numeric support")
    longitude, latitude, _derived_height = bridge.inverse(*point)
    returned_vertical = bridge.up_at(longitude, latitude)
    if math.dist(vertical, returned_vertical) > MAX_DIRECTION_RESIDUAL:
        raise InvalidInput("geographic roof intersection cannot preserve its position")
    return uv
