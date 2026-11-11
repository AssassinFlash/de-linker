"""Admit a declared roof to the work budget its measured resources need.

Two decisions used to be one. A scene had to be small *and* a single clear array
to reach the isolated envelope, so a customer roof with two arrays or a chimney
was refused rather than priced. The budget now follows the measured cost of the
declared scene, and the isolated envelope accepts any declared roof its numeric
limits cover.
"""

from __future__ import annotations

from .canonical import Object
from .direct_beam_geometry import Scene, build_scene
from .errors import GeometricPvExpandedScopeRequired
from .geometric_pv_diffuse import diffuse_sample_upper_bound
from .geometric_pv_inputs import MODEL_V1, MODEL_V3, GeometricPvInputs
from .geometric_pv_limits import ClearFlatRoofLimits, GeometricPvLimits
from .geometry import read_geometry
from .pv_string_inputs import PvStringPlan
from .pv_weather import WeatherSeries

# A receiver whose normal is this close to vertical belongs to the horizontal
# class; the ray code carries the same magnitude of arithmetic guard.
HORIZONTAL_GUARD = 1e-12
# The pitched envelope samples a front-facing receiver frame; a near-vertical
# plane is not a mounted roof surface.
PITCHED_MIN_NORMAL_Z = 0.5


def scene_matches_class(scene: Scene, *, pitched: bool) -> bool:
    """The declared module planes belong to the envelope being selected.

    Class is a property of the declared surfaces, not of the roof or array
    count: one flat roof with three arrays and a parapet and one flat roof with
    a single clear array are the same arithmetic.
    """
    horizontal = [
        abs(receiver.normal[2] - 1) <= HORIZONTAL_GUARD for receiver in scene.receivers
    ]
    if pitched:
        return all(
            receiver.normal[2] >= PITCHED_MIN_NORMAL_Z for receiver in scene.receivers
        ) and not all(horizontal)
    return all(horizontal)


def work_samples(
    modules: int, rows: int, coarse: int, fine: int, *, diffuse: bool
) -> int:
    """The sampling upper bound the operator's counters price for this request."""
    samples = modules * rows * (coarse**2 + fine**2)
    return samples + (diffuse_sample_upper_bound(modules, fine) if diffuse else 0)


def admitted_limits(
    inputs: Object,
    weather: WeatherSeries,
    request: GeometricPvInputs,
    ordinary: GeometricPvLimits,
    expanded: ClearFlatRoofLimits,
    *,
    pitched: bool = False,
    scene: Scene | None = None,
) -> GeometricPvLimits:
    """Select a budget from the saved work, never from a preferred roof shape.

    The ordinary budget is the un-isolated worker's envelope. The isolated
    envelope covers the largest measured declared roof; reaching it requires
    work inside its numeric limits, module planes of the envelope's class and an
    hourly contiguous source. Roof count, array count, obstacles, keep-outs,
    panel dimensions and sampling grids no longer decide admission: the declared
    rays are what cost resources, and the operator's counters price them.
    """
    geometry = read_geometry(inputs.get("geometry"))
    modules = sum(
        array.rows * array.columns - len(array.excluded_slots)
        for array in geometry.arrays
    )
    rows = len(weather.points)
    coarse = request.sampling.coarse_cells_per_edge
    fine = request.sampling.fine_cells_per_edge
    steps = modules * rows
    samples = work_samples(
        modules, rows, coarse, fine, diffuse=request.model != MODEL_V1
    )
    if steps <= ordinary.max_module_steps and samples <= ordinary.max_samples:
        return ordinary

    def refuse() -> None:
        raise GeometricPvExpandedScopeRequired(
            "geometric PV exceeds the configured work envelope"
        )

    built = build_scene(inputs.get("geometry")) if scene is None else scene
    if (
        not 0 < modules <= expanded.max_modules
        or not 0 < rows <= expanded.max_weather_rows
        or steps > expanded.max_module_steps
        or samples > expanded.max_samples
        or not scene_matches_class(built, pitched=pitched)
    ):
        refuse()
    if request.model == MODEL_V3:
        # One selected inverter and one string per tracker are the series
        # scenario's own contract; the plant forms it cannot nest stay out.
        if (
            inputs.get("equipment_plant") is not None
            or inputs.get("pv_plant_string_plan") is not None
            or len(request.parameters.converters) != 1
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

    return GeometricPvLimits.read(
        {
            **ordinary.model_dump(mode="json"),
            "max_module_steps": expanded.max_module_steps,
            "max_samples": expanded.max_samples,
        }
    )
