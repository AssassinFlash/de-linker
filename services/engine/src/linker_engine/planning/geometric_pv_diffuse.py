"""Static cosine-weighted visibility for pinned Perez diffuse components.

`pvlib.irradiance.perez(..., return_components=True)` in the pinned 0.16.1
build returns isotropic, circumsolar and horizon plane irradiances. The horizon
term is ``F2 * sind(surface_tilt)``; that function has no finite horizon-band
width, so the horizon factor is the front-facing horizon ring. Circumsolar
uses the hourly direct-beam fraction. Isotropic sky and ground are sampled
once per module from the front hemisphere. A ray with no positive cosine on
the module normal is not a front contribution, so ground light does not
illuminate the module back. An empty front domain is not occlusion: the
pinned transposition already carries that view factor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .direct_beam_geometry import Receiver, Scene, plus, scalar, times, unit
from .direct_beam_index import DirectBeamIndex
from .direct_beam_inputs import DirectBeamSampling
from .direct_beam_visibility import VisibilityBudget, blocked_ids
from .errors import InvalidInput
from .geometry import Vector

# One azimuth sample per quadrant of each declared edge cell. The same count
# steps the horizon ring, so both domains use the request's fine grid rather
# than a second hidden resolution.
_AZIMUTH_QUADRANTS = 4


def diffuse_direction_count(fine_cells_per_edge: int) -> int:
    """Upper bound on traced directions for one module, before the panel grid."""
    return fine_cells_per_edge * (_AZIMUTH_QUADRANTS * fine_cells_per_edge) + (
        _AZIMUTH_QUADRANTS * fine_cells_per_edge
    )


def diffuse_sample_upper_bound(modules: int, fine_cells_per_edge: int) -> int:
    """Panel-midpoint rays the diffuse pass may spend. Night hours are absent.

    Rejected back-facing directions are not traced. The bound still counts
    them, matching the direct-beam admission rule that includes unsampled night
    rows rather than the rays a particular orientation happens to cast.
    """
    return (
        modules * fine_cells_per_edge**2 * diffuse_direction_count(fine_cells_per_edge)
    )


def front_component(direction: Vector, normal: Vector) -> str | None:
    """Front-face Perez domain of one unit direction, or None on the back.

    Downward world rays are ground only when they meet the module front.
    A downward ray into the back is rejected and cannot add ground irradiance.
    """
    if scalar(normal, direction) <= 0:
        return None
    if direction[2] < 0:
        return "ground"
    if direction[2] == 0:
        return "horizon"
    return "isotropic"


@dataclass(frozen=True)
class ModuleDiffuseVisibility:
    isotropic: float
    horizon: float
    ground: float
    blocked_samples: int
    accepted_directions: dict[str, int]


def _hemisphere(receiver: Receiver, edge: int) -> list[tuple[Vector, float, str]]:
    rays: list[tuple[Vector, float, str]] = []
    azimuths = _AZIMUTH_QUADRANTS * edge
    # ξ = sin²θ makes cosθ sinθ dθ uniform. Weight Δξ Δφ / 2 sums to π over
    # the front hemisphere, the projected solid angle of an unobstructed dome.
    weight = (1 / edge) * (math.tau / azimuths) / 2
    for step in range(edge):
        xi = (step + 0.5) / edge
        theta = math.asin(math.sqrt(xi))
        sin_t, cos_t = math.sin(theta), math.cos(theta)
        for turn in range(azimuths):
            phi = (turn + 0.5) / azimuths * math.tau
            direction = unit(
                plus(
                    plus(
                        times(receiver.u, sin_t * math.cos(phi)),
                        times(receiver.v, sin_t * math.sin(phi)),
                    ),
                    times(receiver.normal, cos_t),
                )
            )
            kind = front_component(direction, receiver.normal)
            if kind is None:
                continue
            rays.append((direction, weight, kind))
    return rays


def _horizon(receiver: Receiver, edge: int) -> list[tuple[Vector, float]]:
    count = _AZIMUTH_QUADRANTS * edge
    rays: list[tuple[Vector, float]] = []
    for turn in range(count):
        psi = (turn + 0.5) / count * math.tau
        direction = (math.cos(psi), math.sin(psi), 0.0)
        cosine = scalar(receiver.normal, direction)
        if cosine <= 0:
            continue
        rays.append((direction, cosine))
    return rays


def _panel_fraction(
    scene: Scene,
    receiver: Receiver,
    direction: Vector,
    cells: int,
    budget: VisibilityBudget,
    index: DirectBeamIndex,
) -> tuple[float, int]:
    visible = 0
    blocked = 0
    for y in range(cells):
        for x in range(cells):
            budget.sample()
            point = receiver.midpoint(x, y, cells)
            if blocked_ids(scene, receiver, point, direction, budget, index):
                blocked += 1
            else:
                visible += 1
    return visible / (cells * cells), blocked


def _factor(visible: list[float], total: list[float]) -> float:
    if not total:
        return 1.0
    seen, whole = math.fsum(visible), math.fsum(total)
    if seen == whole:
        return 1.0
    if whole <= 0 or not math.isfinite(seen) or seen < 0 or seen > whole:
        raise InvalidInput("diffuse visibility weights are not a fraction")
    return seen / whole


def module_diffuse_visibility(
    scene: Scene,
    receiver: Receiver,
    sampling: DirectBeamSampling,
    budget: VisibilityBudget,
    index: DirectBeamIndex,
) -> ModuleDiffuseVisibility:
    """One module's static sky, horizon-ring and ground fractions.

    The result is independent of the weather row. Circumsolar is not sampled
    here; it reuses the hourly direct-beam fraction.
    """
    cells = sampling.fine_cells_per_edge
    grouped: dict[str, list[tuple[Vector, float]]] = {
        "isotropic": [],
        "horizon": [],
        "ground": [],
    }
    for direction, weight, kind in _hemisphere(receiver, cells):
        grouped[kind].append((direction, weight))
    grouped["horizon"].extend(_horizon(receiver, cells))
    factors: dict[str, float] = {}
    blocked = 0
    accepted = {kind: len(rays) for kind, rays in grouped.items()}
    for kind, rays in grouped.items():
        visible_weights: list[float] = []
        total_weights: list[float] = []
        for direction, weight in rays:
            fraction, hits = _panel_fraction(
                scene, receiver, direction, cells, budget, index
            )
            blocked += hits
            visible_weights.append(weight * fraction)
            total_weights.append(weight)
        factors[kind] = _factor(visible_weights, total_weights)
    return ModuleDiffuseVisibility(
        factors["isotropic"],
        factors["horizon"],
        factors["ground"],
        blocked,
        accepted,
    )
