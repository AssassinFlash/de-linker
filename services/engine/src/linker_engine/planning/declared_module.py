"""A roof module the customer will supply, declared instead of published.

Linker sells energy storage, not PV modules, so a roof layout may use a generic
size/power tier rather than a Woo-maintained reference component. Such a module
is a planning assumption: it carries its own temperature coefficient under a
stable note marker and has no product, revision, document or manufacturer
claim. Nothing here may turn it into a product fact.
"""

from __future__ import annotations

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
    """Refuse a tier that cannot carry its own unshaded PV reference model.

    Geometry already bounds the positive dimensions, thickness and STC power.
    The coefficient is the one number the PVWatts model reads from the module
    when no published product supplies it, so an absent or non-negative value
    is refused instead of silently borrowing the Woo reference figure.
    """
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
    if coefficient is None:
        raise InvalidInput(
            "declared_module_gamma_missing: a declared reference needs its own gamma_pdc_per_c"
        )
    # PVWatts expects the fractional relative change per degree, which is
    # negative for every crystalline module; zero or positive would overstate
    # output rather than describe the assumption.
    if not coefficient < 0:
        raise InvalidInput(
            "declared_module_gamma_invalid: gamma_pdc_per_c must be a negative fraction"
        )


def declared_module_basis(module: ModuleSpec) -> PvModuleParameters:
    """The module's own declared parameters, never the published reference."""
    check_declared_module(module)
    assert module.gamma_pdc_per_c is not None
    return PvModuleParameters(
        module_spec_id=module.id,
        gamma_pdc_per_c=module.gamma_pdc_per_c,
        source=module.source,
    )
