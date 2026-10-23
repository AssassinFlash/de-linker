"""Explicit arithmetic support domain, independent of survey accuracy claims."""

from __future__ import annotations

import math

from .geometry import dot, panel_poses, scale
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
    rules = {rule.roof_id: rule for rule in document.layout_rules}
    for pose in panel_poses(document):
        coordinates.extend(pose.centre_uvn[:2])
        coordinates.extend(value for point in pose.corners_uvn() for value in point[:2])
        coordinates.extend(value for point in pose.footprint_uv for value in point)
        rule = rules.get(pose.roof_id)
        clearance = rule.obstacle_clearance_m if rule is not None else None
        if clearance is not None:
            for axis in range(2):
                values = [p[axis] for p in pose.footprint_uv]
                coordinates.extend([min(values) - clearance, max(values) + clearance])
    roofs = {roof.id: roof for roof in document.roofs}
    for obstacle in document.obstacles:
        roof = roofs[obstacle.roof_id]
        extrusion = scale(obstacle.extrusion_axis_enu, obstacle.height_m)
        du, dv = dot(extrusion, roof.u_axis_enu), dot(extrusion, roof.v_axis_enu)
        coordinates.extend(
            value for u, v in obstacle.footprint_uv for value in [u + du, v + dv]
        )
    coordinates.extend(
        value
        for area in document.keepouts
        for point in area.footprint_uv
        for value in point
    )
    return max((math.ulp(value) for value in coordinates), default=0.0)
