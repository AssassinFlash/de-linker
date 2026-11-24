"""The report, PDF, independent CSV and Genie consume one saved rule review."""

from __future__ import annotations

import csv
import io
from dataclasses import replace
from hashlib import sha256
from typing import cast

import pytest
from pypdf import PdfReader

from linker_engine.planning.assets import Assets
from linker_engine.planning.assistant_context import _result_rows, assistant_context
from linker_engine.planning.canonical import Object
from linker_engine.planning.equipment_assessment import assess_equipment
from linker_engine.planning.equipment_kernel import EquipmentKernel
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.product_sources import ProductSources
from linker_engine.planning.project_input_contracts import (
    ENGINEERING_V10_INPUT_CONTRACT,
)
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.report_copy import text
from linker_engine.planning.report_inputs import ReportOptions
from linker_engine.planning.report_kernel import ReportKernel, ReportService
from linker_engine.planning.worker import Worker
from linker_engine.planning.workspace import Workspace

from .conftest import FixtureObject, json_object
from .test_country_rules import rule_input
from .test_equipment import feed as feed
from .test_equipment import inputs
from .test_eu6_country_rules import EVIDENCE
from .test_grid_connection import declared


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("country", ["FR", "NL", "DE", "SE"])
def test_saved_rules_reach_all_consumers_and_remain_frozen(
    workspace: Workspace,
    owner: Actor,
    context: Context,
    feed: FixtureObject,
    monkeypatch: pytest.MonkeyPatch,
    locale: str,
    country: str,
) -> None:
    rule = {
        "FR": rule_input(
            "fr_generation_pmax",
            power_kw=11,
            connection_voltage_kv=0.4,
            fr_enedis_full_self_consumption=True,
        ),
        "NL": rule_input("nl_storage_max_active", power_kw=0.8),
        "DE": rule_input(
            "de_pv_installed",
            power_kw=2,
            de_before_control_test=True,
            de_remuneration="feed_in_or_tenant",
        ),
        "SE": rule_input(
            "se_rfg_maximum_capacity",
            power_kw=120,
            connection_voltage_kv=0.4,
            se_export_power_kw=40,
            se_existing_installation_change=True,
        ),
    }[country]
    values = cast(
        Object,
        {
            **inputs(feed, 3),
            **declared(country=country, complete=True),
            "country_rule_inputs": rule,
        },
    )
    grid = cast(Object, values["grid_connection"])
    grid["dso_name"] = "Enedis" if country == "FR" else "PRIVATE OPERATOR"
    grid["dso_source_url"] = "https://example.org/PRIVATE-OPERATOR"
    cast(Object, grid["tab"])["title"] = "PRIVATE TAB TITLE"
    project = workspace.create(
        owner,
        "Country report fixture",
        values,
        key="create",
        input_contract=ENGINEERING_V10_INPUT_CONTRACT,
    )
    proof = workspace.blobs.put_object(feed)
    equipment_context = replace(
        context, assets={**context.assets, "woo.equipment_inputs": proof}
    )
    equipment_run = workspace.evaluate(
        owner, project.id, 1, equipment_context, key="equipment", max_attempts=1
    )
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture-equipment", kinds=("evaluate",), lease_seconds=30)
    assert lease is not None
    assessment = assess_equipment(values, feed)
    jobs.complete(
        lease,
        {
            "kind": EquipmentKernel.kind,
            "assessment": assessment,
            "pinned_assets": cast(Object, equipment_context.assets),
            "runtime_sha256": equipment_context.code_sha256,
        },
    )

    products = ProductSources(lambda: pytest.fail("must use retained Woo proof"))
    monkeypatch.setattr(products, "confirm_bases", lambda *_args, **_kwargs: None)
    kernel = ReportKernel(workspace, products)
    options = ReportOptions.read(
        {
            "locale": locale,
            "energy_run_id": None,
            "pv_run_id": None,
            "equipment_run_id": equipment_run.id,
            "logo": None,
        }
    )
    report_run = ReportService(workspace, kernel, max_attempts=1).evaluate(
        owner, project.id, 1, options, key="report"
    )
    worker = Worker(
        jobs,
        "country-report-fixture",
        {"evaluate": kernel},
        lease_seconds=30,
        heartbeat_seconds=1,
        retry_seconds=1,
    )
    assert worker.run_once()
    completed = workspace.run(owner, report_run.id)
    assert completed.state == "succeeded", completed.error
    result = json_object(completed.result)
    sections = result["report"]["sections"]
    report_text = str(sections)
    review = json_object(json_object(assessment["country_assessment"])["rule_review"])
    checks = review["checks"]
    source_sha = result["pinned_assets"]["report.source"]
    expected = {
        "FR": "country_rule_fr_generation_type",
        "NL": "country_rule_nl_storage_lfsm",
        "DE": "country_rule_de_eeg_export",
        "SE": "country_rule_se_module_type",
    }[country]
    assert text(expected, locale) in report_text
    assert all(
        text(f"country_rule_{check['outcome']}", locale) in report_text
        for check in checks
    )
    assert text("country_rule_scope", locale) in report_text
    assert "PRIVATE TAB TITLE" in report_text
    crowded_report = {
        **result["report"],
        "sections": [
            {
                "id": "large-unrelated-section",
                "title": "Other details",
                "paragraphs": [],
                "rows": [
                    {"label": "Other", "value": str(index)} for index in range(300)
                ],
                "table": None,
            },
            *sections,
        ],
    }
    crowded_run = replace(completed, result={**result, "report": crowded_report})
    assert text(expected, locale) in str(
        _result_rows(workspace, crowded_run, locale)[:256]
    )

    assets = Assets(workspace)
    pdf = assets.content(owner, project.id, result["prepared_asset"]["id"])
    pdf_text = " ".join(
        page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages
    )
    date_condition = (
        "aktuell und zum Netzanschlussdatum des Projekts gelten"
        if locale == "de"
        else "apply today and on the project's grid connection date"
    )
    assert text(expected, locale) in pdf_text
    if country == "NL":
        lfsm_label = (
            "LFSM-U / Statik bei Unterfrequenz der niederländischen Speichereinheit"
            if locale == "de"
            else "Dutch storage-unit LFSM-U droop"
        )
        assert lfsm_label in report_text
        assert lfsm_label in pdf_text
    assert date_condition in " ".join(pdf_text.split())
    assert "2026-11-04" in pdf_text
    assert "PRIVATE TAB TITLE" in pdf_text
    attachments = result["prepared_attachments"]
    assert set(attachments) == {"bill_of_materials_csv", "country_rule_review_csv"}
    exported = attachments["country_rule_review_csv"]
    assert exported["metadata"]["dependencies"]["report_source"] == source_sha
    csv_bytes = assets.content(owner, project.id, exported["id"])
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig")))
    assert reader.fieldnames is not None
    assert (
        "Prüfung [check_label]" if locale == "de" else "Check [check_label]"
    ) in reader.fieldnames
    reader.fieldnames = [name.rsplit(" [", 1)[1][:-1] for name in reader.fieldnames]
    rows = list(reader)
    if country == "NL":
        assert any(row["check_label"] == lfsm_label for row in rows)
    assert [row["check_id"] for row in rows] == [check["id"] for check in checks]
    assert all(
        row["project_id"] == project.id
        and row["revision"] == "1"
        and row["report_source_sha256"] == source_sha
        for row in rows
    )
    assert all(
        row["source_text_sha256"] and row["source_url"].startswith("https://")
        for row in rows
    )
    assert all(row["scope"] == text("country_rule_scope", locale) for row in rows)
    assert all(date_condition in row["scope"] for row in rows)
    if country == "DE":
        assert all(
            "7dbf22b9f82a3bf380d25975e4d9fe9c68fa37c9feb4ee7972e3272f91f0b208"
            in row["grid_source_hashes"]
            and "4aea379ed9f11476d915b5f9baacad618b39209df9acd02c78c612418fe528c6"
            in row["grid_source_hashes"]
            for row in rows
        )
    assert "PRIVATE" not in csv_bytes.decode("utf-8-sig")
    assert exported["id"] != attachments["bill_of_materials_csv"]["id"]
    material_bytes = assets.content(
        owner, project.id, attachments["bill_of_materials_csv"]["id"]
    )
    assert b"source_text_sha256" not in material_bytes
    if country == "FR":
        assert {row["source_id"] for row in rows} == {
            "fr_arrete_article_35",
            "fr_enedis_total_self_consumption",
        }
        assert (
            "sworn declaration" not in report_text
            and "eidesstattliche" not in report_text
        )
    else:
        assert any(row["status"] == "unresolved" for row in rows)
    if country == "SE":
        # The three SE sources are separate instruments: the national code, the
        # EU regulation whose table it adopts, and the electricity act that
        # carries the connection duty.
        assert {row["source_id"] for row in rows} == {
            "se_eifs_2018_2",
            "se_rfg_2016_631",
            "se_ellagen_1997_857",
        }

    for selected in (equipment_run.id, completed.id):
        for language in ("en", "de"):
            shown = assistant_context(
                workspace, owner, project.id, 1, [selected], language
            )
            if selected == completed.id:
                assert (
                    "country_assessment" not in json_object(shown)["runs"][0]["scope"]
                )
            rendered = str(shown)
            assert "PRIVATE" not in rendered
            assert text(expected, language) in rendered
            if country == "NL":
                assert (
                    "LFSM-U / Statik bei Unterfrequenz"
                    if language == "de"
                    else "LFSM-U droop"
                ) in rendered
            assert text("country_rule_scope", language) in rendered
            assert (
                "aktuell und zum Netzanschlussdatum des Projekts gelten"
                if language == "de"
                else "apply today and on the project's grid connection date"
            ) in rendered
            assert all(
                source["title"] in rendered and source["text_sha256"] in rendered
                for source in review["sources"]
            )

    # Revisions cannot mutate an existing PDF, export or Genie projection.
    updated = {**values, "country_rule_inputs": {**rule, "power_kw": 1200}}
    workspace.revise(
        owner,
        project.id,
        1,
        updated,
        key="new-values",
        input_contract=ENGINEERING_V10_INPUT_CONTRACT,
    )
    assert assets.content(owner, project.id, exported["id"]) == csv_bytes
    assert assets.content(owner, project.id, result["prepared_asset"]["id"]) == pdf
    old = assistant_context(workspace, owner, project.id, 1, [completed.id], locale)
    assert text(expected, locale) in str(old)


def test_legacy_grid_review_has_no_country_rule_csv() -> None:
    from linker_engine.planning.grid_connection import country_assessment
    from linker_engine.planning.grid_connection_report import country_rule_csv

    assert (
        country_rule_csv(
            country_assessment(declared(complete=True)), "en", {}, "a" * 64
        )
        is None
    )


@pytest.mark.parametrize("locale", ["en", "de"])
def test_report_never_rounds_declared_power_across_a_rule_threshold(
    locale: str,
) -> None:
    from linker_engine.planning.grid_connection import country_assessment
    from linker_engine.planning.grid_connection_report import grid_connection_sections

    values = declared(country="FR", complete=True)
    values["country_rule_inputs"] = rule_input(
        "fr_generation_pmax", power_kw=999.9999, connection_voltage_kv=0.4
    )
    rendered = str(grid_connection_sections(country_assessment(values), locale))
    assert ("999,9999 kW" if locale == "de" else "999.9999 kW") in rendered
    assert text("country_rule_type_a", locale) in rendered


@pytest.mark.parametrize(
    ("locale", "heading"),
    [("en", "Grid connection review"), ("de", "Prüfung des Netzanschlusses")],
)
def test_known_pv_with_selected_equipment_prints_one_grid_review(
    feed: FixtureObject, locale: str, heading: str
) -> None:
    from linker_engine import pdf
    from linker_engine.planning.report_model import build_report

    values = inputs(feed, 3)
    values["equipment_selection"]["pv_dc_kw"] = 8
    values["brief"] = {"site": {"country_code": "DE"}}
    report = build_report(
        {
            "title": "Known PV size",
            "project_id": "de-known-pv",
            "input_sha256": "1" * 64,
            "revision": 1,
            "locale": locale,
            "generated_at": "2026-11-23T00:00:00Z",
            "source_runs": [],
            "brief": values["brief"],
            "equipment": assess_equipment(values, feed),
            "declared_pv_panels": {"count": 16, "stc_power_w": 500},
        }
    )
    ids = [section.id for section in report.sections]
    document = PdfReader(io.BytesIO(pdf.render(report)))
    extracted = "\n".join(page.extract_text() for page in document.pages)
    assert extracted.count(heading) == 1
    assert ids.count("grid-connection-evidence") == 1
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("locale", ["en", "de"])
def test_all_50_european_countries_report_official_sources_or_explicit_rule_gaps(
    locale: str,
) -> None:
    from linker_engine import geo, pdf
    from linker_engine.planning.grid_connection import (
        BUNDLED_RULE_COUNTRIES,
        bundled_country_sources,
        country_assessment,
    )
    from linker_engine.planning.grid_connection_report import grid_connection_sections
    from linker_engine.planning.report_copy import country_name
    from linker_engine.planning.report_model import build_report

    from .test_grid_connection import declared

    expected_frameworks = {
        "GB": "ENA Engineering Recommendation G98 / G99",
        "IT": "CEI 0-21 / CEI 0-16",
        "ES": "RD 244/2019",
        "CH": "VSE NA/EEA-CH",
        "PL": "PTPiREE IRiESD",
        "BE": "Synergrid C10/11",
        "PT": "E-Redes",
        "CZ": "PPDS",
        "IE": "ESB Networks NC6 / NC7",
        "DK": "Green Power Denmark TR 3.2.1 / TR 3.3.1",
        "FI": "Fingrid VJV",
        "NO": "FoL / REN",
    }

    for code in sorted(geo.countries()):
        name = country_name(code, locale)
        # Path 1: grid_connection filled (without country_rule_inputs)
        with_grid = country_assessment(declared(country=code, complete=True))
        sections = grid_connection_sections(with_grid, locale)
        evidence_section = next(
            s for s in sections if s.id == "grid-connection-evidence"
        )
        rendered = " ".join(
            [
                evidence_section.title,
                *evidence_section.paragraphs,
                *(f"{r.label} {r.value}" for r in evidence_section.rows),
            ]
        )
        assert name in rendered
        assert "sondern" not in rendered.lower()
        if code in BUNDLED_RULE_COUNTRIES:
            assert "No verified grid-connection rule pack" not in rendered
            assert "kein geprüftes Regelwerk" not in rendered
            for source in bundled_country_sources(code):
                assert str(source["title"]) in rendered
                assert str(source["clause"]) in rendered
                assert str(source["source_url"]) in rendered
        else:
            assert (
                "German TAB requirements are not assumed"
                if locale == "en"
                else "Deutsche TAB werden für dieses Projekt nicht vorausgesetzt"
            ) in rendered
            assert (
                "not bundled as an automated rule pack"
                if locale == "en"
                else "nicht als automatisiertes Regelwerk hinterlegt"
            ) in rendered
            if code in expected_frameworks:
                assert expected_frameworks[code] in rendered

        # Path 2: QuickStart / no grid_connection (`versioned_country_rules_required`)
        quick_source: Object = {
            "title": f"QuickStart {code}",
            "project_id": "0" * 32,
            "revision": 1,
            "input_sha256": "1" * 64,
            "locale": locale,
            "generated_at": "2026-11-16T00:00:00+00:00",
            "source_runs": [],
            "brief": {
                "site": {
                    "location_label": f"Site {code}",
                    "country_code": code,
                    "timezone": None,
                },
                "project_note": "",
            },
            "equipment": {
                "model": "woo_equipment_v1",
                "overall_status": "unresolved",
                "equipment_status": "unresolved",
                "selected_products": [],
                "checks": [],
                "provisional_bill_of_materials": [],
                "country_assessment": {
                    "status": "unresolved",
                    "country_code": code,
                    "reason": "versioned_country_rules_required",
                },
            },
        }
        report = build_report(quick_source)
        quick_section = next(
            s for s in report.sections if s.id == "grid-connection-evidence"
        )
        quick_text = " ".join(
            [
                quick_section.title,
                *quick_section.paragraphs,
                *(f"{r.label} {r.value}" for r in quick_section.rows),
            ]
        )
        assert name in quick_text
        assert text("country_open", locale) not in str(report.sections)
        if code in BUNDLED_RULE_COUNTRIES:
            source_rows = [
                row
                for section in report.sections
                if section.id in {"grid-connection-evidence", "grid-source-register"}
                for row in section.rows
            ]
            evidence_text = "\n".join(
                row.label + " " + row.value for row in source_rows
            )
            for source in bundled_country_sources(code):
                assert str(source["title"]) in evidence_text
                assert str(source["source_url"]) in evidence_text
                if source.get("text_sha256"):
                    assert str(source["text_sha256"]) in evidence_text
        elif code in expected_frameworks:
            assert expected_frameworks[code] in quick_text

    # Spot-check PDF rendering for bundled and non-bundled countries (no missing glyphs)
    for sample_code in ("DE", "FR", "NL", "AT", "SE", "GB", "IT", "CZ", "PL", "AX"):
        report = build_report(
            {
                "title": f"PDF {sample_code}",
                "project_id": "0" * 32,
                "revision": 1,
                "input_sha256": "1" * 64,
                "locale": locale,
                "generated_at": "2026-11-16T00:00:00+00:00",
                "source_runs": [],
                "brief": {
                    "site": {
                        "location_label": f"Site {sample_code}",
                        "country_code": sample_code,
                        "timezone": None,
                    },
                    "project_note": "",
                },
            }
        )
        doc = pdf.render(report)
        extracted = "\n".join(
            page.extract_text() for page in PdfReader(io.BytesIO(doc)).pages
        )
        assert country_name(sample_code, locale) in extracted
        assert "\x00" not in extracted and "■" not in extracted


@pytest.mark.parametrize("multiple", [False, True])
def test_g98_paperwork_cites_the_operator_procedure_in_report_and_csv(
    multiple: bool,
    feed: FixtureObject,
) -> None:
    from linker_engine import pdf
    from linker_engine.planning.grid_connection import country_assessment
    from linker_engine.planning.grid_connection_report import (
        country_rule_csv,
    )
    from linker_engine.planning.report_model import build_report

    values: Object = {**inputs(feed, 3), **declared(country="GB", complete=True)}
    values["country_rule_inputs"] = rule_input(
        "gb_lv_microgeneration",
        rule_date="2026-11-24",
        gb_in_great_britain=True,
        gb_permanently_wired=True,
        current_per_phase_a=16,
        gb_type_tested=True,
        gb_multiple_premises=multiple,
    )
    grid = country_assessment(values)
    report = build_report(
        {
            "title": "G98",
            "project_id": "g98",
            "input_sha256": "1" * 64,
            "revision": 1,
            "locale": "en",
            "generated_at": "2026-11-24T00:00:00Z",
            "source_runs": [],
            "brief": values["brief"],
            "equipment": assess_equipment(values, feed),
        }
    )
    detail = next(
        s for s in report.sections if s.id == "country-rule-gb_connection_route"
    )
    evidence = next(s for s in report.sections if s.id == "grid-source-register")
    dno = "https://connections.nationalgrid.co.uk/g98-connection-procedures"
    assert any(dno in row.value for row in detail.rows)
    assert any("EID=102993" in row.value for row in evidence.rows)

    document = PdfReader(io.BytesIO(pdf.render(report)))
    pdf_text = "".join("".join(page.extract_text().split()) for page in document.pages)
    assert "EID=102993" in pdf_text and dno in pdf_text

    source: Object = {"project_id": "g98", "revision": 1, "input_sha256": "inputs"}
    data = country_rule_csv(grid, "en", source, "report")
    assert data is not None
    headers, row = csv.reader(io.StringIO(data.decode("utf-8-sig")))
    fields = {
        h.split("[")[-1].rstrip("]"): value
        for h, value in zip(headers, row, strict=True)
    }
    assert fields["outcome"] == (
        "gb_cluster_agreement" if multiple else "gb_single_g98_notice"
    )
    assert fields["source_url"] == dno
    assert (
        fields["source_text_sha256"]
        == sha256((EVIDENCE / "dno-excerpts.txt").read_bytes()).hexdigest()
    )
