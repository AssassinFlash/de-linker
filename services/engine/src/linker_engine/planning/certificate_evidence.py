"""Read certificate associations from a run's frozen Woo proof, without work.

A Woo document classification/association is not a certificate applicability
decision. Model, firmware, edition, annexes and national/site acceptance remain
separate obligations (COUNTRY-EVIDENCE.md). This reader never upgrades them.
"""

from __future__ import annotations

from typing import cast

from .canonical import Json, Object
from .equipment_candidate_store import EquipmentCandidateStore
from .errors import InvalidInput, VersionUnavailable
from .records import Actor
from .workspace import Workspace


def certificate_documents(basis: Object, assessment: Object) -> Object:
    """Project only the selected products; preserve each recorded source binding."""
    products = {
        cast(int, row["canonical_product_id"]): row
        for row in cast(list[Object], basis["products"])
    }
    selected = cast(list[Object], assessment["selected_products"])
    documents: dict[str, Object] = {}
    identities: list[Json] = []
    for product in selected:
        identity = cast(int, product["product_id"])
        source = products.get(identity)
        if source is None or source["product_revision"] != product.get(
            "product_revision"
        ):
            raise VersionUnavailable(
                "certificate product differs from frozen selection"
            )
        identities.append(
            {
                "product_id": identity,
                "product_revision": source["product_revision"],
                "model": source["model"],
                "brand": source["brand"],
            }
        )
        for document in cast(list[Object], source["documents"]):
            if document.get("type") != "certificate":
                continue
            if identity not in cast(list[Json], document.get("product_ids", [])):
                raise VersionUnavailable(
                    "certificate association is not bound to product"
                )
            key = str(document["document_id"])
            row: Object = {
                name: document[name]
                for name in (
                    "document_id",
                    "document_revision",
                    "blob_sha256",
                    "url",
                    "title",
                    "lang",
                )
            }
            if key in documents:
                previous = {
                    k: v for k, v in documents[key].items() if k != "product_ids"
                }
                if previous != row:
                    raise VersionUnavailable(
                        "certificate has conflicting frozen identities"
                    )
            else:
                documents[key] = {**row, "product_ids": []}
            members = cast(list[Json], documents[key]["product_ids"])
            if identity not in members:
                members.append(identity)
    return {
        "schema_version": 1,
        "scope": "associated_product_documents",
        "applicability": "not_assessed",
        "products": identities,
        "documents": list(documents.values()),
    }


class CertificateEvidence:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def read(
        self, actor: Actor, run_id: str, candidate_id: str | None = None
    ) -> Object:
        run = self.workspace.run(actor, run_id)
        if run.state != "succeeded" or run.result is None:
            raise InvalidInput("certificate sources need a completed equipment result")
        result = run.result
        assessment_sha: Json = None
        assessment: Object | None
        proof: Json = None
        if result.get("kind") == "search_woo_equipment_v1":
            if candidate_id is None:
                raise InvalidInput("choose a recorded equipment candidate")
            detail = EquipmentCandidateStore(self.workspace).read(
                actor, run_id, candidate_id
            )
            assessment = cast(Object, detail["assessment"])
            assessment_sha = detail["assessment_sha256"]
        elif result.get("kind") == "planning_report_v1":
            if candidate_id is not None:
                raise InvalidInput("candidate reference requires its equipment search")
            dependencies = cast(Object, result["dependencies"])
            source_sha = dependencies.get("report_source")
            if not isinstance(source_sha, str):
                raise VersionUnavailable("saved report source is unavailable")
            source = self.workspace.blobs.object(source_sha)
            if (
                source.get("project_id") != run.project_id
                or source.get("revision") != run.revision
                or source.get("input_sha256") != run.manifest["input_sha256"]
            ):
                raise VersionUnavailable("report source does not belong to this result")
            assessment = cast(Object | None, source.get("equipment"))
            proof = cast(Object, source.get("woo_bases", {})).get("equipment")
        else:
            if candidate_id is not None:
                raise InvalidInput("candidate reference requires its equipment search")
            assessment = cast(Object | None, result.get("assessment"))
            binding = result.get("equipment_binding")
            if assessment is None and isinstance(binding, dict):
                assessment = cast(Object | None, binding.get("assessment"))
        if not isinstance(assessment, dict):
            raise InvalidInput("this result has no recorded equipment assessment")
        context = cast(Object, run.manifest["context"])
        assets = cast(Object, context["assets"])
        proof = proof if proof is not None else assets.get("woo.equipment_inputs")
        if not isinstance(proof, str):
            raise VersionUnavailable("recorded Woo certificate source is unavailable")
        evidence = certificate_documents(self.workspace.blobs.object(proof), assessment)
        return {
            **evidence,
            "run_id": run.id,
            "project_id": run.project_id,
            "revision": run.revision,
            "manifest_sha256": run.manifest_sha256,
            "basis_sha256": proof,
            "candidate_id": candidate_id,
            "assessment_sha256": assessment_sha,
        }
