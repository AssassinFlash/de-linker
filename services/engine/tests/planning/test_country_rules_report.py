"""The report, PDF, independent CSV and Genie consume one saved rule review."""

from __future__ import annotations

import csv
import io
from dataclasses import replace
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
from linker_engine.planning.project_input_contracts import ENGINEERING_V10_INPUT_CONTRACT
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
from .test_grid_connection import declared


@pytest.mark.parametrize("locale", ["en", "de"])
@pytest.mark.parametrize("country", ["FR", "NL", "DE"])
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
            "pinned_assets": equipment_context.assets,
            "runtime_sha256": equipment_context.code_sha256,
        },
    )

    products = ProductSources(lambda: pytest.fail("must use retained Woo proof"))
    monkeypatch.setattr(products, "confirm_basis", lambda *_args, **_kwargs: None)
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
    expected = (
        "country_rule_fr_generation_type"
        if country == "FR"
        else "country_rule_nl_storage_lfsm"
        if country == "NL"
        else "country_rule_de_eeg_export"
    )
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
    assert "2026-11-01" in pdf_text
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

    for selected in (equipment_run.id, completed.id):
        for language in ("en", "de"):
            shown = assistant_context(
                workspace, owner, project.id, 1, [selected], language
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
