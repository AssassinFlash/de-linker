"""One frozen Woo pool, compiled lazily and shared across a finite search."""

from __future__ import annotations

from typing import Any, cast

from ..compatibility import Compatibility
from .canonical import Object
from .equipment_facts import compile_product
from .errors import InvalidInput


class EquipmentEvidence:
    def __init__(self, basis: Object) -> None:
        self.basis = basis
        self.rows = cast(list[dict[str, Any]], basis["products"])
        self.products = {row["canonical_product_id"]: row for row in self.rows}
        self.contract = Compatibility(cast(dict[str, Any], basis["compatibility"]))
        self._compiled: dict[int, Object] = {}

    def compiled(self, product_id: int) -> Object:
        if product_id not in self._compiled:
            self._compiled[product_id] = compile_product(self.products[product_id])
        return self._compiled[product_id]

    def scalar(self, product_id: int, key: str, quantity: str) -> float | None:
        fact = cast(dict[str, Any], self.compiled(product_id)["facts"]).get(key)
        if (
            fact
            and fact["status"] == "typed"
            and fact["shape"] == "scalar"
            and fact["quantity"] == quantity
        ):
            return float(fact["value"])
        return None

    def sales_unit(self, product_id: int) -> str | None:
        fact = cast(dict[str, Any], self.compiled(product_id)["facts"]).get(
            "sales_unit_kind"
        )
        if fact and fact["source"] and not fact["qualifier"]:
            value = fact["raw_value"]
            return value if isinstance(value, str) else None
        return None

    def require_basis(self, basis: Object) -> None:
        # Only the enclosing worker owns this in-memory projection. Reusing it
        # with another source object would mix independently frozen inputs.
        if basis is not self.basis:
            raise InvalidInput("equipment evidence belongs to another frozen pool")
