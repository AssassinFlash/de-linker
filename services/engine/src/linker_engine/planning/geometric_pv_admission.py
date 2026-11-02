"""Admit declared clear single-plane roofs to their isolated work budgets."""

from __future__ import annotations

from .canonical import Object
from .direct_beam_geometry import build_scene
from .direct_beam_index import DirectBeamIndex, PlaneClearance
from .errors import GeometricPvExpandedScopeRequired
from .geometric_pv_diffuse import diffuse_sample_upper_bound
from .geometric_pv_inputs import MODEL_V1, MODEL_V3, GeometricPvInputs
from .geometric_pv_limits import ClearFlatRoofLimits, GeometricPvLimits
from .geometry import read_geometry
from .pv_string_inputs import PvStringPlan
from .pv_weather import WeatherSeries


def admitted_limits(
    inputs: Object,
    weather: WeatherSeries,
    request: GeometricPvInputs,
    ordinary: GeometricPvLimits,
    expanded: ClearFlatRoofLimits,
    *,
    pitched: bool = False,
) -> GeometricPvLimits:
    """Select a budget from saved inputs; never infer clearance from a near-zero slope."""
    geometry = read_geometry(inputs.get("geometry"))
    modules = sum(
        array.rows * array.columns - len(array.excluded_slots)
        for array in geometry.arrays
    )
    rows = len(weather.points)
    coarse = request.sampling.coarse_cells_per_edge
    fine = request.sampling.fine_cells_per_edge
    steps = modules * rows
    samples = steps * (coarse**2 + fine**2)
    if request.model != MODEL_V1:
        samples += diffuse_sample_upper_bound(modules, fine)
    if steps <= ordinary.max_module_steps and samples <= ordinary.max_samples:
        return ordinary

    def refuse() -> None:
        raise GeometricPvExpandedScopeRequired(
            "geometric PV exceeds the configured clear roof scope"
        )

    if (
        request.model != MODEL_V3
        or coarse != 1
        or fine != 2
        or not 0 < modules <= expanded.max_modules
        or not 0 < rows <= expanded.max_weather_rows
        or steps > expanded.max_module_steps
        or samples > expanded.max_samples
        or len(geometry.roofs) != 1
        or len(geometry.arrays) != 1
        or len(geometry.module_specs) != 1
        or geometry.obstacles
        or geometry.keepouts
        or len(geometry.layout_rules) > 1
        or inputs.get("equipment_plant") is not None
        or inputs.get("pv_plant_string_plan") is not None
        or len(request.parameters.converters) != 1
        or len(request.parameters.arrays) != 1
    ):
        refuse()
    roof, array, spec = geometry.roofs[0], geometry.arrays[0], geometry.module_specs[0]
    if (
        len(roof.boundary_uv) != 4
        or roof.holes_uv
        or (not pitched and (roof.u_axis_enu[2] != 0 or roof.v_axis_enu[2] != 0))
        or (pitched and roof.u_axis_enu[2] == 0 and roof.v_axis_enu[2] == 0)
        or max(p[0] for p in roof.boundary_uv) - min(p[0] for p in roof.boundary_uv)
        > 40
        or max(p[1] for p in roof.boundary_uv) - min(p[1] for p in roof.boundary_uv)
        > 40
        or array.mount_tilt_deg != 0
        or array.rows > 8
        or array.columns > 12
        or array.column_gap_m < 0.2
        or array.row_gap_m < 0.4
        or array.lower_edge_clearance_m < 0.1
        or spec.width_m > 1.134
        or spec.length_m > 1.762
        or spec.thickness_m > 0.03
    ):
        refuse()
    plan = PvStringPlan.read(inputs.get("pv_string_plan"))
    if not 0 < len(plan.strings) <= expanded.max_strings or any(
        len(string.module_ids) > 16 for string in plan.strings
    ):
        refuse()
    if any(
        (p.interval.end - p.interval.start).total_seconds() != 3600
        for p in weather.points
    ) or any(
        a.interval.end != b.interval.start
        for a, b in zip(weather.points, weather.points[1:], strict=False)
    ):
        refuse()

    scene = build_scene(inputs.get("geometry"))
    if len(scene.receivers) != modules:
        refuse()
    if pitched:
        first = scene.receivers[0]
        frame = (first.u, first.v, first.normal)
        if (
            first.normal[2] < 0.5
            or len(scene.opaque) != modules + 1
            or any((r.u, r.v, r.normal) != frame for r in scene.receivers)
        ):
            refuse()
        plane = PlaneClearance.from_scene(scene, frame)
        if plane is None:
            refuse()
        assert plane is not None
        for receiver in scene.receivers:
            points = tuple(
                receiver.midpoint(x, y, count)
                for count in (coarse, fine)
                for y in range(count)
                for x in range(count)
            )
            if (
                plane.threshold(receiver.id, points, on_bounds_check=lambda: None)
                is None
            ):
                refuse()
        return GeometricPvLimits.read(
            {
                **ordinary.model_dump(mode="json"),
                "max_module_steps": expanded.max_module_steps,
                "max_samples": expanded.max_samples,
            }
        )

    # Check the flat-roof contract on actual built scene as well as inputs.
    top = scene.receivers[0].centre[2]
    if len(scene.opaque) != modules + 1 or any(
        r.normal != (0.0, 0.0, 1.0) or r.centre[2] != top for r in scene.receivers
    ):
        refuse()
    index = DirectBeamIndex.from_scene(scene, leaf_size=ordinary.index_leaf_size)
    for receiver in scene.receivers:
        points = tuple(
            receiver.midpoint(x, y, count)
            for count in (coarse, fine)
            for y in range(count)
            for x in range(count)
        )
        if index.upward_clearance(receiver.id, points) is None:
            refuse()
    return GeometricPvLimits.read(
        {
            **ordinary.model_dump(mode="json"),
            "max_module_steps": expanded.max_module_steps,
            "max_samples": expanded.max_samples,
        }
    )
