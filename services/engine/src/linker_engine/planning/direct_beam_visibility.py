"""Equal-area midpoint visibility, not diffuse irradiance or electrical loss."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol, cast

from .canonical import Json, Object
from .direct_beam_geometry import ANGULAR_GUARD, Receiver, Scene, scalar
from .direct_beam_index import DirectBeamIndex, PlaneClearance
from .direct_beam_inputs import DirectBeamLimits, DirectBeamSampling
from .errors import InvalidInput, NumericalFailure
from .geometry import Vector


class VisibilityLimits(Protocol):
    """The three CPU budgets this ray work actually spends.

    A caller that runs the same ray work over a different admission rule (the
    full-axis geometric model uses every retained row) can supply exactly these
    limits rather than an unrelated selected-row policy it does not enforce.
    """

    @property
    def max_samples(self) -> int: ...

    @property
    def max_ray_face_checks(self) -> int: ...

    @property
    def max_bounds_checks(self) -> int: ...


@dataclass
class VisibilityBudget:
    limits: VisibilityLimits
    samples: int = 0
    ray_face_checks: int = 0
    bounds_checks: int = 0

    def sample(self) -> None:
        if self.samples >= self.limits.max_samples:
            raise InvalidInput("direct-beam sample resource budget exhausted")
        self.samples += 1

    def samples_clear(self, count: int) -> None:
        """Charge every sample whose result was proved by a common bound."""
        if count < 0 or self.samples + count > self.limits.max_samples:
            raise InvalidInput("direct-beam sample resource budget exhausted")
        self.samples += count

    def face(self) -> None:
        if self.ray_face_checks >= self.limits.max_ray_face_checks:
            raise InvalidInput("direct-beam ray resource budget exhausted")
        self.ray_face_checks += 1

    def bounds(self) -> None:
        if self.bounds_checks >= self.limits.max_bounds_checks:
            raise InvalidInput("direct-beam bounds resource budget exhausted")
        self.bounds_checks += 1


def blocked_ids(
    scene: Scene,
    receiver: Receiver,
    point: Vector,
    direction: Vector,
    budget: VisibilityBudget,
    index: DirectBeamIndex,
) -> set[str]:
    """Opaque ids hit by one ray. The receiver module itself is exempt."""
    blockers: set[str] = set()
    candidates = index.query(point, direction, on_bounds_check=budget.bounds)
    for item in candidates.opaque:
        # Only this receiver module, never its supporting roof or an
        # entire array/group, is exempt from ray intersections.
        if item.kind == "module_volume" and item.id == receiver.id:
            continue
        if item.contains_receiver(point, scene.epsilon_m):
            raise NumericalFailure("receiver intersects a declared opaque volume")
        for face in item.faces:
            budget.face()
            if face.ray_hit(point, direction, scene.epsilon_m):
                blockers.add(item.id)
    return blockers


def _grid(
    scene: Scene,
    receiver: Receiver,
    direction: Vector,
    count: int,
    budget: VisibilityBudget,
    index: DirectBeamIndex,
) -> Object:
    visible = 0
    blocked_by: dict[str, int] = {}
    for y in range(count):
        for x in range(count):
            budget.sample()
            point = receiver.midpoint(x, y, count)
            blockers = blocked_ids(scene, receiver, point, direction, budget, index)
            if not blockers:
                visible += 1
            for blocker in blockers:
                blocked_by[blocker] = blocked_by.get(blocker, 0) + 1
    return {
        "cells_per_edge": count,
        "sample_count": count * count,
        "visible_sample_count": visible,
        "visible_fraction": visible / (count * count),
        # Overlapping occluders can count the same blocked sample. Fractions
        # use the union; these counts must not be summed into a loss fraction.
        "blocker_sample_counts": {key: blocked_by[key] for key in sorted(blocked_by)},
    }


def visibility_row(
    scene: Scene,
    direction: Vector,
    sampling: DirectBeamSampling,
    budget: VisibilityBudget,
    *,
    index: DirectBeamIndex,
    upward_clearances: dict[str, float] | None = None,
    plane_clearances: dict[str, tuple[PlaneClearance, float]] | None = None,
) -> Object:
    if (
        any(not math.isfinite(value) for value in direction)
        or abs(math.hypot(*direction) - 1) > ANGULAR_GUARD
    ):
        raise InvalidInput("finite unit ENU direction towards the sun required")
    rows: list[Json] = []
    for receiver in scene.receivers:
        incidence = scalar(receiver.normal, direction)
        status = (
            "night"
            if direction[2] <= 0
            else "back_facing_or_tangent"
            if incidence <= 0
            else "sampled"
        )
        if status == "sampled" and incidence <= ANGULAR_GUARD:
            raise NumericalFailure("near-tangent direct-beam incidence is unresolved")
        coarse = fine = None
        delta = None
        if status == "sampled":
            threshold = (upward_clearances or {}).get(receiver.id)
            plane = (plane_clearances or {}).get(receiver.id)
            if (threshold is not None and direction[2] > threshold) or (
                plane is not None and plane[0].clear(direction, plane[1])
            ):

                def clear_grid(count: int) -> Object:
                    samples = count * count
                    budget.samples_clear(samples)
                    return {
                        "cells_per_edge": count,
                        "sample_count": samples,
                        "visible_sample_count": samples,
                        "visible_fraction": 1.0,
                        "blocker_sample_counts": {},
                    }

                coarse = clear_grid(sampling.coarse_cells_per_edge)
                fine = clear_grid(sampling.fine_cells_per_edge)
            else:
                coarse = _grid(
                    scene,
                    receiver,
                    direction,
                    sampling.coarse_cells_per_edge,
                    budget,
                    index,
                )
                fine = _grid(
                    scene,
                    receiver,
                    direction,
                    sampling.fine_cells_per_edge,
                    budget,
                    index,
                )
            # Same finite sample domain, not a certified error estimate/bound.
            delta = abs(
                cast(float, fine["visible_fraction"])
                - cast(float, coarse["visible_fraction"])
            )
        rows.append(
            {
                "module_id": receiver.id,
                "array_id": receiver.array_id,
                "roof_id": receiver.roof_id,
                "status": status,
                "coarse": coarse,
                "fine": fine,
                "observed_absolute_delta": delta,
            }
        )
    return {"modules": rows}


def geometric_visibility(
    scene: Scene,
    direction: Vector,
    sampling: DirectBeamSampling,
    limits: DirectBeamLimits,
) -> Object:
    """One declared sun direction; useful independently of any weather/model call."""
    budget = VisibilityBudget(limits)
    index = DirectBeamIndex.from_scene(scene, leaf_size=limits.index_leaf_size)
    result = visibility_row(scene, direction, sampling, budget, index=index)
    return {
        **result,
        "sample_count": budget.samples,
        "ray_face_checks": budget.ray_face_checks,
        "bounds_checks": budget.bounds_checks,
    }
