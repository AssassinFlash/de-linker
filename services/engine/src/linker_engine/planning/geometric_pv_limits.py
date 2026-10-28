"""Explicit work envelope for full-source geometric PV preparation."""

from .direct_beam_inputs import DirectBeamLimits
from .energy_inputs import Document
from .geometry_documents import PositiveInteger


class GeometricPvLimits(Document):
    """Deployment work budgets, not accuracy claims or manufacturer limits."""

    max_module_steps: PositiveInteger
    max_samples: PositiveInteger
    max_ray_face_checks: PositiveInteger
    max_bounds_checks: PositiveInteger
    index_leaf_size: PositiveInteger

    def visibility_limits(self, max_weather_rows: int) -> DirectBeamLimits:
        return DirectBeamLimits(
            max_selected_rows=max_weather_rows,
            **self.model_dump(exclude={"max_module_steps"}),
        )
