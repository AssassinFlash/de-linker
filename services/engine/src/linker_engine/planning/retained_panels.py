"""Project views of retired catalog panel references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

from .canonical import Json, Object
from .declared_module import panel_label

RETAINED_NOTE = "declared_reference — Parameters retained from an earlier design."


@dataclass(frozen=True)
class RetainedPanel:
    id: str
    label: str
    model: str
    url: str
    reference: str
    document_sha256: str

    @property
    def source(self) -> Object:
        return {
            "kind": "user_declared",
            "note": RETAINED_NOTE,
            "url": None,
            "page": None,
            "document_sha256": None,
        }


def project_panels(inputs: Object) -> list[RetainedPanel]:
    geometry = inputs.get("geometry")
    if not isinstance(geometry, dict):
        return []
    panels = []
    for spec in cast(list[dict[str, Any]], geometry.get("module_specs", [])):
        source = spec["source"]
        woo = source.get("woo")
        if isinstance(woo, dict):
            panels.append(
                RetainedPanel(
                    spec["id"],
                    panel_label(spec["stc_power_w"], spec["length_m"], spec["width_m"]),
                    spec["model"],
                    source.get("url") or "",
                    woo["reference_input_id"],
                    source.get("document_sha256") or "",
                )
            )
    return panels


def _coefficient(inputs: Object, identifier: str) -> Json:
    solar = inputs.get("solar_setup")
    geometric = inputs.get("geometric_pv_preparation")
    values = set()
    for parameters in (
        inputs.get("pv_generation"),
        solar.get("pv") if isinstance(solar, dict) else None,
        geometric.get("parameters") if isinstance(geometric, dict) else None,
    ):
        if isinstance(parameters, dict):
            for module in cast(list[dict[str, Any]], parameters.get("modules", [])):
                if (
                    module["module_spec_id"] == identifier
                    and module.get("gamma_pdc_per_c") is not None
                ):
                    values.add(module["gamma_pdc_per_c"])
    if len(values) > 1:
        raise ValueError(
            "conflicting retained temperature coefficients for " + identifier
        )
    return next(iter(values), None)


def _display_text(text: str, panels: list[RetainedPanel]) -> str:
    for panel in panels:
        if panel.document_sha256:
            text = re.sub(
                r";? " + re.escape(panel.document_sha256) + r" / p\. \d+", "", text
            )
        for old in (panel.model, panel.reference, panel.url):
            if old:
                text = re.sub(re.escape(old), panel.label, text, flags=re.IGNORECASE)
        # Retained analysis notes also used the maker's short name.
        brand = panel.model.split()[0]
        text = re.sub(
            r"\b(?:current Woo-maintained |Woo-maintained )?"
            + re.escape(brand)
            + r"(?: Solar)?(?: module evidence)?\b",
            panel.label,
            text,
            flags=re.IGNORECASE,
        )
    return text


def display_document(
    document: Object, panels: list[RetainedPanel], *, inputs: bool = False
) -> Object:
    if not panels:
        return document
    by_ref = {p.reference: p for p in panels}
    by_model = {p.model: p for p in panels}

    def visit(value: Json, key: str = "") -> Json:
        if isinstance(value, list):
            return [
                visit(item, key)
                for item in value
                if not (
                    key == "rows"
                    and isinstance(item, dict)
                    and item.get("href") in {p.url for p in panels if p.url}
                )
            ]
        if isinstance(value, str):
            if not inputs or key in ("source_note", "model"):
                return _display_text(value, panels)
            return value
        if not isinstance(value, dict):
            return value
        binding = value.get("woo")
        if (
            isinstance(binding, dict)
            and str(binding.get("reference_input_id")) in by_ref
        ):
            return by_ref[str(binding["reference_input_id"])].source
        if key == "pv_module_inputs" or key == "woo_module_inputs":
            if isinstance(value.get("module"), dict):
                return {"schema_version": 1, "kind": "project_panel_parameters"}
        if value.get("kind") == "pv_module" and str(value.get("id")) in by_ref:
            return {"kind": "project_panel_parameters"}
        if (
            value.get("handling") == "pv_reference"
            and str(value.get("model")) in by_model
        ):
            panel = by_model[str(value["model"])]
            return {
                **value,
                "id": "pv:" + panel.id,
                "product_id": None,
                "model": panel.label,
                "source": {"kind": "design_parameters", "basis": "saved_project"},
            }
        result = {k: visit(v, k) for k, v in value.items()}
        if value.get("href") in {p.url for p in panels if p.url}:
            result["href"] = None
        return result

    result = cast(Object, visit(document))
    if inputs:
        geometry = result.get("geometry")
        if isinstance(geometry, dict):
            by_id = {panel.id: panel for panel in panels}
            for spec in cast(list[Object], geometry["module_specs"]):
                if spec["id"] in by_id:
                    gamma = _coefficient(document, str(spec["id"]))
                    if gamma is not None and spec.get("gamma_pdc_per_c") is None:
                        spec["gamma_pdc_per_c"] = gamma
    return result
