"""Versioned, conditional readings of selected national connection rules.

These checks use project-declared quantities, not inferred equipment ratings.
They do not establish project applicability, operator acceptance or permission.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, cast

from pydantic import Field, field_validator

from .canonical import Json, Object
from .energy_inputs import Document, SchemaVersion
from .errors import InvalidInput

type Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
type Basis = Literal["fr_generation_pmax", "nl_storage_max_active", "de_pv_installed"]


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

    @field_validator("rule_date")
    @classmethod
    def calendar_date(cls, value: str | None) -> str | None:
        if value is not None:
            date.fromisoformat(value)
        return value


# These are the exact official-source text extractions recorded in
# docs/research/2026-10-23-modern-workbench/COUNTRY-EVIDENCE.md. The dates
# delimit the version actually read; they are not future legal assurances.
_SOURCES: dict[str, Object] = {
    "FR": {
        "id": "fr_arrete_article_35",
        "title": "Arrêté du 9 juin 2020",
        "source_url": "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042036860",
        "edition": "2020-06-26",
        "clause": "Article 35",
        "effective_from": "2020-06-26",
        "evidence_snapshot_date": "2026-11-01",
        "text_sha256": "4d35445b56b2d705e6afb81e93a4beec10f896ffcd3f14b1e69feda61794dfb3",
    },
    "NL": {
        "id": "nl_systeemcode_article_2_9",
        "title": "Systeemcode elektriciteit 2026",
        "source_url": "https://wetten.overheid.nl/BWBR0052336/2026-10-01",
        "edition": "2026-10-01",
        "clause": "Article 2.9(3)(a), (g)",
        "effective_from": "2026-10-01",
        "evidence_snapshot_date": "2026-11-01",
        "text_sha256": "d20979cca5d06af7da83962f2a6afaef8112fe2cf2411ec540e84b08436831e0",
    },
    "DE": {
        "id": "de_eeg_section_9",
        "title": "EEG 2023",
        "source_url": "https://www.gesetze-im-internet.de/eeg_2014/__9.html",
        "edition": None,
        "clause": "§ 9(2), (3)",
        "effective_from": None,
        "evidence_snapshot_date": "2026-11-01",
        "text_sha256": "dfbff2f705291e19c119bcbefec5ed046917044e20a8c20d43e993000df3958f",
    },
}

_BASIS_COUNTRY: dict[str, str] = {
    "fr_generation_pmax": "FR",
    "nl_storage_max_active": "NL",
    "de_pv_installed": "DE",
}

_ENEDIS_SOURCE: Object = {
    "id": "fr_enedis_total_self_consumption",
    "title": "Enedis: autoconsommation totale",
    "source_url": "https://www.enedis.fr/autoconsommer-la-totalite-de-lenergie-produite-par-vos-panneaux",
    "edition": None,
    "clause": "Déclarer mon installation, CACSI",
    "effective_from": None,
    "evidence_snapshot_date": "2026-11-01",
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
    start = cast(str | None, source["effective_from"])
    through = cast(str, source["evidence_snapshot_date"])
    in_version = facts.rule_date is not None and (
        (start <= facts.rule_date <= through)
        if start is not None
        else facts.rule_date == through
    )
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
            enedis_outcome = (
                "missing_inputs"
                if missing_date
                else "outside_version"
                if facts.rule_date != _ENEDIS_SOURCE["evidence_snapshot_date"]
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
    else:
        missing = [
            key
            for key, absent in (
                ("rule_date", missing_date),
                ("de_before_control_test", facts.de_before_control_test is None),
            )
            if absent
        ]
        control = export = "missing_inputs" if missing else "outside_version"
        control_missing = list(missing)
        export_missing = list(missing)
        if not missing and in_version:
            if facts.de_before_control_test is False:
                control = export = "not_this_phase"
            elif p is None:
                control = export = "missing_inputs"
                control_missing.append("power_kw")
                export_missing.append("power_kw")
            else:
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
    return {
        "schema_version": 1,
        "country_code": country,
        "rule_date": facts.rule_date,
        "inputs": cast(Object, facts.model_dump(mode="json")),
        "sources": sources,
        "checks": checks,
    }
