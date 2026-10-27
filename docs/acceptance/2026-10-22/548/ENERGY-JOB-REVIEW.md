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
backup/restore. Initial full planning was 129 passing tests; whole engine was
286 passing in 18.27s. Strict mypy, Ruff lint and format checks passed.

Fixtures are synthetic, labelled and bounded. No hardware/country/weather or
frontend/production acceptance is claimed by these tests. The new handler is
not mounted publicly; old customer entry points still use the existing app.

## Standards

Fixed `be0cd227`: one P2. Pydantic's strict model configuration did not prevent
`Literal[1]` from accepting boolean true or float 1.0 as an integer version.
Both parameter/scenario classes were affected; the reviewer also reproduced
scenario true through the actual durable Worker to a satisfied result.
No project/asset-ID/runtime binding or child-backup bypass was found.

## Spec

Fixed `be0cd227`: the same P2 was independently reproduced, including true in
both persisted project and battery asset. Extra owner/initial/nonfinite/gap/
TZif-substitution checks passed; finished result/trace backup was complete,
insufficient terminal inventory remained succeeded+violated, and restored outage
scope remained mixed. No scope creep was found.

## Repair and fixed recheck

Versions now require a strict integer of supported value; true, 1.0, strings,
null and unsupported integer versions are rejected. Pinned metadata/manifest
version guards also check integer identity. Ten direct/enqueue regressions and
two actual malformed-durable-job Worker regressions cover the original cases.
The repaired fixed commit will be rechecked by both independent axes. Full
planning has 141 passing tests (6.66s), with strict mypy/Ruff/format checks.

Both axes independently passed fixed `685773a143e07d6e934ba5e233f91c28e855024d`
from isolated git archives, 141 tests each (6.54s / 6.57s). Spec additionally
created reference/hash-consistent malformed profile metadata and manifests;
boolean/float versions failed in the real Worker as version_unavailable with
no result. Correct integer versions completed the analytic scenario. No
remaining blocker or scope expansion was found. Whole engine after the fix:
298 tests passed in 19.49s; Ruff lint/format and strict mypy passed.
