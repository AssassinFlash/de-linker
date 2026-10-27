"""Project the existing Woo reference figures into the planner's input units.

No defaults or product facts are maintained here. Every value comes from the
loaded, publication-checked reference. Unsupported/missing evidence remains an
explicit unavailable projection, without closing unrelated saleable products.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .canonical import Object, decode_object, encode
from .errors import VersionUnavailable
from .geometry_documents import ModuleSource, ModuleSpec
from .product_binding import WooReference
from .pv_parameters import PvModuleParameters


def module_template(raw: dict[str, Any]) -> Object:
    binding = WooReference(
        product_id=raw["canonical_product_id"],
        product_revision=raw["product_revision"],
        reference_input_id=raw["id"],
    )
    figures = raw["figures"]

    def figure(key: str, unit: str) -> dict[str, Any]:
        value = figures.get(key)
        if not isinstance(value, dict) or value.get("unit") != unit:
            raise VersionUnavailable(
                "Woo module figure or supported unit is missing: " + key
            )
        return value

    def source(value: dict[str, Any]) -> ModuleSource:
        citation = value["citation"]
        url = citation["url"]
        document = next(
            (d for d in raw["documents"] if url in [d["url"], *d.get("aliases", [])]),
            None,
        )
        if document is None:
            raise VersionUnavailable("Woo module document relationship is missing")
        return ModuleSource(
            kind="datasheet",
            note=raw["brand"] + " " + raw["model"],
            document_sha256=document.get("blob_sha256"),
            url=url,
            page=citation.get("page"),
            woo=binding,
        )

    def number(value: dict[str, Any]) -> float:
        try:
            result = float(Decimal(str(value["value"])))
            if not math.isfinite(result):
                raise ValueError
            return result
        except (InvalidOperation, ValueError, OverflowError) as error:
            raise VersionUnavailable(
                "Woo module requires an unambiguous numeric figure"
            ) from error

    dimensions = figure("dimensions_mm", "mm")
    parts = re.split(r"\s*[×x]\s*", str(dimensions["value"]).strip())
    if len(parts) != 3:
        raise VersionUnavailable("Woo module requires length, width and thickness")
    sides = [number({"value": side}) / 1000 for side in parts]
    power = figure("pmax_w", "W")
    # The current geometry contract has one citation for size and STC power.
    # Refuse an unsupported multi-document claim rather than invent a citation.
    if dimensions["citation"] != power["citation"]:
        raise VersionUnavailable("Woo module size and power need a common source page")
    specification = ModuleSpec(
        id="woo_" + str(raw["canonical_product_id"]),
        model=raw["brand"] + " " + raw["model"],
        length_m=sides[0],
        width_m=sides[1],
        thickness_m=sides[2],
        stc_power_w=number(power),
        source=source(dimensions),
    )
    coefficient = figure("gamma_pmax_pct_per_c", "%/°C")
    # Percent per degree -> fractional relative change per degree. The
    # convention is the existing PVWatts parameter contract, not an estimate.
    parameters = PvModuleParameters(
        module_spec_id=specification.id,
        gamma_pdc_per_c=number(coefficient) / 100,
        source=source(coefficient),
    )
    return decode_object(
        encode(
            {
                "specification": specification.model_dump(mode="json"),
                "parameters": parameters.model_dump(mode="json"),
            }
        )
    )
