"""An explicit execution budget, never an engineering search-space limit."""

from typing import Annotated

from pydantic import Field

from .energy_inputs import Document


class EquipmentSearchLimits(Document):
    work_budget: Annotated[int, Field(strict=True, gt=0)]
