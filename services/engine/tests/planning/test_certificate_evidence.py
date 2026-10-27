"""Certificate lookup reuses immutable sources and never upgrades applicability."""

from __future__ import annotations

from typing import cast

import pytest

from linker_engine.planning.canonical import Object
from linker_engine.planning.certificate_evidence import (
    CertificateEvidence,
    certificate_documents,
)
from linker_engine.planning.certificate_report import certificate_sections
from linker_engine.planning.errors import NotFound, VersionUnavailable
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
    proof = workspace.blobs.put_object(basis)
    pinned = Context(
        context.code_sha256,
        context.models,
        {**context.assets, "woo.equipment_inputs": proof},
        context.parameters,
    )
    project = workspace.create(owner, "Certificate fixture", {}, key="new")
    run = workspace.evaluate(owner, project.id, 1, pinned, key="run", max_attempts=1)
    jobs = Jobs(workspace)
    lease = jobs.claim("fixture", kinds=("evaluate",), lease_seconds=30)
    assert lease
    jobs.complete(lease, {"kind": "qualify_woo_equipment_v1", "assessment": assessment})
    workspace.revise(owner, project.id, 1, {"later": True}, key="edit")
    with workspace.database.read() as c:
        before = list(c.iterdump())
    result = CertificateEvidence(workspace).read(owner, run.id)
    assert result["revision"] == 1 and result["basis_sha256"] == proof
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
