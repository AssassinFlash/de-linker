"""Check real Aladdin UI exports; this is not an engineering accuracy test."""
from __future__ import annotations

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def geometry(elements: list[dict]) -> list[dict]:
    result = deepcopy(elements)
    for element in result:
        element.pop("yearlyYield", None)
        element.pop("dailyYield", None)
    return result


rows = []
projects = []
for project_name, csv_name, observed_days, ui_annual in [
    ("linker-study-aladdin-garage.ala", "yearly-pv-yield.csv", 4, 282262.24),
    ("linker-study-aladdin-garage-12-days.ala", "yearly-pv-yield-12-days.csv", 12, 281869.30),
]:
    project = json.loads((ARTIFACTS / project_name).read_text())
    projects.append(project)
    # Aladdin's default-compression omits daysPerYear=12 from saved files.
    # Source: fixed 2.0.6 contentUtil.ts compress/expand; live UI explicitly set 12.
    days = project["world"].get("daysPerYear", 12)
    assert days == observed_days
    assert project["version"] == "2.0.7"
    with (ARTIFACTS / csv_name).open(newline="") as stream:
        data = list(csv.reader(stream))
    values = [float(row[1].strip()) for row in data[1:] if len(row) > 1 and row[1].strip()]
    assert len(values) == observed_days
    annual = sum(values) * 12 / days
    assert abs(annual - ui_annual) < 0.005
    rows.append({
        "project": project_name,
        "csv": csv_name,
        "app_version": project["version"],
        "days_per_year_explicit_in_file": project["world"].get("daysPerYear"),
        "days_per_year_effective_and_ui_observed": days,
        "times_per_hour": project["world"]["timesPerHour"],
        "dust_loss": project["world"].get("dustLoss"),
        "csv_rows": len(values),
        "csv_sum": sum(values),
        "annual_scale": 12 / days,
        "annual_from_csv": annual,
        "ui_annual_kwh": ui_annual,
        "within_display_rounding": True,
    })
assert geometry(projects[0]["elements"]) == geometry(projects[1]["elements"])
worlds = [deepcopy(project["world"]) for project in projects]
for world in worlds:
    world.pop("daysPerYear", None)
assert worlds[0] == worlds[1]
report = {
    "verified_at": "2026-10-22",
    "comparison": rows,
    "same_geometry_and_other_world_settings": True,
    "difference_kwh": rows[1]["ui_annual_kwh"] - rows[0]["ui_annual_kwh"],
    "difference_percent": 100 * (rows[1]["ui_annual_kwh"] / rows[0]["ui_annual_kwh"] - 1),
    "interpretation": "Same public vendor example and geometry. Only daysPerYear was changed through the real UI. Neither run is a simulation of every hour of 365 days. Difference is sampling sensitivity, not ground-truth error.",
}
(ROOT / "runtime-comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
files = []
for path in sorted(ROOT.rglob("*")):
    if path.is_file() and (path.relative_to(ROOT).parts[0] in {"artifacts", "screens", "raw"} or path.name in {"runtime-comparison.json", "check_runtime_artifacts.py"}):
        files.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(ROOT / "artifact-manifest.json").write_text(json.dumps(files, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(report, ensure_ascii=False, indent=2))
