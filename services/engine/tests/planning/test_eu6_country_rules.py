"""The national reading classifies only project declarations under the cited clause."""

from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from linker_engine.planning.country_rules import review_country_rules
from linker_engine.planning.grid_connection import (
    BUNDLED_RULE_COUNTRIES,
    bundled_country_sources,
    rule_gap_metadata,
)

EVIDENCE = (
    Path(__file__).resolve().parents[4] / "docs/research/2026-11-24-eu6-country-rules"
)
BASES = {
    "IT": "it_lv_generation_spi",
    "ES": "es_self_consumption",
    "GB": "gb_lv_microgeneration",
    "PL": "pl_renewable_electric_installation",
    "BE": "be_small_plant_limits",
    "CH": "ch_lv_generation_control",
}


def assess(country: str, **values: Any) -> Any:
    voltage = values.pop("voltage_level", "low")
    return review_country_rules(
        country,
        {
            "schema_version": 1,
            "basis": BASES[country],
            "rule_date": "2026-11-24",
            "power_kw": None,
            "connection_voltage_kv": None,
            "de_before_control_test": None,
            "de_remuneration": None,
            "de_plug_in_exception": None,
            "fr_enedis_full_self_consumption": None,
            **values,
        },
        voltage_level=voltage,
    )


def test_eleven_reference_packs_have_versioned_sources() -> None:
    assert BUNDLED_RULE_COUNTRIES == {"DE", "FR", "NL", "AT", "SE", *BASES}
    for country in BUNDLED_RULE_COUNTRIES:
        assert rule_gap_metadata(country)["gap_code"] == "bundled_rule_pack_available"
        assert bundled_country_sources(country)
    for country in BASES:
        source = bundled_country_sources(country)[0]
        assert (
            source["text_sha256"]
            == sha256(
                (EVIDENCE / f"{country.lower()}-excerpts.txt").read_bytes()
            ).hexdigest()
        )


@pytest.mark.parametrize(
    ("country", "values", "expected"),
    [
        ("GB", {"gb_in_great_britain": False}, "gb_other_territory"),
        (
            "GB",
            {"gb_in_great_britain": True, "gb_permanently_wired": False},
            "gb_plug_in_scope",
        ),
        ("CH", {"ch_new_installation": False}, "ch_existing"),
        (
            "CH",
            {"ch_new_installation": True, "power_kw": 251},
            "ch_above_interface_scope",
        ),
        ("IT", {"power_kw": 11.08}, "it_integrated_or_dedicated"),
        ("IT", {"power_kw": 11.09}, "it_dedicated_relay"),
        ("IT", {"power_kw": 9.5, "voltage_level": "medium"}, "outside_lv_scope"),
        ("PL", {"power_kw": 50, "connection_voltage_kv": 0.4}, "pl_microinstallation"),
        (
            "PL",
            {"power_kw": 50.01, "connection_voltage_kv": 0.4},
            "pl_outside_microinstallation",
        ),
        (
            "PL",
            {"power_kw": 50, "connection_voltage_kv": 110},
            "pl_outside_microinstallation",
        ),
        (
            "BE",
            {"be_three_phase": False, "be_generation_kva": 5, "be_storage_kva": 5},
            "be_within_power_limits",
        ),
        (
            "BE",
            {"be_three_phase": False, "be_generation_kva": 5.01, "be_storage_kva": 0},
            "be_check_local_single_phase_limit",
        ),
        (
            "BE",
            {"be_three_phase": True, "be_generation_kva": 10, "be_storage_kva": 10},
            "be_within_power_limits",
        ),
        (
            "BE",
            {"be_three_phase": True, "be_generation_kva": 10, "be_storage_kva": 10.01},
            "be_above_power_limits",
        ),
        (
            "GB",
            {
                "gb_in_great_britain": True,
                "gb_permanently_wired": True,
                "current_per_phase_a": 16,
                "gb_type_tested": True,
                "gb_multiple_premises": False,
            },
            "gb_single_g98_notice",
        ),
        (
            "GB",
            {
                "gb_in_great_britain": True,
                "gb_permanently_wired": True,
                "current_per_phase_a": 16,
                "gb_type_tested": True,
                "gb_multiple_premises": True,
            },
            "gb_cluster_agreement",
        ),
        (
            "GB",
            {
                "gb_in_great_britain": True,
                "gb_permanently_wired": True,
                "current_per_phase_a": 16.01,
            },
            "gb_g99_application",
        ),
        ("ES", {"es_export_surplus": False}, "es_generation_permit_exempt"),
        (
            "ES",
            {"es_export_surplus": True, "es_serviced_urban_land": True, "power_kw": 15},
            "es_generation_permit_exempt",
        ),
        (
            "ES",
            {
                "es_export_surplus": True,
                "es_serviced_urban_land": True,
                "power_kw": 15.01,
            },
            "es_generation_permits",
        ),
        (
            "ES",
            {"es_export_surplus": True, "es_serviced_urban_land": False, "power_kw": 8},
            "es_generation_permits",
        ),
        (
            "CH",
            {"ch_new_installation": True, "apparent_power_kva": 30, "power_kw": 30},
            "ch_remote_disconnect",
        ),
        (
            "CH",
            {"ch_new_installation": True, "apparent_power_kva": 30.01, "power_kw": 30},
            "ch_power_reduction",
        ),
    ],
)
def test_national_thresholds_use_the_declared_quantity(
    country: str, values: dict[str, Any], expected: str
) -> None:
    result = assess(country, **values)
    assert result["checks"][0]["outcome"] == expected
    assert result["checks"][0]["source_id"] == result["sources"][0]["id"]


@pytest.mark.parametrize("country", BASES)
def test_no_guess_from_missing_inputs_or_later_date(country: str) -> None:
    assert assess(country)["checks"][0]["outcome"] == "missing_inputs"
    assert (
        assess(country, rule_date="2026-11-25")["checks"][0]["outcome"]
        == "outside_version"
    )
