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
