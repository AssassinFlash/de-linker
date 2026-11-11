"""Versioned, conditional readings of selected national connection rules.

These checks use project-declared quantities, not inferred equipment ratings.
They do not establish project applicability, operator acceptance or permission.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, cast

from pydantic import Field, field_validator

from .canonical import Json, Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput

type Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Basis = Literal[
    "fr_generation_pmax",
    "nl_storage_max_active",
    "de_pv_installed",
    "at_tor_typ_a_max_capacity",
]


class CountryRuleInputs(Document):
    schema_version: SchemaVersion
    basis: Basis
    rule_date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None
    power_kw: Positive | None
    connection_voltage_kv: Positive | None
    de_before_control_test: bool | None
    de_remuneration: Literal["feed_in_or_tenant", "other"] | None
    de_plug_in_exception: bool | None
    fr_enedis_full_self_consumption: bool | None
    # TOR Erzeuger Typ A measures the disconnection-protection threshold in
    # apparent power (kVA), not in the declared active power (kW), and it
    # distinguishes the maximum capacity Pmax from the agreed net active power
    # at the connection point (§ 4.1). These declarations are additive: an
    # existing revision saved before them stays readable, and an AT reading
    # reports them as missing instead of guessing.
    apparent_power_kva: Positive | None = None
    net_active_power_kw: Positive | None = None
    at_existing_installation_change: bool | None = None
    at_change_previous_power_kw: Positive | None = None
    at_conformity_basis: (
        Literal[
            "austrian_inverter_list",
            "accredited_r25_report",
            "vde_4105_with_r25_properties",
        ]
        | None
    ) = None

    @field_validator("rule_date")
    @classmethod
    def calendar_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


# These are the exact official-source text extractions recorded in
# docs/research/2026-10-23-modern-workbench/COUNTRY-EVIDENCE.md.
# Each reading is bounded by its effective date and the last date on which the
# cited text was verified; later dates remain unresolved instead of inheriting it.
_SOURCES: dict[str, Object] = {
    "FR": {
        "id": "fr_arrete_article_35",
        "title": "Arrêté du 9 juin 2020",
        "source_url": "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036860",
        "edition": "2020-06-26",
        "clause": "Article 35",
        "effective_from": "2020-06-26",
        "evidence_snapshot_date": "2026-11-04",
        "text_sha256": "4d35445b56b2d705e6afb81e93a4beec10f896ffcd3f14b1e69feda61794dfb3",
    },
    "NL": {
        "id": "nl_systeemcode_article_2_9",
        "title": "Systeemcode elektriciteit 2026",
        "source_url": "https://wetten.overheid.nl/BWBR0052336/2026-10-01",
        "edition": "2026-10-01",
        "clause": "Article 2.9(3)(a), (g)",
        "effective_from": "2026-10-01",
        "evidence_snapshot_date": "2026-11-04",
        "text_sha256": "41c61e47556c3415fc2072745f38bc2f7ae9a6e82a2ad6aa9f981828ebd7edf1",
    },
    "DE": {
        "id": "de_eeg_section_9",
        "title": "EEG 2023",
        "source_url": "https://www.gesetze-im-internet.de/eeg_2014/__9.html",
        "edition": None,
        "clause": "§ 9(2), (3)",
        # EEG 2023 (BGBl. 2022 I S. 1237) entered into force on
        # 1 January 2023; § 9 has been in force from that date.
        "effective_from": "2023-01-01",
        "evidence_snapshot_date": "2026-11-04",
        "text_sha256": "dfbff2f705291e19c119bcbefec5ed046917044e20a8c20d43e993000df3958f",
    },
    "AT": {
        "id": "at_tor_erzeuger_typ_a_1_4",
        "title": "TOR Stromerzeugungsanlagen Typ A, Version 1.4",
        "source_url": "https://ogd.ris.bka.gv.at/Dokumente/BgblAuth/BGBLA_2026_II_301/Anlagen_0001_1C9138FC_241E_4C87_9C70_B47AC7600383.pdf",
        "edition": "Version 1.4, BGBl. II Nr. 301/2026",
        # Kapitel 2 of the document history: version 1.4 is valid from
        # 2026-06-01 and was published in BGBl. II Nr. 301/2026 (2026-10-14).
        "effective_from": "2026-06-01",
        "evidence_snapshot_date": "2026-11-11",
        "text_sha256": "5be42c6431cfbe670c70e3fb64827c7f97a72cab1b8a6741e9a3955432399820",
        "clause": "Kapitel 2.1, 2.2, 4.1, 6.1.2, 6.3.1",
    },
}

# The connection route and the conformity evidence of an Austrian installation
# come from the ElWG and from the same TOR part, so they carry their own source
# identity and their own dated reading instead of inheriting the TOR's.
_AT_ELWG_SOURCE: Object = {
    "id": "at_elwg_2025",
    "title": "Elektrizitätswirtschaftsgesetz (ElWG)",
    "source_url": "https://www.e-netze.at/downloads-data/pdf.aspx?pdf=ElWG_Fassung%20vom%2007012026.pdf",
    "edition": "RIS consolidated version dated 2026-01-07",
    "clause": "§ 6 Abs. 1 Z 78, § 77, § 96(1), (2)",
    # The ElWG was published in BGBl. I Nr. 91/2025. This reading is the RIS
    # consolidated version dated 2026-01-07, which is the edition the cited
    # provisions were verified in; later amendments are not covered.
    "effective_from": "2026-01-07",
    "evidence_snapshot_date": "2026-11-11",
    "text_sha256": "c933a15dc7c3802fda69e2d04ab144d1a5143a056c7bfad0318ddfc5555ac641",
}
_AT_CONFORMITY_SOURCE: Object = {
    "id": "at_tor_erzeuger_typ_a_1_4_conformity",
    "title": "TOR Stromerzeugungsanlagen Typ A, Version 1.4, Kapitel 8.1",
    "source_url": "https://ogd.ris.bka.gv.at/Dokumente/BgblAuth/BGBLA_2026_II_301/Anlagen_0001_1C9138FC_241E_4C87_9C70_B47AC7600383.pdf",
    "edition": "Version 1.4, BGBl. II Nr. 301/2026",
    "clause": "Kapitel 8.1 samt Fußnoten 37 und 38",
    "effective_from": "2026-06-01",
    "evidence_snapshot_date": "2026-11-11",
    "text_sha256": "5be42c6431cfbe670c70e3fb64827c7f97a72cab1b8a6741e9a3955432399820",
}

_BASIS_COUNTRY: dict[str, str] = {
    "fr_generation_pmax": "FR",
    "nl_storage_max_active": "NL",
    "de_pv_installed": "DE",
    "at_tor_typ_a_max_capacity": "AT",
}

_ENEDIS_SOURCE: Object = {
    "id": "fr_enedis_total_self_consumption",
    "title": "Enedis: autoconsommation totale",
    "source_url": "https://www.enedis.fr/autoconsommer-la-totalite-de-lenergie-produite-par-vos-panneaux",
    "edition": None,
    "clause": "Déclarer mon installation, CACSI",
    # This page has no effective-date statement; only the dated reading itself.
    "effective_from": None,
    "evidence_snapshot_date": "2026-11-04",
    "text_sha256": "3741f1e39b855240554fc7348cd130d08f8b186e2e3a38dd831b2c708b4ff673",
}


def validate_country_rule_inputs(inputs: Object) -> None:
    if "country_rule_inputs" in inputs:
        if "grid_connection" not in inputs:
            raise InvalidInput(
                "country rule inputs require grid connection information"
            )
        CountryRuleInputs.read(inputs["country_rule_inputs"])


def review_country_rules(
    country: str | None, value: Json, *, operator: str | None = None
) -> Object | None:
    """Interpret only the specified country, quantity and source edition."""
    facts = CountryRuleInputs.read(value)
    if country != _BASIS_COUNTRY[facts.basis]:
        return None
    assert country is not None
    source = dict(_SOURCES[country])
    source_id = cast(str, source["id"])
    floor = cast(str, source["effective_from"])
    through = cast(str, source["evidence_snapshot_date"])
    in_version = facts.rule_date is not None and floor <= facts.rule_date <= through
    actual: Object = {
        "power_kw": facts.power_kw,
        "connection_voltage_kv": facts.connection_voltage_kv,
    }
    checks: list[Json] = []
    sources: list[Json] = [source]

    def add(
        identifier: str,
        outcome: str,
        missing: list[str] | None = None,
        *,
        origin: str = source_id,
    ) -> None:
        checks.append(
            {
                "id": identifier,
                "status": "unresolved"
                if outcome
                in {
                    "missing_inputs",
                    "outside_version",
                    "below_range",
                    "boundary_not_established",
                    # AT: the cited TOR part does not govern the declared
                    # project, so it supplies no conditional reading for it.
                    "outside_scope",
                    # AT § 2.2 lists example criteria ("können z.B. sein"), so
                    # an unchanged power does not settle the question.
                    "power_criterion_not_exceeded_other_criteria_open",
                }
                else "conditional",
                "outcome": outcome,
                "source_id": origin,
                "actual": dict(actual),
                "missing_inputs": cast(list[Json], missing or []),
            }
        )

    missing_date = facts.rule_date is None
    p = facts.power_kw
    if country == "FR":
        missing = [
            key
            for key, absent in (
                ("rule_date", missing_date),
                ("power_kw", p is None),
                ("connection_voltage_kv", facts.connection_voltage_kv is None),
            )
            if absent
        ]
        outcome = "missing_inputs" if missing else "outside_version"
        if not missing and in_version:
            assert p is not None and facts.connection_voltage_kv is not None
            outcome = (
                "below_range"
                if p < 0.8
                else "type_d"
                if facts.connection_voltage_kv >= 110 or p >= 75000
                else "type_c"
                if p >= 18000
                else "type_b"
                if p >= 1000
                else "type_a"
            )
        add("fr_generation_type", outcome, missing)
        if (
            facts.fr_enedis_full_self_consumption is True
            and operator is not None
            and operator.strip().casefold() == "enedis"
        ):
            sources.append(dict(_ENEDIS_SOURCE))
            enedis_through = cast(str, _ENEDIS_SOURCE["evidence_snapshot_date"])
            enedis_outcome = (
                "missing_inputs"
                if missing_date
                else "outside_version"
                if facts.rule_date != enedis_through
                else "enedis_declare_cacsi"
            )
            enedis_missing = ["rule_date"] if missing_date else []
            enedis_id = cast(str, _ENEDIS_SOURCE["id"])
            add(
                "fr_enedis_declaration",
                enedis_outcome,
                enedis_missing,
                origin=enedis_id,
            )
            add(
                "fr_enedis_certification",
                "enedis_consuel_or_attestation"
                if enedis_outcome == "enedis_declare_cacsi"
                else enedis_outcome,
                enedis_missing,
                origin=enedis_id,
            )
    elif country == "NL":
        missing = [
            key
            for key, absent in (("rule_date", missing_date), ("power_kw", p is None))
            if absent
        ]
        kind = lfsm = "missing_inputs" if missing else "outside_version"
        if not missing and in_version:
            assert p is not None
            kind = (
                "below_range"
                if p < 0.8
                else "type_d"
                if p >= 60000
                else "type_c"
                if p >= 50000
                else "type_b"
                if p >= 1000
                else "type_a"
            )
            lfsm = (
                "below_range"
                if p < 0.8
                else "boundary_not_established"
                if p == 0.8
                else "statism_1_percent"
                if p >= 1000
                else "statism_2_percent"
            )
        add("nl_storage_type", kind, missing)
        add("nl_storage_lfsm", lfsm, missing)
    elif country == "DE":
        missing = [
            key
            for key, absent in (
                ("rule_date", missing_date),
                ("de_before_control_test", facts.de_before_control_test is None),
            )
            if absent
        ]
        if facts.de_before_control_test is not False and p is None:
            missing.append("power_kw")
        control = export = "missing_inputs" if missing else "outside_version"
        control_missing = list(missing)
        export_missing = list(missing)
        if not missing and not in_version:
            control = export = "outside_version"
        elif not missing:
            if facts.de_before_control_test is False:
                control = export = "not_this_phase"
            else:
                assert p is not None
                control = (
                    "fetch_and_reduce"
                    if p >= 100
                    else "reduce"
                    if p >= 25
                    else "no_requirement_in_9_2_1_2"
                )
                if p >= 100:
                    export = "no_60_percent_in_9_2_2b_3"
                elif facts.de_remuneration is None:
                    export = "missing_inputs"
                    export_missing.append("de_remuneration")
                elif facts.de_remuneration == "other":
                    export = "not_in_tariff"
                elif p <= 2 and facts.de_plug_in_exception is None:
                    export = "missing_inputs"
                    export_missing.append("de_plug_in_exception")
                elif p <= 2 and facts.de_plug_in_exception:
                    export = "exempt_plug_in"
                else:
                    export = "sixty_percent_conditionally"
        add("de_eeg_control", control, control_missing)
        add("de_eeg_export", export, export_missing)
    else:
        assert country == "AT"
        scope_missing = [
            key
            for key, absent in (
                ("rule_date", missing_date),
                ("power_kw", p is None),
                ("connection_voltage_kv", facts.connection_voltage_kv is None),
            )
            if absent
        ]
        scope = "missing_inputs" if scope_missing else "outside_version"
        klein = protection = change = scope
        protection_missing: list[str] = []
        change_missing: list[str] = []
        if not scope_missing:
            assert p is not None and facts.connection_voltage_kv is not None
            if in_version:
                # TOR Erzeuger Typ A v1.4 § 2.1: this part of the TOR covers new
                # or substantially changed generating installations with a
                # maximum capacity below 250 kW at a distribution-network
                # connection point below 110 kV. Both limits are exclusive in
                # the cited text ("kleiner als 250 kW", "unter 110 kV").
                in_scope = p < 250 and facts.connection_voltage_kv < 110
                scope = (
                    "in_scope_below_250_kw_and_110_kv" if in_scope else "outside_scope"
                )
                if not in_scope:
                    klein = protection = change = "outside_scope"
                else:
                    # § 2.1: installations whose maximum capacity in total is at
                    # most 0.8 kW are "Kleinsterzeugungsanlagen". They are
                    # exempt from this part except § 5.1.3 (LFSM-O), OVE EN
                    # 61000-3-2 and OVE EN 61000-3-3+A1+A2, must run at a fixed
                    # cos phi = 1, and need written notice to the network
                    # operator no later than two weeks before commissioning.
                    # The 0,8 kW figure is a decimal fraction, so it is compared
                    # exactly instead of through binary floating point.
                    klein = (
                        "kleinsterzeugungsanlage_two_weeks_notice"
                        if Decimal(str(p)) <= Decimal("0.8")
                        else "not_kleinsterzeugungsanlage"
                    )
                    # § 6.3.1: an external network disconnection protection is
                    # required above 30 kVA of the maximum capacity of the
                    # generating installations that can be operated at one
                    # network connection point of a network user in the
                    # low-voltage network; up to a total maximum capacity of 30
                    # kVA per connection point, automatic disconnection devices
                    # under OVE-Richtlinie R 25 may be used instead. The
                    # threshold is stated in kVA and is met at exactly 30 kVA,
                    # so only a value above it needs the external device.
                    # Footnote 30 there (same wording as footnote 26 in § 6.1.2):
                    # rated apparent power of AC-coupled storage that does not
                    # feed back into the network is not counted for this.
                    if facts.apparent_power_kva is None:
                        protection = "missing_inputs"
                        protection_missing = ["apparent_power_kva"]
                    else:
                        protection = (
                            "external_network_disconnection_protection"
                            if Decimal(str(facts.apparent_power_kva)) > Decimal(30)
                            else "automatic_disconnection_device_r25"
                        )
                    # § 2.2: a change is "wesentlich" when the electrical
                    # characteristics differ from the agreed state and can
                    # materially affect network operation. § 2.2 gives an
                    # increase of maximum capacity by more than 15 % as one
                    # example ("Wesentliche Änderungen können z.B. sein"), so
                    # staying within 15 % does not settle the question and is
                    # reported as unresolved rather than as a negative result.
                    if facts.at_existing_installation_change is None:
                        change = "missing_inputs"
                        change_missing = ["at_existing_installation_change"]
                    elif facts.at_existing_installation_change is False:
                        change = "new_installation"
                    elif facts.at_change_previous_power_kw is None:
                        change = "missing_inputs"
                        change_missing = ["at_change_previous_power_kw"]
                    elif Decimal(str(p)) > Decimal(
                        str(facts.at_change_previous_power_kw)
                    ) * Decimal("1.15"):
                        change = "substantial_change_power_increase_above_15_percent"
                    else:
                        change = "power_criterion_not_exceeded_other_criteria_open"
        # ElWG § 96(1): renewable generating installations and high-efficiency
        # CHP up to 20 kW of net active power are connected on a notification
        # ("Anzeige") to the distribution system operator. § 96(2): the
        # installation is to be connected when the operator confirms it in
        # writing or four weeks pass after a complete notification without a
        # decision. § 4.1 footnote 8 of the TOR keeps this quantity apart from
        # the maximum capacity: the net active power is irrelevant for the size
        # class, so it is a separate declaration and not derived from Pmax.
        # A reading is one dated package: the ElWG source keeps its own
        # effective date in the report, but the whole AT reading stays bounded
        # by the same verified window as the TOR part, so a date outside it
        # yields no partially evaluated result.
        connection = "missing_inputs"
        connection_missing: list[str] = []
        if not facts.net_active_power_kw:
            connection_missing = ["net_active_power_kw"]
        elif not in_version:
            connection = "outside_version"
        elif Decimal(str(facts.net_active_power_kw)) <= Decimal(20):
            connection = "notification_route_up_to_20_kw_net_active_power"
        else:
            connection = "network_access_contract_required_above_20_kw"
        # § 8.1: conformity is shown inside the operating-permit procedure. The
        # cited paths are an Austrian inverter-list entry (footnote 37), a test
        # report from a laboratory accredited under OVE/ÖNORM EN ISO/IEC 17025
        # for OVE-Richtlinie R 25 including the "Österreich" country settings,
        # or a VDE-AR-N 4105 / DIN VDE V 0124-100 report accepted only together
        # with the R 25-specific properties and the Austrian parameter
        # documentation (footnote 38). Which path a given device actually
        # satisfies needs the registry and document read-back, so a declared
        # basis stays conditional.
        if facts.at_conformity_basis is None:
            conformity = "missing_inputs"
            conformity_missing = ["at_conformity_basis"]
        elif not in_version:
            conformity = "outside_version"
            conformity_missing = []
        else:
            conformity = "declared_" + facts.at_conformity_basis
            conformity_missing = []
        add("at_tor_scope", scope, scope_missing)
        add("at_kleinsterzeugungsanlage", klein, scope_missing)
        add(
            "at_network_disconnection_protection",
            protection,
            scope_missing or protection_missing,
        )
        add("at_substantial_change", change, scope_missing or change_missing)
        sources.append(dict(_AT_ELWG_SOURCE))
        add(
            "at_connection_route",
            connection,
            connection_missing,
            origin=cast(str, _AT_ELWG_SOURCE["id"]),
        )
        sources.append(dict(_AT_CONFORMITY_SOURCE))
        add(
            "at_conformity_evidence",
            conformity,
            conformity_missing,
            origin=cast(str, _AT_CONFORMITY_SOURCE["id"]),
        )
    return {
        "schema_version": 1,
        "country_code": country,
        "rule_date": facts.rule_date,
        "inputs": cast(Object, facts.model_dump(mode="json")),
        "sources": sources,
        "checks": checks,
    }
