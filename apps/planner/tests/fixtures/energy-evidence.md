# Energy browser fixtures

`energy-run.json` is the actual finished managed numerical worker response from
`docs/acceptance/2026-10-24/548/managed-energy-worker/http.json`, key `finished`.
It uses synthetic two-hour sources and contains no real customer data. Its
manifest, source hashes, verification checks and provenance remain unchanged.

`energy-scenario.json`, `energy-selections.json` and `energy-inputs.json` are
frontend preparation fixtures with explicit analytic parameters and synthetic
asset references. They do not grant real asset ownership or equipment approval.
Both Pydantic and Ajv validate the same positive documents and the mutations in
`energy-invalid.json`; preparation additionally tests field dependencies and
binding. These fixtures add no physical default or independent numerical limit.

`dc-energy-run.json` reuses the already passed two-hour native service DC fixture
(`test_equipment.py::test_shared_dc_native_asset_command_worker_and_stage_bound_trace`).
It retains that existing worker result and its two-row TraceWindow unchanged;
physics was not replayed to create the browser fixture. The synthetic Woo rows
are contract fixtures, never a customer-product maintenance source or a real
H2/B2 performance approval. This adds the distinct DC consumer/stage boundary
which the existing AC fixtures cannot cover.

`plant-energy-run.json` is the captured native output of
`test_plant_energy.py::test_native_joint_parameters_run_trace_and_report_share_one_owned_plant`.
It retains the completed joint run, its exact named-unit TraceWindow and
prepared report, plus the owned project inputs used by browser preparation.
This is one two-hour synthetic Woo/AC-charging contract fixture, not a real
H2 performance claim or a runtime product source. The existing worker output
is reused by result, trace, preparation and comparison presentation checks;
those consumers do not trigger another physical replay.

`dc-plant-energy-run.json` retains the one completed two-hour native shared-DC
plant run, named-unit trace and report from
`test_native_dc_plant_projects_owned_pv_groups_and_keeps_report_stages`.
The actual PV producer supplies three distinct retained groups: two DC-connected
storage converters and one independent AC group. Product constraints originate
from the existing explicitly synthetic Woo maintenance fixture; no unknown
reverse capability is invented. Browser contract and preparation checks share
this output without another PV or dispatch replay. The fixture is never runtime
product data or manufacturer/country qualification.

The shared-DC plant fixture now also retains its native per-system PV string assessment and energy-only report. Each converter uses its own wiring and the whole-roof coverage is assessed separately. It was refreshed through the same two-hour exporter for the multi-system string feature; the synthetic product and operating assumptions remain test-only.
