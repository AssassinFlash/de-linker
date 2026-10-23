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
from .geometry import cross, dot, roof_coordinates
from .geometry_documents import PlaneFrame
from .wire_numbers import MAX_WIRE_NUMBER

type Finite = Annotated[float, Field(allow_inf_nan=False)]


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
    up_m = (
        dot(normal, roof.origin_enu) - normal[0] * east_m - normal[1] * north_m
    ) / normal[2]
    uv = roof_coordinates(roof, (east_m, north_m, up_m))
    if not all(math.isfinite(v) and abs(v) <= MAX_WIRE_NUMBER for v in (*uv, up_m)):
        raise InvalidInput("roof projection exceeds numeric support")
    return uv
