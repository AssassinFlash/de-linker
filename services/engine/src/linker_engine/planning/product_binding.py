"""A saved reference to Woo-owned product facts, never a product editor."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from .energy_inputs import Document


class WooReference(Document):
    # Same exact-integer browser transport bound as the geometry contracts.
    product_id: Annotated[int, Field(strict=True, gt=0, le=2**53 - 1)]
    product_revision: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    reference_input_id: Annotated[str, Field(min_length=1, max_length=128)]
