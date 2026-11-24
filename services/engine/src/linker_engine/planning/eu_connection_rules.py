"""Selected national grid-connection provisions, matched to declared project quantities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .canonical import Object

if TYPE_CHECKING:
    from .country_rules import CountryRuleInputs

BASES = {
    "it_lv_generation_spi": "IT",
    "es_self_consumption": "ES",
    "gb_lv_microgeneration": "GB",
    "pl_renewable_electric_installation": "PL",
    "be_small_plant_limits": "BE",
    "ch_lv_generation_control": "CH",
}

CHECKS = {
    "IT": "it_interface_protection",
    "ES": "es_generation_access",
    "GB": "gb_connection_route",
    "PL": "pl_microinstallation_scope",
    "BE": "be_small_plant_power",
    "CH": "ch_dso_interface",
}


# The inputs here keep power, apparent power and current distinct. A date selects
# a verified edition; establishing which edition governs the site is a DSO task.
def evaluate(
    country: str, f: CountryRuleInputs, voltage_level: str | None
) -> tuple[str, list[str]]:
    if country in {"IT", "GB", "BE", "CH"}:
        if voltage_level is None:
            return "missing_inputs", ["voltage_level"]
        if voltage_level != "low":
            return "outside_lv_scope", []

    if country == "IT":
        if f.power_kw is None:
            return "missing_inputs", ["power_kw"]
        return (
            "it_integrated_or_dedicated"
            if f.power_kw <= 11.08
            else "it_dedicated_relay"
        ), []

    if country == "ES":
        if f.es_export_surplus is None:
            return "missing_inputs", ["es_export_surplus"]
        if not f.es_export_surplus:
            return "es_generation_permit_exempt", []
        if f.es_serviced_urban_land is False or (
            f.power_kw is not None and f.power_kw > 15
        ):
            return "es_generation_permits", []
        missing = [
            k
            for k, v in (
                ("power_kw", f.power_kw),
                ("es_serviced_urban_land", f.es_serviced_urban_land),
            )
            if v is None
        ]
        return ("missing_inputs" if missing else "es_generation_permit_exempt"), missing

    if country == "GB":
        if f.gb_in_great_britain is None:
            return "missing_inputs", ["gb_in_great_britain"]
        if not f.gb_in_great_britain:
            return "gb_other_territory", []
        if f.gb_permanently_wired is None:
            return "missing_inputs", ["gb_permanently_wired"]
        if not f.gb_permanently_wired:
            return "gb_plug_in_scope", []
        if f.current_per_phase_a is None:
            return "missing_inputs", ["current_per_phase_a"]
        if f.current_per_phase_a > 16:
            return "gb_g99_application", []
        if f.gb_type_tested is None:
            return "missing_inputs", ["gb_type_tested"]
        if not f.gb_type_tested:
            return "gb_confirm_non_type_tested", []
        if f.gb_multiple_premises is None:
            return "missing_inputs", ["gb_multiple_premises"]
        return (
            "gb_cluster_agreement" if f.gb_multiple_premises else "gb_single_g98_notice"
        ), []

    if country == "PL":
        missing = [
            k
            for k, v in (
                ("power_kw", f.power_kw),
                ("connection_voltage_kv", f.connection_voltage_kv),
            )
            if v is None
        ]
        if f.power_kw is None or f.connection_voltage_kv is None:
            return "missing_inputs", missing
        return (
            "pl_microinstallation"
            if f.power_kw <= 50 and f.connection_voltage_kv < 110
            else "pl_outside_microinstallation"
        ), []

    if country == "BE":
        g, s = f.be_generation_kva, f.be_storage_kva
        if f.be_three_phase is None or g is None or s is None:
            return "missing_inputs", [
                k
                for k, v in (
                    ("be_three_phase", f.be_three_phase),
                    ("be_generation_kva", g),
                    ("be_storage_kva", s),
                )
                if v is None
            ]
        if max(g, s) == 0:
            return "be_no_generating_units", []
        if f.be_three_phase:
            return (
                "be_within_power_limits" if max(g, s) <= 10 else "be_above_power_limits"
            ), []
        return (
            "be_within_power_limits"
            if max(g, s) <= 5
            else "be_check_local_single_phase_limit"
        ), []

    # VSE §6.5.1 applies to new LV EEA up to 250 kW. Its second criterion
    # is stated in kVA and cannot be inferred from that active power.
    assert country == "CH"
    if f.ch_new_installation is None:
        return "missing_inputs", ["ch_new_installation"]
    if not f.ch_new_installation:
        return "ch_existing", []
    if f.power_kw is None:
        return "missing_inputs", ["power_kw"]
    if f.power_kw > 250:
        return "ch_above_interface_scope", []
    if f.apparent_power_kva is None:
        return "missing_inputs", ["apparent_power_kva"]
    return (
        "ch_power_reduction" if f.apparent_power_kva > 30 else "ch_remote_disconnect"
    ), []


SOURCES: dict[str, Object] = {
    "IT": {
        "id": "it_cei_0_21_spi",
        "title": "CEI 0-21",
        "source_url": "https://static.ceinorme.it/strumenti-online/doc/0-21consolidata.pdf",
        "edition": "V3 · 2025-10",
        "clause": "§ 8.6.2, pp. 97–98",
        "effective_from": None,
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "577aba951895f5399b33ac4e0b644a552db7456b800c049c546dfc10312d03c8",
    },
    "ES": {
        "id": "es_rd244_generation_access",
        "title": "Real Decreto 244/2019",
        "source_url": "https://www.boe.es/eli/es/rd/2019/04/05/244/con",
        "edition": "BOE · 2026-03-21",
        "clause": "Arts. 3(h), 7.1(a)–(b)",
        "effective_from": "2019-04-07",
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "971ac7bd5452cc237d33a4a972dc768bebdeebf658bf3afe23c77c1a07b10bff",
    },
    "GB": {
        "id": "gb_ena_g98",
        "title": "ENA Engineering Recommendation G98",
        "source_url": "https://www.ena-eng.org/ENA-Docs/Index?Action=ViewDetail&EID=102993&tab=introduction",
        "edition": "G98 2/A1 · 2026-08",
        "clause": "§§ 2.1, 2.4",
        "effective_from": None,
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "46ec5271069c2bcb1e02c3bed0b1162dc52723cd4b9e834c4734046631a2da99",
    },
    "PL": {
        "id": "pl_oze_art2_19",
        "title": "Ustawa o odnawialnych źródłach energii",
        "source_url": "https://eli.gov.pl/api/acts/DU/2026/68/text/U/D20260068Lj.pdf",
        "edition": "Dz.U. 2026 poz. 68 · 2026-08-03",
        "clause": "Art. 2 pkt 19, p. 9",
        "effective_from": None,
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "d4e24aadd640f35ac5612dc0076fe405816e7afdd43b07802a2d8d91a0cb3d95",
    },
    "BE": {
        "id": "be_c1011_small_power",
        "title": "Synergrid C10/11",
        "source_url": "https://www.synergrid.be/images/downloads/Technical_prescription_C10-11_ed2-4_20251015_tekst_FR.pdf",
        "edition": "2.4 · 2025-10-15",
        "clause": "§ 4.1.7, tableau 2, note 9, pp. 19–20",
        "effective_from": "2025-10-15",
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "70d2303c656be257bc08581b68c1656c8e5bcacdea1aa49be8a64f50427dacca",
    },
    "CH": {
        "id": "ch_vse_lv_control",
        "title": "VSE/AES NA/EEA-NE7 – CH",
        "source_url": "https://www.strom.ch/sites/default/files/media/documents/20250627-be-netzanschluss-ne7.pdf",
        "edition": "2025-06-27",
        "clause": "§§ 6.5.1(2–3), 6.5.2, S. 40",
        "effective_from": None,
        "evidence_snapshot_date": "2026-11-24",
        "text_sha256": "613862fc48cd153d33a80b3036e2e2e767d7e6b583be4881c4c4121737adc424",
    },
}

GB_DNO_SOURCE: Object = {
    "id": "gb_nged_g98_procedure",
    "title": "National Grid Electricity Distribution – G98 connection procedures",
    "source_url": "https://connections.nationalgrid.co.uk/g98-connection-procedures",
    "edition": None,
    "clause": "Single and multiple premises",
    "effective_from": None,
    "evidence_snapshot_date": "2026-11-24",
    "text_sha256": "b29664ffe2d8657c32235fb3dfde3da710c4179cbe0b1cc004773975495de942",
}

FIELDS: dict[str, tuple[str, ...]] = {
    "IT": ("power_kw",),
    "ES": (
        "es_export_surplus",
        "power_kw",
        "es_serviced_urban_land",
    ),
    "GB": (
        "gb_in_great_britain",
        "gb_permanently_wired",
        "current_per_phase_a",
        "gb_type_tested",
        "gb_multiple_premises",
    ),
    "PL": (
        "power_kw",
        "connection_voltage_kv",
    ),
    "BE": (
        "be_three_phase",
        "be_generation_kva",
        "be_storage_kva",
    ),
    "CH": (
        "ch_new_installation",
        "power_kw",
        "apparent_power_kva",
    ),
}

UNITS = {
    "power_kw": "kW",
    "connection_voltage_kv": "kV",
    "apparent_power_kva": "kVA",
    "current_per_phase_a": "A",
    "be_generation_kva": "kVA",
    "be_storage_kva": "kVA",
}
