"""Owned views expose frozen facts, never a filesystem path or owner secret."""

from __future__ import annotations

from typing import cast

from .assets import Asset, Assets
from .canonical import Json, Object
from .equipment_candidate_store import candidate_ratings
from .records import Actor, Project, Run
from .retained_panels import display_document, project_panels
from .workspace import Workspace


def project_view(project: Project) -> Object:
    return {
        "id": project.id,
        "title": project.title,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "inputs": display_document(
            project.inputs, project_panels(project.inputs), inputs=True
        ),
    }


def run_view(run: Run) -> Object:
    return {
        "id": run.id,
        "project_id": run.project_id,
        "revision": run.revision,
        "state": run.state,
        "is_current": run.is_current,
        "manifest_sha256": run.manifest_sha256,
        "manifest": run.manifest,
        "result_sha256": run.result_sha256,
        "result": run.result,
        "error": run.error,
    }


def owned_run_view(workspace: Workspace, actor: Actor, run: Run) -> Object:
    project = workspace.get(actor, run.project_id, revision=run.revision)
    panels = project_panels(project.inputs)
    view = display_document(run_view(run), panels)
    result = view.get("result")
    if isinstance(result, dict) and result.get("kind") == "search_woo_equipment_v1":
        search = cast(Object, result["search"])
        candidates = cast(list[Object], search["candidates"])
        if any("nominal_ac_kw" not in row for row in candidates):
            expanded: list[Json] = []
            for row in candidates:
                if "nominal_ac_kw" in row:
                    expanded.append(row)
                    continue
                frozen = workspace.blobs.object(cast(str, row["assessment_sha256"]))
                selection = cast(Object, row.get("plant") or row["selection"])
                expanded.append({**row, **candidate_ratings(selection, frozen)})
            return {
                **view,
                "result": {**result, "search": {**search, "candidates": expanded}},
            }
        return view
    if not isinstance(result, dict) or result.get("kind") != "planning_report_v1":
        return view
    prepared = result.get("prepared_asset")
    if not isinstance(prepared, dict):
        return view
    assets = Assets(workspace)
    with workspace.database.read() as db:
        pdf = assets.presented(db, run.project_id, str(prepared["id"]))
        if pdf.id == prepared["id"]:
            return view
        result["prepared_asset"] = asset_view(pdf)
        deps = cast(Object, result["dependencies"])
        pdf_deps = cast(Object, pdf.metadata["dependencies"])
        deps.update(pdf_deps)
        deps.update(
            prepared_asset_content=pdf.content_sha256,
            prepared_asset_metadata=pdf.metadata_sha256,
        )
        result["report_sha256"] = pdf_deps["report_model"]
        result["report"] = workspace.blobs.object(str(pdf_deps["report_model"]))
        result["materials_sha256"] = pdf_deps["materials_model"]
        for name, old in cast(
            dict[str, Object], result["prepared_attachments"]
        ).items():
            attachment = assets.presented(db, run.project_id, str(old["id"]))
            cast(Object, result["prepared_attachments"])[name] = asset_view(attachment)
            deps[f"prepared_attachment.{name}.content"] = attachment.content_sha256
            deps[f"prepared_attachment.{name}.metadata"] = attachment.metadata_sha256
    return view


def asset_view(asset: Asset) -> Object:
    return {
        "id": asset.id,
        "project_id": asset.project_id,
        "content_sha256": asset.content_sha256,
        "media_type": asset.media_type,
        "purpose": asset.purpose,
        "metadata_sha256": asset.metadata_sha256,
        "metadata": asset.metadata,
        **(
            {"reissued_from": asset.metadata["reissued_from"]}
            if "reissued_from" in asset.metadata
            else {}
        ),
    }
