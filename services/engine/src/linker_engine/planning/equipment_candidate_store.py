"""Freeze candidate checks with shared fact blobs; private reads stay historical."""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from .canonical import Json, Object, decode_object, encode
from .errors import NotFound, VersionUnavailable
from .records import Actor
from .workspace import Workspace


def assessments(root: Object) -> Iterator[Object]:
    """Unit and plant checks share immutable fact blobs instead of raw copies."""
    yield root
    for unit in cast(list[Object], root.get("systems", [])):
        yield cast(Object, unit["assessment"])


class EquipmentCandidateStore:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def put(self, assessment: Object) -> str:
        compact = decode_object(encode(assessment))
        for assessment in assessments(compact):
            for row in cast(list[Object], assessment["selected_products"]):
                row.pop("facts", None)
            for check in cast(list[Object], assessment["checks"]):
                check["fact_sha256s"] = [
                    self.workspace.blobs.put_object(cast(Object, fact))
                    for fact in cast(list[Json], check.pop("facts"))
                ]
        return self.workspace.blobs.put_object(compact)

    def read(self, actor: Actor, run_id: str, candidate_id: str) -> Object:
        run = self.workspace.run(actor, run_id)
        if not run.result or run.result.get("kind") != "search_woo_equipment_v1":
            raise NotFound("equipment search result not found")
        search = cast(Object, run.result["search"])
        candidates = cast(list[Object], search["candidates"])
        row = next((row for row in candidates if row["id"] == candidate_id), None)
        if row is None:
            raise NotFound("candidate does not belong to this result")
        sha = row.get("assessment_sha256")
        if not isinstance(sha, str):
            raise VersionUnavailable("candidate assessment binding is missing")
        assessment = self.workspace.blobs.object(sha)
        for part in assessments(assessment):
            for check in cast(list[Object], part["checks"]):
                refs = check.pop("fact_sha256s")
                check["facts"] = [
                    self.workspace.blobs.object(cast(str, fact))
                    for fact in cast(list[Json], refs)
                ]
        return {
            "run_id": run.id,
            "candidate_id": candidate_id,
            "assessment_sha256": sha,
            "assessment": assessment,
        }
