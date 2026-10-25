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


class HandoffRevisionChanged(Conflict):
    code = "handoff_revision_changed"


class HandoffIncomplete(InvalidInput):
    code = "handoff_incomplete"


def publication_scope(workspace: Workspace, source: Object) -> Object:
    """Retain every consumed product/document reference without a second source."""
    bases = source.get("woo_bases")
    if not isinstance(bases, dict) or "equipment" not in bases:
        raise HandoffIncomplete("the report has no selected equipment")
    scopes: list[Object] = []
    for sha in dict.fromkeys(cast(dict[str, str], bases).values()):
        scope = workspace.blobs.object(sha).get("publication")
        if not isinstance(scope, dict) or scope.get("engineering_contract") != 2:
            raise VersionUnavailable("report Woo permission proof is missing")
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
        if not isinstance(equipment, dict):
            raise HandoffIncomplete("the report has no selected products")
        products = {
            product["product_id"]: product
            for product in cast(list[Object], equipment["selected_products"])
        }
        material_lines = equipment["provisional_bill_of_materials"]
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
        items: list[Json] = []
        for line in cast(list[Object], material_lines):
            product_id, quantity = line.get("product_id"), line.get("quantity")
            if (
                type(product_id) is not int
                or product_id <= 0
                or type(quantity) is not int
                or quantity <= 0
            ):
                raise HandoffIncomplete("selected product quantities remain unresolved")
            product = products.get(product_id, {})
            label = " ".join(
                str(product.get(key, "")) for key in ("brand", "model")
            ).strip()
            if not label:
                raise HandoffIncomplete("selected product identity is unresolved")
            items.append(
                {"product_id": product_id, "quantity": quantity, "label": label}
            )
        if not items:
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
        )
        snapshot: Object = {
            "schema_version": 1,
            "kind": "planning_products_v1",
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
            "publication": publication_scope(self.workspace, source),
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
            or snapshot.get("kind") != "planning_products_v1"
        ):
            raise VersionUnavailable("the handoff snapshot binding is invalid")
        return {
            "schema_version": 1,
            "id": row["id"],
            "snapshot_sha256": row["snapshot_sha256"],
            "snapshot": snapshot,
        }
