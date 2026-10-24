"""Owned component verification; retire this workspace after evidence export."""
from __future__ import annotations

import json
import os
import shlex
import time
from pathlib import Path

from linker_engine.planning.apify_transport import ApifyTransport
from linker_engine.planning.apify_weather_client import ApifyWeatherClient
from linker_engine.planning.canonical import digest, encode
from linker_engine.planning.jobs import Jobs
from linker_engine.planning.records import Actor, Context, Lease
from linker_engine.planning.weather_acquisition import WeatherAcquisition
from linker_engine.planning.weather_fetch_plan import WeatherFetchPlan
from linker_engine.planning.weather_journal import WeatherJournal
from linker_engine.planning.worker import Control
from linker_engine.planning.workspace import Workspace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "docs/acceptance/2026-10-24/548/weather-transport/actual"
OUT = BASE / "accepted"
OUT.mkdir(parents=True, exist_ok=True)


def credential() -> str:
    if not os.environ.get("APIFY_TOKEN"):
        for line in (Path.home() / ".config/terravolt-builder/apify.env").read_text().splitlines():
            parts = shlex.split(line, comments=True)
            for part in parts:
                if part.startswith("APIFY_TOKEN="):
                    os.environ["APIFY_TOKEN"] = part.partition("=")[2]
    return os.environ.get("APIFY_TOKEN", "")


plan = WeatherFetchPlan.read({
    "schema_version": 1, "kind": "pvgis_tmy_apify_acquisition_v1",
    "request": {
        "schema_version": 1, "api_version": "5.3", "latitude_deg": 52.52,
        "longitude_deg": 13.405, "start_year": 2005, "end_year": 2023,
        "use_terrain_horizon": False, "radiation_database_policy": "provider_default_with_verified_echo",
        "expected_radiation_database": "PVGIS-SARAH3", "expected_meteo_database": "ERA5",
    },
    "interpretation": {
        "schema_version": 1, "synthetic_energy_year": 2023,
        "solar_date_policy": "original_selected_year_plus_reported_irradiance_offset",
        "output_axis_policy": "nonleap_synthetic_utc_hourly_scenario_v1",
        "power_reconstruction": "representative_pv_output_over_declared_intervals_v1",
    },
    "limits": {
        "max_response_bytes": 2000000, "max_metadata_bytes": 100000, "max_weather_rows": 9000,
        "connect_timeout_seconds": 5, "read_timeout_seconds": 20, "max_elapsed_seconds": 240,
        "poll_seconds": 1, "max_polls": 180, "actor_timeout_seconds": 180, "actor_memory_mb": 1024,
        "max_total_charge_usd": 0.05, "request_timeout_seconds": 90, "request_retries": 1,
        "minimum_download_kb_per_second": 1,
    },
})
transport = ApifyTransport(credential, plan.limits)
# Credential repair cannot consume the irreversible start permit. This private
# read is not retained; account details and token never enter evidence/output.
transport.request("GET", "/v2/users/me", expected_status=200, limit=100000, guard=lambda: None)
if not (HERE / "workspace").exists():
    raise SystemExit("This repair requires the one retained rejected-origin trial")
workspace = Workspace(HERE / "workspace")
with workspace.database.read() as connection:
    previous = connection.execute("SELECT * FROM weather_acquisitions").fetchall()
    assert len(previous) == 1 and previous[0]["remote_run_id"] == "tXCGhHtxHRpnGQrOS"
    previous = dict(previous[0])
    observed = workspace.blobs.object(previous["observation_sha256"])
    assert observed["status"] == "SUCCEEDED" and previous["capture_sha256"] is None
    job = dict(connection.execute("SELECT * FROM jobs WHERE run_id=?", (previous["run_id"],)).fetchone())
old_lease = Lease(job["id"], job["run_id"], job["kind"], job["attempt"], job["worker"], job["lease_token"], job["lease_until"], workspace.blobs.object(job["request_sha256"]))
Jobs(workspace).fail(old_lease, {"code": "weather_response_invalid", "retryable": False}, retry_after=None)
failed = BASE / "rejected-origin-1"
failed.mkdir(exist_ok=True)
for item in BASE.iterdir():
    if item.is_file(): item.rename(failed/item.name)
(failed/"journal.json").write_bytes(encode(previous))
# Recover the exact safe original INPUT for the rejected trial. This is a read,
# not adoption of an unknown run or a repeat of its consumed start permit.
from linker_engine.planning.apify_json import apify_json
from linker_engine.planning.weather_submission import submission
r = transport.request("GET", f"/v2/key-value-stores/{observed['store_id']}/records/INPUT", expected_status=200, limit=100000, guard=lambda: None)
expected = json.loads((ROOT/"docs/research/2026-10-24-weather-transport/raw/weather-effective-input-baseline.json").read_bytes())
expected.update(submission(plan, previous["nonce"]))
expected["customHttpHeaders"] = {"Accept":"application/json"}
assert encode(apify_json(r.body)) == encode(expected)
(failed/"effective-input-exact.json").write_bytes(r.body)
(failed/"retirement.json").write_bytes(encode({"local_task_state":"failed", "failure_code":"weather_response_invalid", "provider_status":"SUCCEEDED", "new_starts_for_this_intent":1, "repair_is_separate_local_task":True}))
owner = Actor("user", "component-verification:548-weather-transport")
project = workspace.create(owner, "Pinned weather transport component verification", {}, key="weather-transport-trial")
context = Context(
    digest(b"weather-acquisition-component-verification-not-managed-kernel"),
    {"component_only": "weather_acquisition_transport"},
    {"weather_acquisition.plan": workspace.blobs.put_object(plan.document())},
    {"component_verification_only": True},
)
run = workspace.evaluate(owner, project.id, project.revision, context, key="weather-transport-trial-explicit-agent-repair", max_attempts=1)
lease = Jobs(workspace).claim("p548-component-trial", kinds=("evaluate",), lease_seconds=600)
assert lease is not None


class RecordedJournal(WeatherJournal):
    def acknowledge(self, intent, remote):
        result = super().acknowledge(intent, remote)
        (OUT / "start-acknowledgement.json").write_bytes(encode(remote.document()))
        print(json.dumps({"provider_run": remote.id, "status": remote.status, "acknowledgement": "durably_retained"}), flush=True)
        return result

    def observe(self, intent, remote):
        result = super().observe(intent, remote)
        (OUT / "final-observation.json").write_bytes(encode(remote.document()))
        return result


journal = RecordedJournal(workspace)
started = time.monotonic()
source = WeatherAcquisition(journal, ApifyWeatherClient(transport)).acquire(lease, plan, Control())
intent = journal.begin(lease, plan)
with workspace.database.read() as connection:
    durable = dict(connection.execute("SELECT * FROM weather_acquisitions WHERE run_id=?", (run.id,)).fetchone())
    owned_count = connection.execute("SELECT COUNT(*) FROM project_assets").fetchone()[0]
(OUT / "journal.json").write_bytes(encode(durable))
existing = ROOT / "docs/research/2026-10-24-pv-generation/raw/berlin-2005-2023-nohorizon.tmy.json"
deduplicated = digest(source.content) == digest(existing.read_bytes())
blob_refs = {}
for item in (HERE / "workspace/blobs").glob("*/*"):
    if not item.is_file(): continue
    sha = item.name
    content = item.read_bytes()
    assert digest(content) == sha
    if deduplicated and sha == digest(source.content):
        blob_refs[sha] = str(existing.relative_to(ROOT))
    else:
        target = OUT / "blobs" / sha
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(content)
        blob_refs[sha] = str(target.relative_to(ROOT))
(OUT / "blob-references.json").write_bytes(encode(blob_refs))
result = {
    "schema_version": 1, "component_verification_only": True,
    "provider_run_id": intent.remote_run_id, "local_task_id": run.id,
    "original_sha256": digest(source.content), "original_bytes": len(source.content),
    "original_deduplicated_against_prior_primary_capture": deduplicated,
    "capture_sha256": intent.capture_sha256, "owned_asset_count": owned_count,
    "local_task_state": workspace.run(owner, run.id).state,
    "elapsed_seconds": round(time.monotonic() - started, 3),
    "nonce_echo_verified": True, "effective_input_full_safe_equality_verified": True,
    "live_p548_modified": False, "new_weather_actor_starts_this_task": 1, "new_weather_actor_starts_this_transport_verification": 2,
}
(OUT / "result.json").write_bytes(encode(result))
transport.close()
print(json.dumps(result), flush=True)
