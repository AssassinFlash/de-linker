"""Project a current Woo sales unit and its documented fixed internal count."""

from __future__ import annotations

from typing import cast

from .canonical import Json, Object


def battery_assembly(compiled: Object) -> Object | None:
    facts = cast(dict[str, Object], compiled["facts"])
    sales = facts.get("sales_unit_kind")
    if not sales or not sales.get("source") or sales.get("qualifier"):
        return None
    kind = sales.get("raw_value")
    if kind not in ("battery_module", "battery_system", "integrated_system"):
        return None
    fixed: int | None = None
    used = [sales]
    minimum = facts.get("modules_per_stack_min")
    maximum = facts.get("modules_per_stack_max")
    if kind == "battery_system" and minimum and maximum:
        if all(
            f.get("status") == "typed"
            and f.get("shape") == "scalar"
            and f.get("quantity") == "count"
            and f.get("source")
            and type(f.get("value")) in (int, float)
            for f in (minimum, maximum)
        ):
            count = cast(float, minimum["value"])
            if (
                count == maximum["value"]
                and float(count).is_integer()
                and 0 < count <= 9007199254740991
            ):
                fixed = int(count)
                used += [minimum, maximum]
    documents: list[Json] = []
    for fact in used:
        source = cast(Object, fact["source"])
        document: Object = {"url": source["url"], "page": source["page"]}
        if document not in documents:
            documents.append(document)
    return {
        "sales_unit_kind": kind,
        "fixed_modules_per_stack": fixed,
        "documents": documents,
    }
