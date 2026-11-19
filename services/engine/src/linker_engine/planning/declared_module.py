"""Project-supplied solar panel dimensions, ratings and calculation inputs."""

from __future__ import annotations

from .canonical import Object
from .errors import InvalidInput
from .geometry_documents import ModuleSpec
from .pv_parameters import PvModuleParameters

# A declared tier's note starts with this marker. It is deliberately not a
# product identifier and never appears in a Woo publication.
DECLARED_REFERENCE_PREFIX = "declared_reference"


def is_declared_reference(module: ModuleSpec) -> bool:
    """Whether this roof module is a declared planning reference, not a product."""
    return module.source.woo is None and module.source.note.startswith(
        DECLARED_REFERENCE_PREFIX
    )


def check_declared_module(module: ModuleSpec) -> None:
    """Validate the declared layout identity. Thermal calculations also need gamma."""
    if module.source.woo is not None:
        raise InvalidInput("declared_module_woo_bound: a product module is not a tier")
    if not is_declared_reference(module):
        raise InvalidInput(
            "declared_module_marker_missing: a non-Woo roof module needs a note starting with declared_reference"
        )
    if module.source.kind != "user_declared":
        raise InvalidInput(
            "declared_module_source_kind: a declared reference is not a datasheet"
        )
    coefficient = module.gamma_pdc_per_c
    if coefficient is not None and coefficient >= 0:
        raise InvalidInput(
            "declared_module_gamma_invalid: gamma_pdc_per_c must be a negative fraction"
        )


def declared_module_basis(module: ModuleSpec) -> PvModuleParameters:
    """The module's own declared parameters, never the published reference."""
    check_declared_module(module)
    if module.gamma_pdc_per_c is None:
        raise InvalidInput(
            "declared_module_gamma_missing: supply the temperature coefficient for this calculation"
        )
    return PvModuleParameters(
        module_spec_id=module.id,
        gamma_pdc_per_c=module.gamma_pdc_per_c,
        source=module.source,
    )


def panel_label(power: float, length: float, width: float) -> str:
    """Language-independent project label from the recorded values."""
    return f"PV {power:g} Wp · {length * 1000:g} × {width * 1000:g} mm"


def electrical_facts(module: ModuleSpec) -> Object:
    if module.electrical is None:
        return {}
    facts: Object = {}
    source: Object = {"kind": "user_declared", "module_spec_id": module.id}
    for key, value in module.electrical.model_dump(exclude_none=True).items():
        if key == "cell_technology":
            facts[key] = {
                "status": "text_evidence",
                "raw_value": value,
                "source": source,
            }
            continue
        coefficient = key.endswith("_pct_per_c")
        facts[key] = {
            "status": "typed",
            "shape": "scalar",
            "raw_value": str(value),
            "quantity": "temperature_coefficient"
            if coefficient
            else "voltage"
            if key.endswith("_v")
            else "current",
            "value": value / 100 if coefficient else value,
            "raw_unit": "%/°C" if coefficient else "V" if key.endswith("_v") else "A",
            "source": source,
        }
    return facts
