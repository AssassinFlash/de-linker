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
