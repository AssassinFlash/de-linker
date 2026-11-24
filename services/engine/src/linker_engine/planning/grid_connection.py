"""Project-declared grid evidence, distinct from rule verification and permission.

The source snapshot is the existing country dossier, not a newly retrieved raw
instrument. No threshold or 2026 certificate transition is inferred from it.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, cast
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from . import eu_connection_rules as eu_rules
from .canonical import Json, Object
from .country_rules import (
    _AT_CONFORMITY_SOURCE,
    _AT_ELWG_SOURCE,
    _ENEDIS_SOURCE,
    _SE_ELLAGEN_SOURCE,
    _SE_RFG_SOURCE,
    review_country_rules,
)
from .country_rules import (
    _SOURCES as _COUNTRY_RULE_SOURCES,
)
from .energy_inputs import Document, SchemaVersion

BUNDLED_RULE_COUNTRIES: frozenset[str] = frozenset(
    {"DE", "FR", "NL", "AT", "SE", *eu_rules.CHECKS}
)

_FRAMEWORKS: dict[str, str] = {
    "DE": "EnWG §19; VDE-AR-N 4110:2023-09; EEG 2023 § 9",
    "FR": "Arrêté du 9 juin 2020 (Art. 35); Enedis CACSI",
    "NL": "Systeemcode elektriciteit 2026 (Art. 2.9)",
    "AT": "TOR Stromerzeugungsanlagen Typ A v1.4; ElWG",
    "SE": "EIFS 2018:2; EU 2016/631 (RfG); Ellagen (1997:857)",
    "GB": "ENA ER G98 / G99 & DNO application",
    "IT": "CEI 0-21 / CEI 0-16 & DSO TICA",
    "ES": "RD 244/2019; RD 1183/2020; UNE 217002",
    "CH": "VSE NA/EEA-CH & ESTI / DSO rules",
    "PL": "EU 2016/631 (RfG) & PTPiREE IRiESD",
    "BE": "Synergrid C10/11 & regional DSO rules",
    "PT": "DGEG & E-Redes technical rules",
    "CZ": "PPDS Annex 4 (Priloha c. 4)",
    "IE": "ESB Networks NC6 / NC7 & Distribution Code",
    "DK": "Green Power Denmark TR 3.2.1 / TR 3.3.1",
    "FI": "Fingrid VJV & local DSO rules",
    "NO": "FoL / REN & local DSO rules",
}

_EU_RFG_COUNTRIES: frozenset[str] = frozenset(
    {"BG", "CY", "EE", "GR", "HR", "HU", "LT", "LU", "LV", "MT", "RO", "SI", "SK"}
)

_OTHER_EUROPEAN_COUNTRIES: frozenset[str] = frozenset(
    {
        "AD",
        "AL",
        "AX",
        "BY",
        "FO",
        "GG",
        "GI",
        "IM",
        "IS",
        "JE",
        "LI",
        "MC",
        "MD",
        "MK",
        "RS",
        "RU",
        "SJ",
        "SM",
        "UA",
        "VA",
    }
)


def rule_gap_metadata(country: str | None) -> Object:
    code = country.upper() if isinstance(country, str) and country else None
    bundled = code in BUNDLED_RULE_COUNTRIES
    if code is None:
        gap_code = "site_country_not_specified"
        framework: str | None = None
    elif bundled:
        gap_code = "bundled_rule_pack_available"
        framework = _FRAMEWORKS[code]
    else:
        gap_code = f"country_rule_pack_missing_{code.lower()}"
        if code in _FRAMEWORKS:
            framework = _FRAMEWORKS[code]
        elif code in _EU_RFG_COUNTRIES:
            framework = "EU 2016/631 (RfG) national implementation & local DSO rules"
        elif code in _OTHER_EUROPEAN_COUNTRIES:
            framework = "National network code & local grid operator conditions"
        else:
            framework = "Local grid operator connection conditions"
    return {
        "country_code": code,
        "bundled_rule_pack": bundled,
        "gap_code": gap_code,
        "framework": framework,
    }


def bundled_country_sources(country: str | None) -> list[Object]:
    if not isinstance(country, str):
        return []
    code = country.upper()
    if code == "GB":
        return [dict(_COUNTRY_RULE_SOURCES[code]), dict(eu_rules.GB_DNO_SOURCE)]
    if code in eu_rules.CHECKS:
        return [dict(_COUNTRY_RULE_SOURCES[code])]
    if code == "DE":
        return [
            {
                "id": "de_enwg_19_dso_tab",
                "source_url": "https://www.gesetze-im-internet.de/enwg_2005/__19.html",
                "title": "EnWG §19 Technische Vorschriften",
                "edition": None,
                "clause": "19(1), 19(1a)",
                "evidence_snapshot_date": "2026-11-04",
            },
            {
                "id": "de_fnn_connection_scope",
                "source_url": "https://www.vde.com/de/fnn/themen/tar/tar-mittelspannung-vde-ar-n-4110",
                "title": "VDE FNN TAR Mittelspannung FAQ",
                "edition": "VDE-AR-N 4110:2023-09",
                "clause": "1 Anwendungsbereich",
                "evidence_snapshot_date": "2026-11-04",
            },
            dict(_COUNTRY_RULE_SOURCES["DE"]),
        ]
    if code == "FR":
        return [dict(_COUNTRY_RULE_SOURCES["FR"]), dict(_ENEDIS_SOURCE)]
    if code == "NL":
        return [dict(_COUNTRY_RULE_SOURCES["NL"])]
    if code == "AT":
        return [
            dict(_COUNTRY_RULE_SOURCES["AT"]),
            dict(_AT_ELWG_SOURCE),
            dict(_AT_CONFORMITY_SOURCE),
        ]
    if code == "SE":
        return [
            dict(_COUNTRY_RULE_SOURCES["SE"]),
            dict(_SE_RFG_SOURCE),
            dict(_SE_ELLAGEN_SOURCE),
        ]
    return []


# Private project text/URL transport limits, not engineering restrictions.
type Text = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"\S")]


class TabSource(Document):
    title: Text | None
    source_url: Text | None
    edition: Text | None
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")] | None

    @field_validator("source_url")
    @classmethod
    def source_address(cls, value: str | None) -> str | None:
        return _source_url(value)

    @field_validator("date")
    @classmethod
    def calendar_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


class GridConnection(Document):
    schema_version: SchemaVersion
    dso_name: Text | None
    dso_source_url: Text | None
    voltage_level: Literal["low", "medium", "high"] | None
    tab: TabSource

    @field_validator("dso_source_url")
    @classmethod
    def source_address(cls, value: str | None) -> str | None:
        return _source_url(value)


def _source_url(value: str | None) -> str | None:
    if value is not None:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(character.isspace() for character in value)
        ):
            raise ValueError("an HTTP(S) source URL without credentials is required")
    # This is an inert citation: no request, download or automatic verification.
    return value


def validate_grid_connection(inputs: Object) -> None:
    if "grid_connection" in inputs:
        GridConnection.read(inputs["grid_connection"])


def country_assessment(inputs: Object) -> Object:
    brief = inputs.get("brief")
    site = brief.get("site") if isinstance(brief, dict) else None
    country = site.get("country_code") if isinstance(site, dict) else None
    legacy: Object = {
        "status": "unresolved",
        "country_code": country,
        "reason": "versioned_country_rules_required",
    }
    if "grid_connection" not in inputs:
        # Historical inputs retain their original result shape and semantics.
        return legacy
    facts = GridConnection.read(inputs["grid_connection"])
    declared = cast(Object, facts.model_dump(mode="json"))
    is_de = country == "DE"
    checks: list[Json] = []

    def add(identifier: str, present: bool, reason: str) -> None:
        checks.append(
            {
                "id": identifier,
                "status": "provided" if present else "unresolved",
                "reason": reason,
            }
        )

    add(
        "responsible_dso",
        facts.dso_name is not None and facts.dso_source_url is not None,
        "project_declaration_requires_operator_territory_verification",
    )
    add(
        "connection_voltage",
        facts.voltage_level is not None,
        "voltage_is_at_the_grid_connection_point_not_device_terminals",
    )
    add(
        "applicable_tab",
        facts.tab.source_url is not None
        and (facts.tab.edition is not None or facts.tab.date is not None),
        "project_source_and_edition_or_date_are_not_verified_applicability",
    )
    add(
        "independent_dso_tab_verification",
        False,
        "dso_territory_voltage_edition_and_project_applicability_not_verified",
    )
    add(
        "connection_permission",
        False,
        "project_grid_assessment_and_operator_permission_require_separate_evidence",
    )
    sources: list[Json] = (
        [
            {
                "id": "de_enwg_19_dso_tab",
                "source_url": "https://www.gesetze-im-internet.de/enwg_2005/__19.html",
                "title": "EnWG §19 Technische Vorschriften",
                "edition": None,
                "clause": "19(1), 19(1a)",
                "evidence_snapshot_date": "2026-11-04",
                "raw_sha256": "7dbf22b9f82a3bf380d25975e4d9fe9c68fa37c9feb4ee7972e3272f91f0b208",
                "evidence_basis": "current_official_text_reading",
                "scope": "storage_in_dso_technical_requirements_and_tab_effectiveness",
            },
            {
                "id": "de_fnn_connection_scope",
                "source_url": "https://www.vde.com/de/fnn/themen/tar/tar-mittelspannung-vde-ar-n-4110",
                "title": "VDE FNN TAR Mittelspannung FAQ",
                "edition": "VDE-AR-N 4110:2023-09",
                "clause": "1 Anwendungsbereich",
                "evidence_snapshot_date": "2026-11-04",
                "raw_sha256": "4aea379ed9f11476d915b5f9baacad618b39209df9acd02c78c612418fe528c6",
                "evidence_basis": "current_official_text_reading",
                "scope": "connection_voltage_scope_differs_from_unit_electrical_evidence",
            },
        ]
        if is_de
        else []
    )
    country_str = country if isinstance(country, str) else None
    is_bundled = (
        country_str is not None and country_str.upper() in BUNDLED_RULE_COUNTRIES
    )
    result: Object = {
        "status": "unresolved",
        "country_code": country,
        "reason": "dso_tab_evidence_requires_independent_verification"
        if is_de
        else "bundled_country_rules_require_inputs"
        if is_bundled
        else "country_rules_not_available",
        "model": "declared_grid_connection_evidence_v1",
        "project_facts": declared,
        "declaration_status": "project_provided_not_independently_verified",
        "checks": checks,
        "missing_inputs": [
            identifier
            for identifier, present in (
                ("country_code", country is not None),
                ("dso_name", facts.dso_name is not None),
                ("dso_source_url", facts.dso_source_url is not None),
                ("voltage_level", facts.voltage_level is not None),
                ("tab.source_url", facts.tab.source_url is not None),
                (
                    "tab.edition_or_date",
                    facts.tab.edition is not None or facts.tab.date is not None,
                ),
            )
            if not present
        ],
        "rule_sources": sources,
        "rule_gap": rule_gap_metadata(country_str),
        "independent_verification": "not_assessed",
        "connection_permission": "not_established",
        "numeric_rules": "not_assessed",
        "standard_transition": "not_assessed",
    }
    if "country_rule_inputs" in inputs:
        review = review_country_rules(
            country if isinstance(country, str) else None,
            inputs["country_rule_inputs"],
            operator=facts.dso_name,
            voltage_level=facts.voltage_level,
        )
        if review is not None:
            result["rule_review"] = review
            result["reason"] = "country_rules_require_project_verification"
            if any(
                isinstance(check, dict)
                and check.get("status") == "conditional"
                and check.get("id")
                in {
                    "fr_generation_type",
                    "nl_storage_type",
                    "nl_storage_lfsm",
                    "de_eeg_control",
                    "de_eeg_export",
                    "at_tor_scope",
                    "at_kleinsterzeugungsanlage",
                    "at_network_disconnection_protection",
                    "at_substantial_change",
                    "at_connection_route",
                    "at_conformity_evidence",
                    "se_module_type",
                    "se_frequency_range",
                    "se_lfsm_o",
                    "se_voltage_range",
                    "se_automatic_reconnection",
                    "se_existing_change",
                    "se_connection_duty",
                    *eu_rules.CHECKS.values(),
                }
                for check in cast(list[Json], review["checks"])
            ):
                result["numeric_rules"] = "partially_assessed"
    return result
