"""Project-declared grid evidence, distinct from rule verification and permission.

The source snapshot is the existing country dossier, not a newly retrieved raw
instrument. No threshold or 2026 certificate transition is inferred from it.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, cast
from urllib.parse import urlsplit

from pydantic import Field, field_validator

from .canonical import Json, Object
from .country_rules import review_country_rules
from .energy_inputs import Document, SchemaVersion

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
                "evidence_snapshot_date": "2026-10-28",
                "raw_sha256": None,
                "evidence_basis": "existing_country_dossier_primary_reading",
                "scope": "storage_in_dso_technical_requirements_and_tab_effectiveness",
            },
            {
                "id": "de_fnn_connection_scope",
                "source_url": "https://www.vde.com/de/fnn/themen/tar/tar-mittelspannung-vde-ar-n-4110",
                "title": "VDE FNN TAR Mittelspannung FAQ",
                "edition": "VDE-AR-N 4110:2023-09",
                "clause": "1 Anwendungsbereich",
                "evidence_snapshot_date": "2026-10-27",
                "raw_sha256": None,
                "evidence_basis": "existing_country_dossier_primary_reading",
                "scope": "connection_voltage_scope_differs_from_unit_electrical_evidence",
            },
        ]
        if is_de
        else []
    )
    result: Object = {
        "status": "unresolved",
        "country_code": country,
        "reason": "dso_tab_evidence_requires_independent_verification"
        if is_de
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
                }
                for check in cast(list[Json], review["checks"])
            ):
                result["numeric_rules"] = "partially_assessed"
    return result
