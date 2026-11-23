"""Freeze an owned report for Woo; Woo alone authorises an actual draft write."""

from __future__ import annotations

import sqlite3
from typing import cast
from uuid import uuid4

from . import commands
from .access import project_row
from .assets import Assets
from .canonical import Json, Object, digest, encode
from .errors import Conflict, InvalidInput, NotFound, VersionUnavailable
from .records import Actor
from .report_kernel import ReportKernel
from .wire_numbers import check_wire_numbers
from .workspace import Workspace


class HandoffNotFound(NotFound):
    code = "handoff_not_found"


class HandoffRevisionChanged(Conflict):
    code = "handoff_revision_changed"


class HandoffIncomplete(InvalidInput):
    code = "handoff_incomplete"


def _synthesized_publication(basis: Object) -> Object:
    """Rebuild the publication proof for a basis frozen before it existed.

    Every emitted row carries the required string/int fields the Woo side
    revalidates; a basis row without a complete, well-typed identity is not a
    Woo-provable fact and is not synthesized into the proof.
    """
    products: list[Json] = []
    documents: list[Json] = []
    for row in cast(list[Object], basis["products"]):
        if not isinstance(row, dict):
            continue
        product_id = row.get("canonical_product_id", row.get("id"))
        revision = row.get("product_revision")
        if type(product_id) is not int or not isinstance(revision, str):
            continue
        products.append({"product_id": product_id, "product_revision": revision})
        raw_documents = row.get("documents")
        if not isinstance(raw_documents, list):
            continue
        for document in cast(list[Object], raw_documents):
            if not isinstance(document, dict):
                continue
            document_id = document.get("document_id")
            document_revision = document.get("document_revision")
            blob_sha256 = document.get("blob_sha256")
            if (
                not isinstance(document_id, str)
                or not isinstance(document_revision, str)
                or not isinstance(blob_sha256, str)
            ):
                continue
            documents.append(
                {
                    "document_id": document_id,
                    "document_revision": document_revision,
                    "blob_sha256": blob_sha256,
                    "product_id": product_id,
                }
            )
    return {
        "engineering_contract": 2,
        "compatibility_revision": cast(str, basis["compatibility_revision"]),
        "products": products,
        "documents": documents,
        "reference_inputs": [],
    }


def publication_scope(workspace: Workspace, source: Object) -> Object:
    """Retain every consumed product/document reference without a second source."""
    bases = source.get("woo_bases")
    if not isinstance(bases, dict) or not bases:
        raise HandoffIncomplete("the report has no selected equipment")
    scopes: list[Object] = []
    for sha in dict.fromkeys(cast(dict[str, str], bases).values()):
        basis = workspace.blobs.object(sha)
        raw_scope = basis.get("publication")
        if not isinstance(raw_scope, dict):
            if isinstance(basis.get("compatibility_revision"), str) and isinstance(
                basis.get("products"), list
            ):
                raw_scope = _synthesized_publication(basis)
            else:
                raise VersionUnavailable("report Woo permission proof is missing")
        if raw_scope.get("engineering_contract", 2) != 2:
            raise VersionUnavailable("report Woo permission proof is missing")
        scope: Object = {
            **raw_scope,
            "engineering_contract": 2,
            "compatibility_revision": raw_scope.get(
                "compatibility_revision", basis.get("compatibility_revision")
            ),
            "reference_inputs": raw_scope.get("reference_inputs", []),
        }
        scopes.append(scope)
    revisions = {scope.get("compatibility_revision") for scope in scopes}
    if len(revisions) != 1 or not isinstance(next(iter(revisions)), str):
        raise VersionUnavailable("report Woo permission proofs disagree")
    result: Object = {
        "engineering_contract": 2,
        "compatibility_revision": next(iter(revisions)),
    }
    for kind, fields in (
        ("products", ("product_id",)),
        ("documents", ("document_id", "product_id")),
        ("reference_inputs", ("reference_input_id",)),
    ):
        rows: dict[bytes, Object] = {}
        for scope in scopes:
            values = scope.get(kind)
            if not isinstance(values, list):
                raise VersionUnavailable("report Woo dependency scope is invalid")
            for value in values:
                if not isinstance(value, dict):
                    raise VersionUnavailable("report Woo dependency is invalid")
                identity = encode([value.get(field) for field in fields])
                if identity in rows and rows[identity] != value:
                    raise VersionUnavailable("report Woo dependency versions disagree")
                rows[identity] = value
        result[kind] = cast(list[Json], [rows[key] for key in sorted(rows)])
    return result


def purchase_items(
    material_lines: list[Object], products: dict[int, Object]
) -> list[Json]:
    """Purchasable items per line: quantity minus the exact retained share.

    The complete system list keeps retained originals visible; this purchase
    view subtracts 'retained_quantity' when the report states one, so a mixed
    retain/new line buys only the new units. A declared retention without an
    exact share, or a share exceeding the quantity, stops the handoff instead
    of guessing a purchase count.
    """
    items: list[Json] = []
    for line in material_lines:
        product_id, quantity = line.get("product_id"), line.get("quantity")
        if (
            type(product_id) is not int
            or product_id <= 0
            or type(quantity) is not int
            or quantity <= 0
        ):
            raise HandoffIncomplete("selected product quantities remain unresolved")
        if "retained_quantity" in line:
            retained = line.get("retained_quantity")
            if type(retained) is not int:
                raise HandoffIncomplete(
                    "retained equipment quantities remain unresolved"
                )
            if retained > quantity:
                raise HandoffIncomplete(
                    "retained equipment exceeds the established quantity"
                )
            if quantity - retained <= 0:
                continue
            quantity -= retained
        if "inquiry_quantity" in line:
            quantity = cast(int, line["inquiry_quantity"])
        product = products.get(product_id, {})
        label = (
            " ".join(
                str(product.get(key) or line.get(key) or "")
                for key in ("brand", "model")
            ).strip()
            or str(product.get("sku") or line.get("sku") or "").strip()
        )
        if not label:
            raise HandoffIncomplete("selected product identity is unresolved")
        items.append({"product_id": product_id, "quantity": quantity, "label": label})
    return items


class Handoffs:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def prepare(
        self,
        actor: Actor,
        project_id: str,
        report_run_id: str,
        expected_revision: int,
        *,
        key: str,
    ) -> Object:
        intent: Object = {
            "expected_revision": expected_revision,
            "report_run_id": report_run_id,
        }
        command = commands.command_hash(intent, key)
        scope = f"handoff:{project_id}"
        with self.workspace.database.read() as connection:
            project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.workspace.blobs, actor, scope, key, command
            )
            if receipt is not None:
                return self._read(
                    connection, actor, commands.receipt_string(receipt, "handoff_id")
                )
        project = self.workspace.get(actor, project_id)
        if project.revision != expected_revision:
            raise HandoffRevisionChanged("the saved project has changed")
        run = self.workspace.run(actor, report_run_id)
        report = run.result
        if (
            run.project_id != project_id
            or run.revision != expected_revision
            or run.state != "succeeded"
            or report is None
            or report.get("kind") != ReportKernel.kind
            or report.get("input_sha256") != project.input_sha256
        ):
            raise HandoffIncomplete("choose the matching completed project report")
        model = report.get("report")
        if not isinstance(model, dict) or digest(encode(model)) != report.get(
            "report_sha256"
        ):
            raise VersionUnavailable("the report document cannot be verified")
        pinned = cast(Object, report["pinned_assets"])
        source_hash = pinned.get("report.source")
        if not isinstance(source_hash, str):
            raise VersionUnavailable("the report has no frozen source")
        source = self.workspace.blobs.object(source_hash)
        equipment = source.get("equipment")
        report_only = (
            isinstance(source.get("retained_inverter"), dict) and equipment is None
        )
        if not report_only and not isinstance(equipment, dict):
            raise HandoffIncomplete("the report has no selected products")
        products = (
            {
                cast(int, product["product_id"]): product
                for product in cast(list[Object], equipment["selected_products"])
            }
            if isinstance(equipment, dict)
            else {}
        )
        material_lines = (
            equipment["provisional_bill_of_materials"]
            if isinstance(equipment, dict)
            else []
        )
        material_sha = report.get("materials_sha256")
        if material_sha is not None:
            materials = source.get("materials")
            if (
                not isinstance(materials, dict)
                or digest(encode(materials)) != material_sha
                or cast(Object, report["dependencies"]).get("materials_model")
                != material_sha
            ):
                raise VersionUnavailable("the report materials cannot be verified")
            material_lines = [
                line
                for line in cast(list[Object], materials["lines"])
                if line["handling"] == "woo_product"
            ]
        items = purchase_items(cast(list[Object], material_lines), products)
        if not items and not report_only:
            raise HandoffIncomplete("the report has no selected products")
        asset = Assets(self.workspace).get(
            actor, project_id, cast(str, cast(Object, report["prepared_asset"])["id"])
        )
        asset_dependencies = asset.metadata.get("dependencies")
        result_dependencies = report.get("dependencies")
        if (
            asset.purpose != "planning_report_pdf_v1"
            or asset.metadata.get("report_model_sha256") != report["report_sha256"]
            or not isinstance(asset_dependencies, dict)
            or not isinstance(result_dependencies, dict)
            or asset_dependencies.get("report_model") != report["report_sha256"]
            or asset_dependencies.get("report_source") != source_hash
            or any(
                result_dependencies.get(name) != sha
                for name, sha in asset_dependencies.items()
            )
            or result_dependencies.get("prepared_asset_content") != asset.content_sha256
            or result_dependencies.get("prepared_asset_metadata")
            != asset.metadata_sha256
        ):
            raise VersionUnavailable("the report PDF is missing")
        self.workspace.blobs.read(asset.content_sha256)
        candidate = source.get("candidate")
        candidate_id = (
            cast(str, candidate["candidate_id"])
            if isinstance(candidate, dict)
            else digest(encode(equipment))
            if not report_only
            else source_hash
        )
        publication = (
            publication_scope(self.workspace, source)
            if not report_only or source.get("woo_bases")
            else None
        )
        if (
            report_only
            and publication is not None
            and not any(
                publication[field]
                for field in ("products", "documents", "reference_inputs")
            )
        ):
            publication = None
        snapshot: Object = {
            "schema_version": 1,
            "kind": "planning_report_only_v1"
            if report_only
            else "planning_products_v1",
            "project_id": project_id,
            "title": project.title,
            "revision": expected_revision,
            "input_sha256": project.input_sha256,
            "report_run_id": run.id,
            "candidate_id": candidate_id,
            "report_source_sha256": source_hash,
            "report_sha256": report["report_sha256"],
            "report": model,
            "pdf": {
                "asset_id": asset.id,
                "sha256": asset.content_sha256,
                "media_type": asset.media_type,
            },
            "items": items,
            "publication": publication,
        }
        if material_sha is not None:
            snapshot["materials_sha256"] = material_sha
        check_wire_numbers(snapshot)
        snapshot_hash = self.workspace.blobs.put_object(snapshot)
        with self.workspace.database.transaction() as connection:
            current = project_row(connection, actor, project_id, write=True)
            receipt = commands.replay(
                connection, self.workspace.blobs, actor, scope, key, command
            )
            if receipt is not None:
                return self._read(
                    connection, actor, commands.receipt_string(receipt, "handoff_id")
                )
            if current["revision"] != expected_revision:
                raise HandoffRevisionChanged("the saved project has changed")
            existing = connection.execute(
                "SELECT id FROM handoffs WHERE project_id=? AND run_id=? "
                "AND snapshot_sha256=? ORDER BY created_at,id LIMIT 1",
                (project_id, run.id, snapshot_hash),
            ).fetchone()
            handoff_id, now = (
                (existing["id"] if existing is not None else uuid4().hex),
                self.workspace.clock(),
            )
            if existing is None:
                connection.execute(
                    "INSERT INTO handoffs "
                    "(id,project_id,run_id,revision,candidate_id,snapshot_sha256,created_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        handoff_id,
                        project_id,
                        run.id,
                        expected_revision,
                        candidate_id,
                        snapshot_hash,
                        now,
                    ),
                )
            commands.remember(
                connection,
                self.workspace.blobs,
                actor,
                scope,
                key,
                command,
                {"handoff_id": handoff_id},
                now,
            )
            return self._read(connection, actor, handoff_id)

    def admit_inquiry(
        self, actor: Actor, handoff_id: str, snapshot_sha256: str
    ) -> Object:
        if actor.kind == "team":
            raise NotFound("project handoff not found")
        with self.workspace.database.transaction() as connection:
            try:
                handoff = self._read(connection, actor, handoff_id)
            except NotFound as exc:
                raise HandoffNotFound(
                    "the inquiry's prepared report was removed"
                ) from exc
            if handoff["snapshot_sha256"] != snapshot_sha256:
                raise Conflict("the inquiry report reference changed")
            snapshot = cast(Object, handoff["snapshot"])
            self.workspace.advance_inquiry_generation(
                connection, cast(str, snapshot["project_id"])
            )
            return {"admitted": True}

    def read(self, actor: Actor, handoff_id: str) -> Object:
        with self.workspace.database.read() as connection:
            return self._read(connection, actor, handoff_id)

    def _read(
        self, connection: sqlite3.Connection, actor: Actor, handoff_id: str
    ) -> Object:
        row = connection.execute(
            "SELECT * FROM handoffs WHERE id=?", (handoff_id,)
        ).fetchone()
        if row is None:
            raise NotFound("project handoff not found")
        project_row(connection, actor, row["project_id"])
        snapshot = self.workspace.blobs.object(row["snapshot_sha256"])
        if (
            any(
                snapshot.get(field) != row[column]
                for field, column in (
                    ("project_id", "project_id"),
                    ("report_run_id", "run_id"),
                    ("revision", "revision"),
                    ("candidate_id", "candidate_id"),
                )
            )
            or snapshot.get("schema_version") != 1
            or snapshot.get("kind")
            not in {"planning_products_v1", "planning_report_only_v1"}
        ):
            raise VersionUnavailable("the handoff snapshot binding is invalid")
        return {
            "schema_version": 1,
            "id": row["id"],
            "snapshot_sha256": row["snapshot_sha256"],
            "snapshot": snapshot,
        }
