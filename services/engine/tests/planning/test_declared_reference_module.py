"""Linker does not sell PV modules, so the roof layout may rest on a declared
planning reference instead of the one Woo-maintained reference module.

These tests hold the door open: the engine must accept a tier module that
carries its own numbers, must refuse one that does not, and must keep judging
Woo-selected modules exactly as before.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from linker_engine.planning.errors import InvalidInput
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_documents import ModuleSource, ModuleSpec
from linker_engine.planning.product_binding import WooReference
from linker_engine.planning.product_sources import (
    DECLARED_REFERENCE_PREFIX,
    ProductSources,
)

ROOT = Path(__file__).resolve().parents[4]


def geometry_fixture() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / "fixtures/planning/geometry-flat.json").read_text()),
    )


def tier_module(*, gamma: float | None = -0.0034, power: int = 450) -> ModuleSpec:
    """The shape `apps/planner`'s moduleTiers.ts publishes for a tier."""
    return ModuleSpec(
        id="module_tier",
        model=f"PV {power} Wp",
        width_m=1.134,
        length_m=1.762,
        thickness_m=0.035,
        stc_power_w=power,
        gamma_pdc_per_c=gamma,
        source=ModuleSource(
            kind="user_declared",
            note=f"{DECLARED_REFERENCE_PREFIX} — generic tier planning reference",
            document_sha256=None,
            url=None,
            page=None,
        ),
    )


def test_a_tier_module_is_its_own_basis_and_needs_no_product() -> None:
    module = tier_module()
    assert ProductSources.declared_reference(module)
    # The whole point: no comparison with the Woo publication happens here.
    ProductSources.check_declared_reference(module)


def test_a_tier_without_its_own_coefficient_is_refused() -> None:
    module = tier_module(gamma=None)
    assert ProductSources.declared_reference(module)
    with pytest.raises(InvalidInput) as raised:
        ProductSources.check_declared_reference(module)
    assert "gamma_pdc_per_c" in str(raised.value)
    assert raised.value.code == "invalid_input"


def test_a_note_without_the_marker_is_not_a_tier() -> None:
    source = ModuleSource(
        kind="user_declared",
        note="some other declared module",
        document_sha256=None,
        url=None,
        page=None,
    )
    module = ModuleSpec(
        id="module_other",
        model="PV 450 Wp",
        width_m=1.134,
        length_m=1.762,
        thickness_m=0.035,
        stc_power_w=450,
        gamma_pdc_per_c=-0.0034,
        source=source,
    )
    assert not ProductSources.declared_reference(module)
    with pytest.raises(InvalidInput):
        ProductSources.check_declared_reference(module)


def test_an_unincluded_tier_module_does_not_block_a_woo_layout() -> None:
    """The geometry check only judges modules a placed array actually uses."""
    value = geometry_fixture()
    value["module_specs"].append(
        json.loads(tier_module().model_dump_json(exclude_none=False))
    )
    # The fixture's arrays still reference their Woo module, so adding an unused
    # tier record must not change a single verdict.
    read_geometry(value)


def test_a_woo_module_still_needs_the_maintained_datasheet() -> None:
    """Regression guard: the tier path must not loosen the product path."""
    # A Woo reference on a user_declared source is refused by the document model
    # itself, which is what keeps the two paths from ever blurring.
    with pytest.raises(ValidationError):
        ModuleSource(
            kind="user_declared",
            note="declared_reference — looks like a tier",
            document_sha256=None,
            url=None,
            page=None,
            woo=WooReference(
                product_id=1,
                product_revision="rev-1",
                reference_input_id="trina_reference",
            ),
        )
