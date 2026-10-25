"""Publish a report model and its PDF atomically through the existing worker."""

from __future__ import annotations

import base64
from typing import cast

from linker_engine.pdf import render

from .asset_publication import AssetPublication, AssetResult
from .canonical import Object
from .errors import VersionUnavailable
from .execution_identity import execution_key, request_execution_key
from .frozen_run import frozen_manifest
from .product_sources import ProductSources
from .project_materials import materials_csv, project_materials
from .records import Actor, Context, Lease, Run
from .report_copy import text
from .report_inputs import ReportOptions
from .report_model import build_report
from .report_sources import confirm_report_sources, report_sources
from .runtime_snapshot import RuntimeSnapshot
from .worker import Control
from .workspace import Workspace


class ReportKernel:
    kind = "planning_report_v1"
    models = {
        "task": kind,
        "report": "frozen_project_report_v1",
        "materials": "project_materials_v1",
    }

    def __init__(self, workspace: Workspace, products: ProductSources) -> None:
        self.workspace, self.products = workspace, products
        self.runtime = RuntimeSnapshot.capture()
        workspace.blobs.put(self.runtime.content)

    def parameters(self) -> Object:
        return {"kind": self.kind, "policy": "selected_owned_analyses_current_woo_v1"}

    def execution_key(self) -> str:
        return execution_key(
            {
                "code_sha256": self.runtime.sha256,
                "models": dict(self.models),
                "parameters": self.parameters(),
            }
        )

    def context(
        self, actor: Actor, project_id: str, revision: int, options: ReportOptions
    ) -> Context:
        project = self.workspace.get(actor, project_id, revision=revision)
        logo = options.logo_bytes()
        source = report_sources(self.workspace, self.products, actor, project, options)
        source["materials"] = project_materials(source)
        cast(Object, source["dependencies"])["materials_model"] = (
            self.workspace.blobs.put_object(cast(Object, source["materials"]))
        )
        pinned = {
            "runtime_bundle": self.runtime.sha256,
            "report.source": self.workspace.blobs.put_object(source),
        }
        if logo is not None:
            pinned["report.logo"] = self.workspace.blobs.put(logo)
            pinned["report.logo_media"] = self.workspace.blobs.put_object(
                {
                    "media_type": "image/png"
                    if options.logo and options.logo.startswith("data:image/png;")
                    else "image/jpeg"
                }
            )
        return Context(
            self.runtime.sha256, dict(self.models), pinned, self.parameters()
        )

    def __call__(self, lease: Lease, control: Control) -> AssetResult:
        control.checkpoint()
        sha = lease.request.get("manifest_sha256")
        if not isinstance(sha, str):
            raise VersionUnavailable("report task has no pinned manifest")
        manifest = frozen_manifest(self.workspace, lease, sha)
        if request_execution_key(lease.request, manifest, sha) != self.execution_key():
            raise VersionUnavailable("report execution settings changed")
        context = cast(Object, manifest["context"])
        pinned = cast(Object, context["assets"])
        if pinned.get("runtime_bundle") != self.runtime.sha256 or not isinstance(
            pinned.get("report.source"), str
        ):
            raise VersionUnavailable("report source bundle is missing")
        source = self.workspace.blobs.object(cast(str, pinned["report.source"]))
        if any(
            source.get(key) != manifest.get(key)
            for key in ("project_id", "revision", "input_sha256")
        ):
            raise VersionUnavailable(
                "report bundle does not match its project revision"
            )
        confirm_report_sources(self.workspace, self.products, source)
        control.checkpoint()
        report = build_report(source)
        logo: str | None = None
        if isinstance(pinned.get("report.logo"), str):
            media = self.workspace.blobs.object(cast(str, pinned["report.logo_media"]))
            logo = f"data:{media['media_type']};base64," + base64.b64encode(
                self.workspace.blobs.read(cast(str, pinned["report.logo"]))
            ).decode("ascii")
        content = render(report, logo, credits=text("credits", report.locale))
        control.checkpoint()
        confirm_report_sources(self.workspace, self.products, source)
        report_document = cast(Object, report.model_dump(mode="json"))
        report_sha = self.workspace.blobs.put_object(report_document)
        dependencies: Object = {
            "report_model": report_sha,
            "report_source": pinned["report.source"],
            "materials_model": cast(Object, source["dependencies"])["materials_model"],
        }
        if pinned.get("report.logo") is not None:
            dependencies["branding"] = pinned["report.logo"]
        asset = AssetPublication.prepare(
            self.workspace.blobs,
            cast(str, manifest["project_id"]),
            content,
            "application/pdf",
            "planning_report_pdf_v1",
            {
                "retention": "permanent",
                "provenance": {
                    "label": report.title,
                    "basis": "Selected immutable project analyses and their stated assessment scope",
                    "rights_basis": "Private project output and customer-provided branding",
                },
                "dependencies": dependencies,
                "report_model_sha256": report_sha,
                "locale": report.locale,
            },
        )
        materials = cast(Object, source["materials"])
        csv_asset = AssetPublication.prepare(
            self.workspace.blobs,
            cast(str, manifest["project_id"]),
            materials_csv(
                materials, cast(str, dependencies["materials_model"]), report.locale
            ),
            "text/csv",
            "planning_materials_csv_v1",
            {
                "retention": "permanent",
                "provenance": {
                    "label": report.title,
                    "basis": "Frozen project materials shared with the planning report",
                    "rights_basis": "Private project output",
                },
                "dependencies": dependencies,
                "locale": report.locale,
            },
        )
        return AssetResult(
            {
                "schema": 1,
                "kind": self.kind,
                "project_id": manifest["project_id"],
                "revision": manifest["revision"],
                "input_sha256": manifest["input_sha256"],
                "manifest_sha256": sha,
                "runtime_sha256": self.runtime.sha256,
                "pinned_assets": pinned,
                "report": report_document,
                "report_sha256": report_sha,
                "materials_sha256": dependencies["materials_model"],
                "has_draft_items": any(
                    isinstance(line, dict) and line.get("handling") == "woo_product"
                    for line in cast(list, materials["lines"])
                ),
                "source_runs": source["source_runs"],
                "equipment_candidate": source["candidate"],
                "dependencies": dependencies,
            },
            asset,
            {"bill_of_materials_csv": csv_asset},
        )


class ReportService:
    def __init__(
        self, workspace: Workspace, kernel: ReportKernel, *, max_attempts: int
    ) -> None:
        self.workspace, self.kernel, self.max_attempts = workspace, kernel, max_attempts

    def evaluate(
        self,
        actor: Actor,
        project_id: str,
        revision: int,
        options: ReportOptions,
        *,
        key: str,
    ) -> Run:
        return self.workspace.evaluate(
            actor,
            project_id,
            revision,
            self.kernel.context(actor, project_id, revision, options),
            key=key,
            max_attempts=self.max_attempts,
            intent=options.intent(),
        )
