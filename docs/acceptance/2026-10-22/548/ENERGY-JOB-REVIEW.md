# Source-pinned energy job: review boundary

2026-10-23. This increment follows the independently accepted numerical fixed
point `3c533482` and the contract in `docs/specs/548-energy-job.md`.

## Current verification

Nineteen real asset/SQLite/CSV/Worker tests execute the production EnergyKernel,
not fixture callbacks. They verify analytic energy, immutable history and
artifact hashes, raw/mapping/TZif replay, operating-boundary refinement and load
scope, explicit failure for wrong versions/missing bytes/invalid measurement,
dependency-to-input asset binding, client retry identity, foreign references,
concurrent import, team read-only authority, source retention and standalone
backup/restore. Full planning is 129 passing tests; strict mypy, Ruff lint and
format checks pass. The whole-engine regression is recorded after completion.

Fixtures are synthetic, labelled and bounded. No hardware/country/weather or
frontend/production acceptance is claimed by these tests. The new handler is
not mounted publicly; old customer entry points still use the existing app.

## Standards

Pending fixed-commit independent review. Review all new files plus changes to
Workspace/Jobs/Worker/archive, including source snapshot and child references.

## Spec

Pending fixed-commit independent review against energy-job and the existing
workspace/time/energy contracts. Check that source/identity boundaries, frozen
dependencies, version failures, retries, resolution and output claims match the
contract, and that no full-product scope is deleted by this internal increment.
