"""Owned views expose frozen facts, never a filesystem path or owner secret."""

from __future__ import annotations

from .assets import Asset
from .canonical import Object
from .records import Project, Run


def project_view(project: Project) -> Object:
    return {
        "id": project.id,
        "title": project.title,
        "revision": project.revision,
        "input_sha256": project.input_sha256,
        "inputs": project.inputs,
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


def asset_view(asset: Asset) -> Object:
    return {
        "id": asset.id,
        "project_id": asset.project_id,
        "content_sha256": asset.content_sha256,
        "media_type": asset.media_type,
        "purpose": asset.purpose,
        "metadata_sha256": asset.metadata_sha256,
        "metadata": asset.metadata,
    }
