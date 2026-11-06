"""Declared planning references open roof layout and PV generation together.

Linker does not sell PV modules. The roof may therefore rest on a generic
size/power tier the visitor picked, while a Woo-selected module keeps its
existing identity and document checks. These tests hold both paths at once and
show that a mixed roof judges each module against its own basis.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.declared_module import (
    DECLARED_REFERENCE_PREFIX,
    declared_module_basis,
    is_declared_reference,
)
from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.product_sources import ProductSources

from .conftest import FixtureObject, json_object
from .export_preparation_fixture import frozen_publication, product_sources
from .test_pv_generation import geometry as fixture_geometry
from .test_pv_generation import parameter_document

ROOT = Path(__file__).resolve().parents[4]

TIER_SOURCE_NOTE = (
    DECLARED_REFERENCE_PREFIX
    + " — Generic tier planning reference; unverified planning assumption, "
    "not a manufacturer datasheet value. Customer-supplied modules, not a "
    "Linker product."
)


def tier_spec(
    identifier: str = "module_tier", *, gamma: float | None = -0.0034
) -> Object:
    """The exact record `apps/planner`'s moduleTiers.ts writes for a tier."""
    return {
        "id": identifier,
        "model": "PV 450 Wp · 1762 × 1134 mm",
        "width_m": 1.134,
        "length_m": 1.762,
        "thickness_m": 0.035,
        "stc_power_w": 450,
        **({"gamma_pdc_per_c": gamma} if gamma is not None else {}),
        "source": {
            "kind": "user_declared",
            "note": TIER_SOURCE_NOTE,
            "document_sha256": None,
            "url": None,
            "page": None,
        },
    }


def tier_geometry(*, gamma: float | None = -0.0034) -> FixtureObject:
    value = cast(FixtureObject, fixture_geometry())
    value["module_specs"] = [tier_spec(gamma=gamma)]
    for array in cast(list[FixtureObject], value["arrays"]):
        array["module_spec_id"] = "module_tier"
    return value


def tier_parameters(*, gamma: float | None = -0.0034) -> FixtureObject:
    """PV parameters a browser sends for that tier: its own coefficient."""
    value = cast(FixtureObject, parameter_document())
    value["modules"] = [
        {
            "module_spec_id": "module_tier",
            "gamma_pdc_per_c": gamma,
            "source": {
                "kind": "user_declared",
                "note": TIER_SOURCE_NOTE,
                "document_sha256": None,
                "url": None,
                "page": None,
            },
        }
    ]
    return value


def woo_template(directory: Path) -> tuple[ProductSources, Object, Object]:
    """The site's own loader over the fixture feed plus its frozen proof."""
    products = product_sources(directory)
    with frozen_publication():
        basis = json_object(products.module_basis())
    return products, basis, cast(Object, basis["module"])


def test_a_declared_reference_passes_roof_and_pv_checks_without_a_product(
    tmp_path: Path,
) -> None:
    """The whole point: no Woo publication is consulted at all."""
    products = ProductSources(lambda: pytest.fail("a declared tier needs no product"))
    geometry = tier_geometry()
    ProductSources.check_roof_inputs({"geometry": geometry})
    ProductSources.check_pv_inputs(
        {"geometry": geometry, "pv_generation": tier_parameters()}
    )
    # The same roof module through the typed reader the kernels use.
    module = read_geometry(geometry).module_specs[0]
    assert is_declared_reference(module)
    basis = declared_module_basis(module)
    assert basis.gamma_pdc_per_c == -0.0034
    assert basis.module_spec_id == "module_tier"
    assert products.load.__name__ == "<lambda>"  # never called by the checks above


def test_a_declared_reference_without_its_coefficient_is_refused_by_code(
    tmp_path: Path,
) -> None:
    """An absent coefficient must name itself, not fall back to the Woo figure."""
    geometry = tier_geometry(gamma=None)
    with pytest.raises(InvalidInput) as raised:
        ProductSources.check_roof_inputs({"geometry": geometry})
    assert "declared_module_gamma_missing" in str(raised.value)
    assert raised.value.code == "invalid_input"
    with pytest.raises(InvalidInput) as module_raised:
        declared_module_basis(read_geometry(geometry).module_specs[0])
    assert "declared_module_gamma_missing" in str(module_raised.value)
    # A PV parameter record cannot carry a null coefficient at all: the wire
    # contract refuses it before any basis comparison runs.
    with pytest.raises(InvalidInput) as pv_raised:
        ProductSources.check_pv_inputs(
            {"geometry": geometry, "pv_generation": tier_parameters(gamma=None)}
        )
    assert "modules.0.gamma_pdc_per_c" in str(pv_raised.value)


def test_a_roof_module_without_the_marker_is_still_refused(tmp_path: Path) -> None:
    """A user-declared module that is not a tier is not silently accepted."""
    geometry = tier_geometry()
    geometry["module_specs"][0]["source"]["note"] = "Synthetic module, not a product"
    with pytest.raises(InvalidInput) as raised:
        ProductSources.check_roof_inputs({"geometry": geometry})
    assert "declared_module_marker_missing" in str(raised.value)


def test_pv_parameters_must_match_the_declared_module(tmp_path: Path) -> None:
    """A coefficient the module does not declare is a changed calculation."""
    parameters = tier_parameters(gamma=-0.0029)
    with pytest.raises(InvalidInput) as raised:
        ProductSources.check_pv_inputs(
            {"geometry": tier_geometry(), "pv_generation": parameters}
        )
    assert "declared_module_parameters_changed" in str(raised.value)


def test_pv_parameters_cannot_claim_a_product_document(tmp_path: Path) -> None:
    """A declared tier never borrows a manufacturer citation for its numbers."""
    parameters = tier_parameters()
    parameters["modules"][0]["source"].update(
        kind="datasheet",
        document_sha256="0" * 64,
        url="https://example.invalid/module.pdf",
        page=1,
    )
    with pytest.raises(InvalidInput) as raised:
        ProductSources.check_pv_inputs(
            {"geometry": tier_geometry(), "pv_generation": parameters}
        )
    assert "declared_module_source_claim" in str(raised.value)


def test_the_woo_module_path_is_unchanged(tmp_path: Path) -> None:
    """Regression guard: the product path still needs the maintained record."""
    products, basis, template = woo_template(tmp_path)
    geometry = cast(FixtureObject, fixture_geometry())
    geometry["module_specs"] = [
        {**cast(Object, template["specification"]), "id": "module"}
    ]
    parameters = cast(FixtureObject, parameter_document())
    parameters["modules"] = [
        {**cast(Object, template["parameters"]), "module_spec_id": "module"}
    ]
    with frozen_publication():
        ProductSources.check_roof_inputs({"geometry": geometry}, basis)
        ProductSources.check_pv_inputs(
            {"geometry": geometry, "pv_generation": parameters}, basis
        )
        # Omitting the proof is a refusal, never a silent pass.
        with pytest.raises(InvalidInput) as raised:
            ProductSources.check_roof_inputs({"geometry": geometry})
        assert "woo_module_proof_missing" in str(raised.value)
        # An edited specification still fails against the published record.
        edited = cast(FixtureObject, geometry)
        edited["module_specs"][0]["stc_power_w"] = 495
        with pytest.raises(InvalidInput):
            ProductSources.check_roof_inputs({"geometry": edited}, basis)


def test_a_mixed_roof_judges_each_module_against_its_own_basis(
    tmp_path: Path,
) -> None:
    """One array on the product module, one on a tier: both rules at once."""
    _, basis, template = woo_template(tmp_path)
    geometry = cast(FixtureObject, fixture_geometry())
    woo_spec = {**cast(Object, template["specification"]), "id": "module"}
    geometry["module_specs"] = [woo_spec, tier_spec("module_tier")]
    # Second array placed on the tier; the fixture's own array keeps the product.
    tier_array = dict(cast(list[dict[str, Any]], geometry["arrays"])[0])
    tier_array.update(id="array_tier", module_spec_id="module_tier", origin_uv=[0, 0])
    geometry["arrays"] = [*cast(list[Object], geometry["arrays"]), tier_array]

    parameters = cast(FixtureObject, parameter_document())
    parameters["modules"] = [
        {**cast(Object, template["parameters"]), "module_spec_id": "module"},
        {
            "module_spec_id": "module_tier",
            "gamma_pdc_per_c": -0.0034,
            "source": {
                "kind": "user_declared",
                "note": TIER_SOURCE_NOTE,
                "document_sha256": None,
                "url": None,
                "page": None,
            },
        },
    ]
    parameters["arrays"] = [
        *cast(list[Object], parameters["arrays"]),
        {
            **cast(Object, cast(list[Object], parameters["arrays"])[0]),
            "array_id": "array_tier",
        },
    ]
    parameters["converters"][0]["array_ids"] = ["array", "array_tier"]
    with frozen_publication():
        ProductSources.check_roof_inputs({"geometry": geometry}, basis)
        ProductSources.check_pv_inputs(
            {"geometry": geometry, "pv_generation": parameters}, basis
        )
        # Swapping the coefficients between the two modules must fail: each
        # entry belongs to one basis, and neither may borrow the other's.
        swapped = json.loads(json.dumps(parameters))
        swapped["modules"][0]["gamma_pdc_per_c"] = -0.0034
        swapped["modules"][1]["gamma_pdc_per_c"] = cast(
            float, cast(Object, template["parameters"])["gamma_pdc_per_c"]
        )
        with pytest.raises(InvalidInput):
            ProductSources.check_pv_inputs(
                {"geometry": geometry, "pv_generation": swapped}, basis
            )


def test_the_browser_contract_geometry_still_matches_the_engine() -> None:
    """The tier field is part of the shared geometry schema the planner reads."""
    schema = json.loads(
        (ROOT / "apps/planner/src/contracts/geometry.schema.json").read_text()
    )
    assert "gamma_pdc_per_c" in schema["$defs"]["ModuleSpec"]["properties"]
    assert "gamma_pdc_per_c" not in schema["$defs"]["ModuleSpec"]["required"]
