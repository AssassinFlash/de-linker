"""Preserve historical project originals and publish generic-panel revisions and files."""

from __future__ import annotations

import argparse
import base64
import json
import sqlite3
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from linker_engine.models import Report
from linker_engine.pdf import render

from .canonical import Object
from .project_materials import materials_csv
from .report_copy import text
from .report_model import separate_panel_lists
from .retained_panels import RetainedPanel, display_document, project_panels
from .schema import PANEL_ASSET_REISSUES
from .storage import Blobs


def _reissue(
    row: sqlite3.Row,
    panels: list[RetainedPanel],
    blobs: Blobs,
    db: sqlite3.Connection,
    apply: bool,
) -> bool:
    meta = blobs.object(row["metadata_sha256"])
    deps = cast(Object, meta["dependencies"])
    report = blobs.object(str(deps["report_model"]))
    materials = blobs.object(str(deps["materials_model"]))
    revision = db.execute(
        "SELECT input_sha256 FROM revisions WHERE project_id=? AND number=?",
        (row["project_id"], materials["revision"]),
    ).fetchone()
    if revision is not None:
        # Resolve the retained specification ID against the report’s own revision.
        matching = project_panels(blobs.object(revision["input_sha256"]))
        panels = [p for p in panels if p not in matching] + matching
    revised_report = display_document(report, panels)
    revised_materials = display_document(materials, panels)
    pdf = row["purpose"] == "planning_report_pdf_v1"
    old_scopes = {
        "PV reference module · project quotation",
        "PV-Referenzmodul · Projektangebot",
    }
    has_quoted_panels = any(
        section.get("id") == "bom"
        and isinstance(section.get("table"), dict)
        and any(row and row[-1] in old_scopes for row in section["table"]["rows"])
        for section in cast(list[dict[str, Any]], report.get("sections", []))
    )
    if (
        report == revised_report
        and materials == revised_materials
        and not has_quoted_panels
    ):
        return False
    if not apply:
        return True
    locale = str(meta["locale"])
    revised_report["subtitle"] = str(report["subtitle"]) + (
        " · Neuausgabe mit allgemeinen PV-Moduldaten"
        if locale == "de"
        else " · Reissued with generic panel parameters"
    )
    revised_report = separate_panel_lists(
        Report.model_validate(revised_report), revised_materials
    ).model_dump(mode="json")
    model_hash = blobs.put_object(revised_report)
    material_hash = blobs.put_object(revised_materials)
    deps.update(report_model=model_hash, materials_model=material_hash)
    meta["reissued_from"] = {"id": row["id"], "content_sha256": row["content_sha256"]}
    if pdf:
        meta["report_model_sha256"] = model_hash
        branding = deps.get("branding")
        logo = None
        if isinstance(branding, str):
            data = blobs.read(branding)
            mime = "image/png" if data.startswith(b"\x89PNG") else "image/jpeg"
            logo = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
        content = render(
            Report.model_validate(revised_report), logo, credits=text("credits", locale)
        )
    elif row["purpose"].startswith("planning_materials_csv_"):
        content = materials_csv(revised_materials, material_hash, locale)
    else:
        # Additional report attachments retain the measured values and use the same report dependencies.
        raw = blobs.read(row["content_sha256"]).decode("utf-8-sig")
        content = str(display_document({"csv": raw}, panels)["csv"]).encode("utf-8-sig")
    replacement = uuid4().hex
    db.execute(
        "INSERT INTO project_assets (id,project_id,content_sha256,media_type,purpose,metadata_sha256,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            replacement,
            row["project_id"],
            blobs.put(content),
            row["media_type"],
            row["purpose"],
            blobs.put_object(meta),
            time.time(),
        ),
    )
    db.execute(
        "INSERT INTO panel_asset_reissues(original_id,replacement_id) VALUES(?,?)",
        (row["id"], replacement),
    )
    return True


def migrate(root: Path, *, apply: bool) -> dict[str, int]:
    counts = {
        "historical_revisions": 0,
        "current_projects": 0,
        "reports": 0,
        "materials": 0,
        "other_attachments": 0,
    }
    blobs = Blobs((root / "blobs").resolve(strict=True))
    with sqlite3.connect(
        (root / "workspace.sqlite").resolve(strict=True).as_uri()
        + ("?mode=rw" if apply else "?mode=ro"),
        uri=True,
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        if apply:
            db.execute(PANEL_ASSET_REISSUES)
        mapped = (
            {
                v
                for row in db.execute(
                    "SELECT original_id,replacement_id FROM panel_asset_reissues"
                )
                for v in row
            }
            if db.execute(
                "select 1 from sqlite_master where type='table' and name='panel_asset_reissues'"
            ).fetchone()
            else set()
        )
        for project in db.execute("SELECT id,revision FROM projects").fetchall():
            retained: list[RetainedPanel] = []
            for revision in db.execute(
                "SELECT number,input_sha256 FROM revisions WHERE project_id=? ORDER BY number",
                (project["id"],),
            ).fetchall():
                inputs = blobs.object(revision["input_sha256"])
                panels = project_panels(inputs)
                if not panels:
                    continue
                retained.extend(p for p in panels if p not in retained)
                counts["historical_revisions"] += 1
                if revision["number"] != project["revision"]:
                    continue
                revised = display_document(inputs, panels, inputs=True)
                counts["current_projects"] += 1
                if apply:
                    number = revision["number"] + 1
                    now = time.time()
                    db.execute(
                        "INSERT INTO revisions(project_id,number,input_sha256,created_at) VALUES(?,?,?,?)",
                        (project["id"], number, blobs.put_object(revised), now),
                    )
                    db.execute(
                        "UPDATE projects SET revision=?,updated_at=? WHERE id=?",
                        (number, now, project["id"]),
                    )
            for row in db.execute(
                "SELECT * FROM project_assets WHERE project_id=? AND (purpose='planning_report_pdf_v1' OR purpose LIKE 'planning%csv%')",
                (project["id"],),
            ).fetchall():
                if row["id"] not in mapped and _reissue(
                    row, retained, blobs, db, apply
                ):
                    counts[
                        "reports"
                        if row["purpose"] == "planning_report_pdf_v1"
                        else "materials"
                        if row["purpose"].startswith("planning_materials_csv_")
                        else "other_attachments"
                    ] += 1
    return counts


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(migrate(args.workspace, apply=args.apply), sort_keys=True))


if __name__ == "__main__":
    main()
