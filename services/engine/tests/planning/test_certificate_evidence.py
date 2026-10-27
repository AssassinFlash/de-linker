"""Certificate lookup reuses immutable sources and never upgrades applicability."""

from __future__ import annotations

import copy
import io
from typing import cast

import pytest
from reportlab.pdfgen.canvas import Canvas

from linker_engine.planning.canonical import Object, digest, encode
from linker_engine.planning.certificate_declarations import inspect_certificate
from linker_engine.planning.certificate_evidence import (
    CertificateEvidence,
    certificate_documents,
)
from linker_engine.planning.certificate_information import (
    report_source_with_information,
)
from linker_engine.planning.certificate_report import certificate_sections
from linker_engine.planning.certificate_sources import (
    InspectionUnavailable,
    download_certificate,
    inspect_report_certificates,
)
from linker_engine.planning.equipment_condition_inputs import (
    ConditionBindingChanged,
    ConditionPreparationRequired,
    ConditionRevisionChanged,
    validate_condition_inputs,
)
from linker_engine.planning.equipment_conditions import review_device_conditions
from linker_engine.planning.errors import (
    InvalidInput,
    NotFound,
    ProductEvidenceChanged,
    VersionUnavailable,
)
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context
from linker_engine.planning.workspace import Workspace


def evidence() -> tuple[Object, Object]:
    # Synthetic identities exercise binding, not any product certification.
    document: Object = {
        "document_id": "doc-recorded",
        "document_revision": "d" * 64,
        "blob_sha256": "b" * 64,
        "url": "https://de-linker.com/wp-content/uploads/2026/certificate.pdf",
        "title": "Recorded unit certificate",
        "lang": "en",
        "type": "certificate",
        "product_ids": [1, 2],
    }
    basis: Object = {
        "products": [
            {
                "canonical_product_id": identity,
                "product_revision": "a" * 64,
                "model": f"Fixture-{identity}",
                "brand": "Fixture",
                "documents": [document],
            }
            for identity in (1, 2)
        ]
    }
    assessment: Object = {
        "selected_products": [
            {"product_id": identity, "product_revision": "a" * 64}
            for identity in (1, 2)
        ],
        "checks": [],
    }
    return basis, assessment


def test_shared_certificate_keeps_exact_selected_source_and_report_scope() -> None:
    basis, assessment = evidence()
    result = certificate_documents(basis, assessment)
    docs = cast(list[Object], result["documents"])
    assert len(docs) == 1 and docs[0]["product_ids"] == [1, 2]
    assert result["applicability"] == "not_assessed"
    section = certificate_sections(result, "de")[0]
    assert "nicht geprüft" in section.paragraphs[0]
    assert (
        section.rows[0].href
        and "linker_document_sha256=" + "b" * 64 in section.rows[0].href
    )
    cast(list[Object], assessment["selected_products"])[0]["product_revision"] = (
        "e" * 64
    )
    with pytest.raises(VersionUnavailable):
        certificate_documents(basis, assessment)


def test_owned_old_run_reads_without_jobs_or_rewriting_sources(
    workspace: Workspace, owner: Actor, context: Context
) -> None:
    basis, assessment = evidence()
    recorded = inspected_fixture(workspace)
    original = cast(list[Object], recorded["documents"])[0]
    for product in cast(list[Object], basis["products"]):
        cast(list[Object], product["documents"])[0]["blob_sha256"] = original[
            "blob_sha256"
        ]
    inputs = condition_project()
    recorded["condition_review"] = review_device_conditions(inputs, recorded)
    proof = workspace.blobs.put_object(basis)
    pinned = Context(
        context.code_sha256,
        context.models,
        {**context.assets, "woo.equipment_inputs": proof},
        context.parameters,
    )
    project = workspace.create(owner, "Certificate fixture", inputs, key="new")
    run = workspace.evaluate(owner, project.id, 1, pinned, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease
    jobs.complete(
        lease,
        {
            "kind": "qualify_woo_equipment_v1",
            "assessment": assessment,
            "certificates": recorded,
            "dependencies": {"certificate.doc-recorded.raw": original["blob_sha256"]},
        },
    )
    workspace.revise(owner, project.id, 1, {"later": True}, key="edit")
    with workspace.database.read() as c:
        before = list(c.iterdump())
    result = CertificateEvidence(workspace).read(owner, run.id)
    assert result["revision"] == 1 and result["basis_sha256"] == proof
    assert result["condition_review"] == recorded["condition_review"]
    with pytest.raises(NotFound):
        CertificateEvidence(workspace).read(Actor("guest", "another"), run.id)
    with workspace.database.read() as c:
        assert list(c.iterdump()) == before


def test_absent_certificate_is_distinct_from_a_broken_association() -> None:
    basis, assessment = evidence()
    for product in cast(list[Object], basis["products"]):
        product["documents"] = []
    assert certificate_documents(basis, assessment)["documents"] == []
    basis, assessment = evidence()
    product = cast(list[Object], basis["products"])[0]
    cast(list[Object], product["documents"])[0]["product_ids"] = []
    with pytest.raises(VersionUnavailable):
        certificate_documents(basis, assessment)


def certificate_pdf(
    *,
    models: str = "Fixture-1, Fixture-2",
    firmware: str = "010101",
    extra: tuple[str, ...] = (),
) -> bytes:
    stream = io.BytesIO()
    canvas = Canvas(stream)
    line = canvas.beginText(40, 780)
    for text in (
        "Identification: Type Designation : " + models,
        "Firmware Version : " + firmware,
        "Remark: Refer to report TEST-1 for details.",
        "Tested acc. to: VDE-AR-N 4105/11.18",
        "The certificate is comprised of 1 page and an Annex of 164 pages.",
        "Unrelated footer note: EN 50549-2:2099",
        *extra,
    ):
        line.textLine(text)
    canvas.drawText(line)
    canvas.save()
    return stream.getvalue()


def test_literal_declarations_retain_bytes_and_never_grant_applicability(
    workspace: Workspace,
) -> None:
    basis, assessment = evidence()
    source = certificate_documents(basis, assessment)
    document = cast(list[Object], source["documents"])[0]
    content = certificate_pdf()
    document["blob_sha256"] = digest(content)
    report: Object = {"certificates": source, "dependencies": {}}
    seed_sha = workspace.blobs.put_object(report)
    calls = []

    def load(doc: Object) -> bytes:
        calls.append(doc["document_id"])
        return content

    originals = inspect_report_certificates(
        report, workspace.blobs, lambda: None, load=load
    )
    inspect_report_certificates(report, workspace.blobs, lambda: None, load=load)
    assert calls == ["doc-recorded"]  # Same original reused across report attempts.
    inspection = cast(Object, cast(Object, source["inspections"])["doc-recorded"])
    assert inspection["applicability"] == "not_assessed"
    assert cast(Object, inspection["annex"])["retained_pdf_pages"] == 1
    fields = {
        row["kind"]: row["value"]
        for row in cast(list[Object], inspection["declarations"])
    }
    assert fields["firmware"] == "010101"
    assert "4105/11.18" in str(fields["standards"])
    assert "2026" not in str(fields["standards"])
    assert "2099" not in str(fields["standards"])
    for locale in ("en", "de"):
        section = certificate_sections(source, locale)[0]
        assert any("164" in row.value for row in section.rows)
        assert any(row.value == "010101" for row in section.rows)
    bundle: Object = {
        "schema_version": 1,
        "kind": "certificate_cover_information_v1",
        "report_source_sha256": seed_sha,
        "evidence": source,
        "dependencies": {"report_source": seed_sha, **originals},
    }
    frozen: Object = {
        "report_source": seed_sha,
        "certificate_inspection": workspace.blobs.put_object(bundle),
    }
    assert (
        report_source_with_information(workspace.blobs, frozen)["certificates"]
        == source
    )
    inspection["document_revision"] = "c" * 64
    frozen["certificate_inspection"] = workspace.blobs.put_object(bundle)
    with pytest.raises(VersionUnavailable):
        report_source_with_information(workspace.blobs, frozen)
    with pytest.raises(ProductEvidenceChanged):
        inspect_certificate(content + b" changed", document)
    with pytest.raises(InspectionUnavailable):
        download_certificate({**document, "url": "https://other.invalid/private.pdf"})


def condition_project() -> Object:
    return {
        "equipment_selection": {
            "schema_version": 1,
            "inverter_product_id": 1,
            "battery_product_id": 2,
            "modules_per_stack": None,
            "parallel_stacks": None,
            "accessory_product_ids": [],
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": None,
            "required_usable_kwh": None,
            "required_discharge_ac_kw": None,
            "product_revisions": {"1": "a" * 64, "2": "a" * 64},
        },
        "equipment_condition_inputs": {
            "schema_version": 1,
            "devices": [
                {
                    "selection_ref": {"kind": "single", "role": "inverter"},
                    "product_id": 1,
                    "product_revision": "a" * 64,
                    "declared_model": None,
                    "declared_firmware": "010101",
                    "source_note": "Fixture project observation; not a manufacturer fact.",
                }
            ],
        },
    }


def inspected_fixture(workspace: Workspace, *, firmware: str = "010101") -> Object:
    basis, assessment = evidence()
    content = certificate_pdf(firmware=firmware)
    for product in cast(list[Object], basis["products"]):
        cast(list[Object], product["documents"])[0]["blob_sha256"] = (
            workspace.blobs.put(content)
        )
    result = certificate_documents(basis, assessment)
    inspect_report_certificates(
        {"certificates": result},
        workspace.blobs,
        lambda: None,
        load=lambda _: pytest.fail("retained original must be reused"),
    )
    return result


def test_observations_save_unknowns_preserve_old_hashes_and_refuse_stale_bindings(
    workspace: Workspace,
    owner: Actor,
) -> None:
    legacy = workspace.create(owner, "Unchanged", {}, key="legacy")
    assert legacy.input_sha256 == digest(encode({})) and legacy.inputs == {}
    inputs = condition_project()
    observations = cast(Object, inputs["equipment_condition_inputs"])
    device = cast(list[Object], observations["devices"])[0]
    device.update(
        declared_model=" Fixture-1 ",
        declared_firmware=" 010101\t",
        source_note="\tSource \n",
    )
    preserved = validate_condition_inputs(inputs)
    assert (
        preserved is not None and preserved.devices[0].model_dump(mode="json") == device
    )
    device.update(declared_model="", declared_firmware=" \t", source_note="\n")
    with pytest.raises(
        InvalidInput, match=r"declared_model.*declared_firmware.*source_note"
    ):
        workspace.create(owner, "Blank observations", inputs, key="blank-observations")
    device.update(declared_model=None, declared_firmware=None, source_note=None)
    project = workspace.create(owner, "Unknown conditions", inputs, key="conditions")
    assert project.inputs == inputs
    assert (
        workspace.create(owner, "Unknown conditions", inputs, key="conditions")
        == project
    )
    editable = copy.deepcopy(inputs)
    setup = cast(Object, editable.pop("equipment_selection"))
    setup.pop("product_revisions")
    setup["pv_dc_kw"] = 99
    editable["equipment_setup"] = setup
    changed = workspace.revise(owner, project.id, 1, editable, key="demand-only")
    assert changed.inputs["equipment_condition_inputs"] == observations
    with pytest.raises(ConditionPreparationRequired):
        validate_condition_inputs(editable, require_prepared=True)
    with pytest.raises(ConditionPreparationRequired):
        validate_condition_inputs(
            {**inputs, "equipment_setup": setup}, require_prepared=True
        )
    setup["inverter_product_id"] = 9
    with pytest.raises(ConditionBindingChanged):
        workspace.revise(owner, project.id, 2, editable, key="different-product")
    stale = copy.deepcopy(inputs)
    cast(Object, cast(Object, stale["equipment_selection"])["product_revisions"])[
        "1"
    ] = "c" * 64
    with pytest.raises(ConditionRevisionChanged):
        workspace.revise(owner, project.id, 2, stale, key="different-revision")
    observations["devices"] = []
    assert validate_condition_inputs(inputs) is not None


@pytest.mark.parametrize(
    ("printed", "observed", "expected"),
    [
        ("010101", "010101", "exact_match"),
        ("010101", "10101", "conflict"),
        ("V1.023", "v1.023", "conflict"),
        ("010101-R1", "010101-R1", "exact_match"),
        ("010101-020202", "010101", "unresolved"),
        ("010101, 020202", "010101", "unresolved"),
        ("010101+020202", "010101", "unresolved"),
        ("DIgSILENT PowerFactory 2024", "010101", "unresolved"),
        ("010101", None, "unresolved"),
    ],
)
def test_literal_firmware_never_coerces_or_expands_versions(
    workspace: Workspace,
    printed: str,
    observed: str | None,
    expected: str,
) -> None:
    source = inspected_fixture(workspace, firmware=printed)
    inputs = condition_project()
    device = cast(
        list[Object], cast(Object, inputs["equipment_condition_inputs"])["devices"]
    )[0]
    device["declared_firmware"] = observed
    review = review_device_conditions(inputs, source)
    documents = cast(
        list[Object], cast(list[Object], review["devices"])[0]["documents"]
    )
    firmware = cast(Object, documents[0]["firmware"])
    assert firmware["status"] == expected and firmware["compared_value"] == observed
    assert review["applicability"] == "not_assessed"
    assert "dso_permission" in cast(list[str], review["remaining_obligations"])


def test_conflicting_documents_stay_separate_and_annex_never_passes(
    workspace: Workspace,
) -> None:
    source = inspected_fixture(workspace)
    first = cast(list[Object], source["documents"])[0]
    second: Object = {
        **first,
        "document_id": "doc-unrelated",
        "document_revision": "c" * 64,
        "product_ids": [1],
    }
    content = certificate_pdf(models="Unrelated-9", firmware="010102")
    second["blob_sha256"] = workspace.blobs.put(content)
    cast(list[Object], source["documents"]).append(second)
    inspect_report_certificates({"certificates": source}, workspace.blobs, lambda: None)
    inputs = condition_project()
    cast(list[Object], cast(Object, inputs["equipment_condition_inputs"])["devices"])[
        0
    ]["declared_firmware"] = "010102"
    review = review_device_conditions(inputs, source)
    device = cast(list[Object], review["devices"])[0]
    documents = cast(list[Object], device["documents"])
    assert [cast(Object, d["firmware"])["status"] for d in documents] == [
        "conflict",
        "exact_match",
    ]
    assert [cast(Object, d["model"])["status"] for d in documents] == [
        "listed",
        "not_listed",
    ]
    assert all(
        d["applicability"] == "not_assessed"
        and cast(Object, d["annex"])["status"] == "unresolved"
        for d in documents
    )
    assert (
        len(cast(list[Object], cast(list[Object], review["devices"])[1]["documents"]))
        == 1
    )
    # A family file can name two models; naming a different listed model never
    # reconciles that project declaration with the selected Woo model.
    cast(list[Object], cast(Object, inputs["equipment_condition_inputs"])["devices"])[
        0
    ]["declared_model"] = "Fixture-2"
    declared = cast(list[Object], review_device_conditions(inputs, source)["devices"])[
        0
    ]
    assert (
        declared["model_identity"]
        == {
            "status": "different_text",
            "declared_value": "Fixture-2",
            "selected_woo_value": "Fixture-1",
        }
        and cast(Object, cast(list[Object], declared["documents"])[0]["model"])[
            "status"
        ]
        == "listed"
    )
    cast(Object, cast(Object, source["inspections"])[str(first["document_id"])])[
        "document_revision"
    ] = "f" * 64
    with pytest.raises(VersionUnavailable):
        review_device_conditions(inputs, source)


def test_ambiguous_labelled_fields_remain_unresolved(workspace: Workspace) -> None:
    basis, assessment = evidence()
    source = certificate_documents(basis, assessment)
    document = cast(list[Object], source["documents"])[0]
    content = certificate_pdf(
        models="Fixture-1 or Fixture-2", extra=("Firmware Version : 020202",)
    )
    document["blob_sha256"] = workspace.blobs.put(content)
    inspect_report_certificates({"certificates": source}, workspace.blobs, lambda: None)
    review = review_device_conditions(condition_project(), source)
    row = cast(list[Object], cast(list[Object], review["devices"])[0]["documents"])[0]
    assert cast(Object, row["firmware"])["status"] == "unresolved"
    assert cast(Object, row["model"])["status"] == "unresolved"


def test_plant_observations_never_supply_other_nodes_firmware(
    workspace: Workspace,
) -> None:
    inputs = condition_project()
    selection = inputs.pop("equipment_selection")
    inputs["equipment_plant"] = {
        "schema_version": 1,
        "requirements": {
            "schema_version": 1,
            "grid_phase": 3,
            "operating_mode": "grid_connected",
            "pv_dc_kw": None,
            "required_usable_kwh": 0,
            "required_discharge_ac_kw": 0,
        },
        "units": [
            {"id": identity, "name": identity, "selection": selection}
            for identity in ("a", "b")
        ],
        "parallel_groups": [],
    }
    observation = cast(
        list[Object], cast(Object, inputs["equipment_condition_inputs"])["devices"]
    )[0]
    observation["selection_ref"] = {
        "kind": "plant_unit",
        "unit_id": "a",
        "role": "inverter",
    }
    review = review_device_conditions(inputs, inspected_fixture(workspace))
    inverters = [
        d
        for d in cast(list[Object], review["devices"])
        if cast(Object, d["selection_ref"])["role"] == "inverter"
    ]
    assert [d["declared_firmware"] for d in inverters] == ["010101", None]
    assert [
        cast(Object, cast(list[Object], d["documents"])[0]["firmware"])["status"]
        for d in inverters
    ] == ["exact_match", "unresolved"]
    observation["selection_ref"] = {
        "kind": "plant_unit",
        "unit_id": "absent",
        "role": "inverter",
    }
    with pytest.raises(ConditionBindingChanged):
        validate_condition_inputs(inputs)


def test_frozen_condition_review_rejects_a_changed_decision(
    workspace: Workspace,
) -> None:
    source: Object = {
        **condition_project(),
        "certificates": inspected_fixture(workspace),
        "dependencies": {},
    }
    seed_sha = workspace.blobs.put_object(source)
    originals = inspect_report_certificates(source, workspace.blobs, lambda: None)
    certificates = cast(Object, source["certificates"])
    certificates["condition_review"] = review_device_conditions(source, certificates)
    bundle: Object = {
        "schema_version": 1,
        "kind": "certificate_cover_information_v1",
        "report_source_sha256": seed_sha,
        "evidence": certificates,
        "dependencies": {"report_source": seed_sha, **originals},
    }
    dependencies: Object = {
        "report_source": seed_sha,
        "certificate_inspection": workspace.blobs.put_object(bundle),
    }
    assert (
        report_source_with_information(workspace.blobs, dependencies)["certificates"]
        == certificates
    )
    device = cast(
        list[Object], cast(Object, certificates["condition_review"])["devices"]
    )[0]
    cast(Object, cast(list[Object], device["documents"])[0]["firmware"])["status"] = (
        "conflict"
    )
    dependencies["certificate_inspection"] = workspace.blobs.put_object(bundle)
    with pytest.raises(VersionUnavailable, match="frozen project observations"):
        report_source_with_information(workspace.blobs, dependencies)
