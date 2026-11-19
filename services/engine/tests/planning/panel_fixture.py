"""Project-declared panel inputs for numerical and browser fixtures."""

from .conftest import FixtureObject


def panel_basis() -> FixtureObject:
    return {"schema_version": 1, "kind": "project_panel_parameters"}


def panel_parameters() -> FixtureObject:
    source = {
        "kind": "user_declared",
        "note": "declared_reference — Customer-provided panel parameters.",
        "document_sha256": None,
        "url": None,
        "page": None,
    }
    return {
        "specification": {
            "id": "panel",
            "model": "PV 460 Wp · 1762 × 1134 mm",
            "width_m": 1.134,
            "length_m": 1.762,
            "thickness_m": 0.03,
            "stc_power_w": 460,
            "gamma_pdc_per_c": -0.0029,
            "source": source,
            "electrical": {
                "voc_v": 53.8,
                "vmpp_v": 45.4,
                "isc_a": 10.81,
                "impp_a": 10.14,
                "max_system_voltage_v": 1500,
                "alpha_isc_pct_per_c": 0.04,
                "beta_voc_pct_per_c": -0.24,
                "cell_technology": "monocrystalline",
            },
        },
        "parameters": {
            "module_spec_id": "panel",
            "gamma_pdc_per_c": -0.0029,
            "source": source,
        },
    }
