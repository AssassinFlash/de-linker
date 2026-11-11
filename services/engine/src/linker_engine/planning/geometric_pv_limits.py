"""Explicit work envelopes; every ceiling is a measured deployment bound."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field

from .energy_inputs import Document
from .geometry_documents import PositiveInteger

# Largest measured declared roof: 96 modules over a complete 8,760-interval
# retained year is 840,960 module steps. The four corners of the isolated
# cgroup envelope measured on that scene are 141-238 s wall clock, 1.07-1.12 GB
# peak RSS and 2.15 M sampled rays
# (docs/acceptance/2026-11-11/direct-beam-production-admission.md).
MEASURED_MAX_MODULE_STEPS = 841_000
# 840,960 module steps at the 1 x 2 grid the planner requests, plus the Perez
# diffuse upper bound, is exactly 4,214,016 sampled rays.
MEASURED_MAX_SAMPLES = 4_300_000
# Rays against declared opaque volumes are not proportional to sample count: the
# same 96-module year cost 176,128 bounds checks on a clear roof and 60,985,910
# with twelve walls between the modules and the sun. Measured throughput is
# ~250,000 bounds checks per second on the reference host, so this ceiling keeps
# a single task inside the isolated 600 s envelope (61 M is the worst legal scene
# seen, at 238 s) while a pathological scene still fails closed instead of
# running unbounded. `direct_beam_visibility.bounds_allowance` gives a legal roof
# its own scene-priced allowance below this ceiling.
MEASURED_MAX_BOUNDS_CHECKS = 100_000_000
# Exact face intersections measured 2,443,230 on that occluded 96-module year.
MEASURED_MAX_RAY_FACE_CHECKS = 20_000_000
MEASURED_MAX_MODULES = 96
MEASURED_MAX_STRINGS = 6
MEASURED_MAX_WEATHER_ROWS = 8_760


@dataclass(frozen=True)
class VisibilityRayLimits:
    """Only the ray budgets the full-axis model spends.

    The diagnostic direct-beam task also caps how many source rows may be
    selected; this model selects every retained row and has no such choice, so
    it does not carry that policy under another name.
    """

    max_samples: int
    max_ray_face_checks: int
    max_bounds_checks: int


class GeometricPvLimits(Document):
    """Deployment work budgets, not accuracy claims or manufacturer limits.

    The ceilings keep an operator setting inside the measured host envelope;
    they are not defaults and they do not describe a physical tolerance.
    """

    max_module_steps: Annotated[
        int, Field(strict=True, gt=0, le=MEASURED_MAX_MODULE_STEPS)
    ]
    max_samples: Annotated[int, Field(strict=True, gt=0, le=MEASURED_MAX_SAMPLES)]
    max_ray_face_checks: Annotated[
        int, Field(strict=True, gt=0, le=MEASURED_MAX_RAY_FACE_CHECKS)
    ]
    max_bounds_checks: Annotated[
        int, Field(strict=True, gt=0, le=MEASURED_MAX_BOUNDS_CHECKS)
    ]
    index_leaf_size: PositiveInteger

    def visibility_ray_limits(self) -> VisibilityRayLimits:
        return VisibilityRayLimits(
            max_samples=self.max_samples,
            max_ray_face_checks=self.max_ray_face_checks,
            max_bounds_checks=self.max_bounds_checks,
        )


class ClearFlatRoofLimits(Document):
    """Optional envelope bounded by the measured 96-module host workload."""

    max_module_steps: Annotated[
        int, Field(strict=True, gt=0, le=MEASURED_MAX_MODULE_STEPS)
    ]
    max_samples: Annotated[int, Field(strict=True, gt=0, le=MEASURED_MAX_SAMPLES)]
    max_modules: Annotated[int, Field(strict=True, gt=0, le=MEASURED_MAX_MODULES)]
    max_strings: Annotated[int, Field(strict=True, gt=0, le=MEASURED_MAX_STRINGS)]
    max_weather_rows: Annotated[
        int, Field(strict=True, gt=0, le=MEASURED_MAX_WEATHER_ROWS)
    ]


class ClearPitchedRoofLimits(ClearFlatRoofLimits):
    """Opt-in isolated budget, separately enabled from the flat-roof profile."""
