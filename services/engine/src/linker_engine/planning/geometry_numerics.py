"""Explicit arithmetic support domain, independent of survey accuracy claims."""

from __future__ import annotations

import math

from .geometry import panel_poses
from .geometry_documents import GeometryDocument

# Product computational policy (548-design-geometry §4), not a measurement,
# fitting or industry acceptance epsilon. No coordinate snapping is performed.
# A UV chart coarser than this binary64 granularity needs an explicit change of
# reference before review/rendering can claim to represent local metre detail.
MAX_UV_RESOLUTION_M = 1e-9


def uv_resolution(document: GeometryDocument) -> float:
    coordinates = [
        value
        for roof in document.roofs
        for ring in [roof.boundary_uv, *roof.holes_uv]
        for point in ring
        for value in point
    ]
    coordinates.extend(value for array in document.arrays for value in array.origin_uv)
    coordinates.extend(
        value
        for obstacle in document.obstacles
        for point in obstacle.footprint_uv
        for value in point
    )
    coordinates.extend(
        value for pose in panel_poses(document) for value in pose.centre_uvn[:2]
    )
    coordinates.extend(
        value
        for area in document.keepouts
        for point in area.footprint_uv
        for value in point
    )
    return max((math.ulp(value) for value in coordinates), default=0.0)
