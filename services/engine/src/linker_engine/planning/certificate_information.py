"""Restore a report's frozen certificate information without new acquisition."""

from __future__ import annotations

from typing import cast

from .canonical import Object
from .dependencies import verify_dependencies
from .errors import VersionUnavailable
from .storage import Blobs


def report_source_with_information(blobs: Blobs, dependencies: Object) -> Object:
    seed_sha = dependencies.get("report_source")
    if not isinstance(seed_sha, str):
        raise VersionUnavailable("frozen report source is missing")
    source = blobs.object(seed_sha)
    inspection_sha = dependencies.get("certificate_inspection")
    if inspection_sha is None:
        return source
    if not isinstance(inspection_sha, str):
        raise VersionUnavailable("frozen certificate inspection is missing")
    bundle = blobs.object(inspection_sha)
    evidence, original = bundle.get("evidence"), source.get("certificates")
    if (
        bundle.get("schema_version") != 1
        or bundle.get("kind") != "certificate_cover_information_v1"
        or bundle.get("report_source_sha256") != seed_sha
        or not isinstance(evidence, dict)
        or not isinstance(original, dict)
        or {k: v for k, v in evidence.items() if k != "inspections"} != original
    ):
        raise VersionUnavailable("certificate inspection differs from report source")
    inspections, children = evidence.get("inspections"), bundle.get("dependencies")
    documents = cast(list[Object], original["documents"])
    if (
        not isinstance(inspections, dict)
        or set(inspections) != {str(d["document_id"]) for d in documents}
        or not isinstance(children, dict)
        or children.get("report_source") != seed_sha
    ):
        raise VersionUnavailable("certificate inspection dependencies are missing")
    for document in documents:
        identity = str(document["document_id"])
        item = inspections[identity]
        if not isinstance(item, dict):
            raise VersionUnavailable("certificate inspection is invalid")
        if set(item) == {"status"} and item["status"] in {
            "unavailable",
            "resource_limit",
        }:
            continue
        if (
            item.get("method") != "literal_certificate_cover_v1"
            or item.get("applicability") != "not_assessed"
            or any(
                item.get(k) != document[k]
                for k in ("document_id", "document_revision", "blob_sha256")
            )
            or children.get(f"certificate.{identity}.raw") != document["blob_sha256"]
            or not isinstance(item.get("declarations"), list)
        ):
            raise VersionUnavailable("certificate inspection source binding changed")
        for declaration in cast(list[Object], item["declarations"]):
            if (
                not isinstance(declaration, dict)
                or declaration.get("page") != 1
                or declaration.get("kind") not in {"models", "firmware", "standards"}
                or not isinstance(declaration.get("value"), str)
            ):
                raise VersionUnavailable("certificate declaration is invalid")
    verify_dependencies(blobs, bundle)
    return {**source, "certificates": evidence}
