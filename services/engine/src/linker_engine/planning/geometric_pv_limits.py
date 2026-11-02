"""Explicit work envelope for full-source geometric PV preparation."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field

from .energy_inputs import Document
from .geometry_documents import PositiveInteger


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
    """Deployment work budgets, not accuracy claims or manufacturer limits."""

    max_module_steps: PositiveInteger
    max_samples: PositiveInteger
    max_ray_face_checks: PositiveInteger
    max_bounds_checks: PositiveInteger
    index_leaf_size: PositiveInteger

    def visibility_ray_limits(self) -> VisibilityRayLimits:
        return VisibilityRayLimits(
            max_samples=self.max_samples,
            max_ray_face_checks=self.max_ray_face_checks,
            max_bounds_checks=self.max_bounds_checks,
        )


class ClearFlatRoofLimits(Document):
    """Optional envelope bounded by the measured 96-module host workload."""

    max_module_steps: Annotated[int, Field(strict=True, gt=0, le=841_000)]
    max_samples: Annotated[int, Field(strict=True, gt=0, le=4_300_000)]
    max_modules: Annotated[int, Field(strict=True, gt=0, le=96)]
    max_strings: Annotated[int, Field(strict=True, gt=0, le=6)]
    max_weather_rows: Annotated[int, Field(strict=True, gt=0, le=8_760)]


class ClearPitchedRoofLimits(ClearFlatRoofLimits):
    """Opt-in isolated budget, separately enabled from the flat-roof profile."""
