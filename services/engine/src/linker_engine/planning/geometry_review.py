"""Roof-plane layout diagnostics, never a 3D or engineering release.

Shapely/GEOS ignores Z. We explicitly project full solids into each roof plane;
projection conflicts are conservative. APIs/limits: design-geometry research.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import shapely
from shapely import STRtree
from shapely.affinity import translate
from shapely.errors import GEOSException
from shapely.geometry import MultiPoint, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from .canonical import Json, Object, digest, encode
from .errors import InvalidInput
from .geometry import (
    add,
    cross,
    dot,
    on_roof,
    panel_poses,
    read_geometry,
    roof_coordinates,
    scale,
)
from .geometry_documents import GeometryDocument

# Preview resource policy; exceeding either is explicit, never an all-clear.
MAX_DIAGNOSTICS = 200
MAX_CANDIDATE_CHECKS = 200000


@dataclass
class Diagnostics:
    issues: list[Json] = field(default_factory=list)
    issue_count: int = 0
    conflict_count: int = 0
    candidate_checks: int = 0
    complete: bool = True

    def add(
        self,
        kind: str,
        object_id: str,
        roof_id: str | None,
        *,
        related_id: str | None = None,
        missing: bool = False,
        required_m: float | None = None,
        actual_m: float | None = None,
    ) -> None:
        self.issue_count += 1
        self.conflict_count += not missing
        if len(self.issues) < MAX_DIAGNOSTICS:
            self.issues.append(
                {
                    "kind": kind,
                    "object_id": object_id,
                    "roof_id": roof_id,
                    "related_id": related_id,
                    "category": "missing_input" if missing else "layout_conflict",
                    "required_m": required_m,
                    "actual_m": actual_m,
                }
            )

    def candidate(self) -> bool:
        if self.candidate_checks >= MAX_CANDIDATE_CHECKS:
            self.complete = False
            return False
        self.candidate_checks += 1
        return True


def review_geometry(value: Json) -> Object:
    document = read_geometry(value)
    diagnostics = Diagnostics()
    try:
        _review(document, diagnostics)
    except GEOSException as error:
        raise InvalidInput("geometry operation could not be resolved") from error
    included = [p for p in panel_poses(document) if p.included]
    return {
        "schema_version": 1,
        "geometry_sha256": digest(encode(value)),
        "checker": "roof_plane_layout_v1",
        "libraries": {
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
        "geometry_status": "incomplete"
        if not diagnostics.complete
        else "conflicts_detected"
        if diagnostics.conflict_count
        else "no_conflicts_detected",
        "engineering_status": "not_evaluated",
        "review_complete": diagnostics.complete,
        "diagnostics_truncated": diagnostics.issue_count > len(diagnostics.issues),
        "issue_count": diagnostics.issue_count,
        "conflict_count": diagnostics.conflict_count,
        "candidate_checks": diagnostics.candidate_checks,
        "limits": {
            "max_diagnostics": MAX_DIAGNOSTICS,
            "max_candidate_checks": MAX_CANDIDATE_CHECKS,
        },
        "module_count": len(included),
        "declared_stc_kwp": math.fsum(p.stc_power_w for p in included) / 1000,
        "issues": diagnostics.issues,
    }


def _polygon(
    boundary: list[list[float]], holes: list[list[list[float]]] | None = None
) -> Polygon | None:
    polygon = Polygon(boundary, holes)
    # Never repair, snap or buffer(0) a user shape into another design.
    if (
        not polygon.is_valid
        or polygon.is_empty
        or not math.isfinite(polygon.area)
        or polygon.area <= 0
    ):
        return None
    return polygon


def _review(document: GeometryDocument, result: Diagnostics) -> None:
    poses = panel_poses(document)
    rules = {r.roof_id: r for r in document.layout_rules}
    coordinate = document.coordinate_system
    if coordinate.north_reference == "unreferenced":
        result.add(
            "north_reference_unspecified", "coordinate_system", None, missing=True
        )
    for source in document.sources:
        if source.spatial_precision_m is None:
            result.add("source_precision_unspecified", source.id, None, missing=True)
    for roof in document.roofs:
        shape = _polygon(roof.boundary_uv, roof.holes_uv)
        if shape is None:
            result.add("invalid_roof_polygon", roof.id, roof.id)
            continue
        rule = rules.get(roof.id)
        edge = rule.edge_clearance_m if rule else None
        clearance = rule.obstacle_clearance_m if rule else None
        if edge is None:
            result.add("edge_clearance_unspecified", roof.id, roof.id, missing=True)
        if clearance is None:
            result.add("obstacle_clearance_unspecified", roof.id, roof.id, missing=True)
        openings = [Polygon(hole) for hole in roof.holes_uv]
        opening_tree = STRtree(openings)
        blockers: list[BaseGeometry] = []
        blocker_ids: list[str] = []
        blocker_kinds: list[str] = []
        for obstacle in document.obstacles:
            if obstacle.roof_id != roof.id:
                continue
            base = _polygon(obstacle.footprint_uv)
            if base is None:
                result.add("invalid_obstacle_polygon", obstacle.id, roof.id)
                continue
            if (
                dot(
                    cross(roof.u_axis_enu, roof.v_axis_enu), obstacle.extrusion_axis_enu
                )
                <= 0
            ):
                result.add("obstacle_not_above_roof", obstacle.id, roof.id)
            # Exact sweep of a potentially concave footprint, rather than
            # its convex hull (which would invent a blocker inside recesses).
            du, dv = roof_coordinates(
                roof,
                add(
                    on_roof(roof, 0, 0),
                    scale(obstacle.extrusion_axis_enu, obstacle.height_m),
                ),
            )
            swept: list[BaseGeometry] = [base, translate(base, xoff=du, yoff=dv)]
            ring = obstacle.footprint_uv
            for first, second in zip(ring, [*ring[1:], ring[0]], strict=True):
                side = Polygon(
                    [
                        first,
                        second,
                        [second[0] + du, second[1] + dv],
                        [first[0] + du, first[1] + dv],
                    ]
                )
                if side.area > 0:
                    swept.append(side)
            projected = unary_union(swept)
            if not shape.covers(base):
                result.add("obstacle_outside_roof", obstacle.id, roof.id)
            blockers.append(projected)
            blocker_ids.append(obstacle.id)
            blocker_kinds.append("obstacle")
        for keepout in document.keepouts:
            if keepout.roof_id != roof.id:
                continue
            area = _polygon(keepout.footprint_uv)
            if area is None:
                result.add("invalid_keepout_polygon", keepout.id, roof.id)
                continue
            blockers.append(area)
            blocker_ids.append(keepout.id)
            blocker_kinds.append("keepout")
        blocker_tree = STRtree(blockers)
        footprints: list[Polygon] = []
        panel_ids: list[str] = []
        for pose in poses:
            if pose.roof_id != roof.id or not pose.included:
                continue
            footprint = MultiPoint(
                [roof_coordinates(roof, point) for point in pose.corners()]
            ).convex_hull
            if (
                not isinstance(footprint, Polygon)
                or not footprint.is_valid
                or footprint.area <= 0
            ):
                result.add("invalid_panel_projection", pose.id, roof.id)
                continue
            footprints.append(footprint)
            panel_ids.append(pose.id)
            if not shape.covers(footprint):
                opening = False
                for candidate in sorted(opening_tree.query(footprint)):
                    if not result.candidate():
                        return
                    if footprint.intersection(openings[int(candidate)]).area > 0:
                        opening = True
                        break
                result.add(
                    "panel_over_opening" if opening else "panel_outside_roof",
                    pose.id,
                    roof.id,
                )
            elif edge is not None:
                distance = float(shape.boundary.distance(footprint))
                if distance < edge:
                    result.add(
                        "panel_edge_clearance",
                        pose.id,
                        roof.id,
                        required_m=edge,
                        actual_m=distance,
                    )
            # A bounding box selects candidates; actual Euclidean distance
            # below avoids approximate round-buffer clearance acceptance.
            distance = clearance or 0
            minx, miny, maxx, maxy = footprint.bounds
            search = box(
                minx - distance, miny - distance, maxx + distance, maxy + distance
            )
            for index in sorted(blocker_tree.query(search)):
                if not result.candidate():
                    return
                i = int(index)
                blocker, kind = blockers[i], blocker_kinds[i]
                if footprint.intersection(blocker).area > 0:
                    result.add(
                        "panel_projected_obstacle_overlap"
                        if kind == "obstacle"
                        else "panel_in_keepout",
                        pose.id,
                        roof.id,
                        related_id=blocker_ids[i],
                    )
                elif kind == "obstacle" and clearance is not None:
                    actual = float(footprint.distance(blocker))
                    if actual < clearance:
                        result.add(
                            "panel_obstacle_clearance",
                            pose.id,
                            roof.id,
                            related_id=blocker_ids[i],
                            required_m=clearance,
                            actual_m=actual,
                        )
        tree = STRtree(footprints)
        for index, footprint in enumerate(footprints):
            for candidate in sorted(tree.query(footprint)):
                other = int(candidate)
                if other <= index:
                    continue
                if not result.candidate():
                    return
                if footprint.intersection(footprints[other]).area > 0:
                    result.add(
                        "panel_projected_overlap",
                        panel_ids[index],
                        roof.id,
                        related_id=panel_ids[other],
                    )
