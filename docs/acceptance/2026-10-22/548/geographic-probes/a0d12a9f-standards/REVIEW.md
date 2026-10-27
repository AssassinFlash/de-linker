# Standards review — a0d12a9f geographic originals and metric imports

Fixed source `a0d12a9f68b17db3ebade24bace5eb8a890c6e3f`; baseline `78772822`; diff `git diff 78772822...a0d12a9f`; single feature commit. Independent minimal fixed source, linked dependencies only; no parent/native/production mutation.

**Standards FAIL: one accepted P3 output-boundary defect.** No actionable judgement smell found under the complete Fowler baseline; project rules override heuristics and tooling-enforced style/type checks are not repeated. Standards read/reused: AGENTS, CONTEXT, domain/local-storage, isolated-runtime ADR, geographic-intake/workbench contract. No extra CONTRIBUTING/CODING_STANDARDS was identified in the previously checked repository standards set.

## Documented-rule finding

`apps/planner/src/domain/geographic.ts:112–114` returns directly for p===0, bypassing the computed-output `geodetic(result)` check used at :140. Rule: `docs/specs/548-geographic-intake.md:28`, “unsupported numerical results fail explicitly”; the server's corresponding transform also enforces its safe numerical window.

With WGS84 reference lon0,lat90,h0=0,known ellipsoid and ENU input[0,0,Number.MAX_SAFE_INTEGER], the browser returns[0,90,9007199254740992], outside its declared numeric support. The exact server operation raises InvalidInput. Extreme input is accepted within the existing input window; this finding does not invent a narrower physical domain or claim an actual roof/UI calculation is affected. Route the polar result through the common computed-output check. Parent accepted P3 for this batch.

Original probe: `apps/planner/src/domain/standards-geographic-pole-probe.mjs`; failing output `pole-probe.log`. The probe asserts output remains supported; it fails unmodified on this fixed source. `pole-server-comparison.py` and log record the server refusal. These are retained for the next fixed correction.

## Independent passing evidence

- Fixed geographic/import tests18 plus existing privateHTTP88:106 PASS, including actual SQLite/Assets/blob/receipt APIs. `backend-tests-final.log`. The first archive run lacked the shared planning workspace fixture; that same-SHA conftest was added, then the complete run passed. Initial setup failures are not product findings.
- `services/engine/tests/planning/standards_import_probe.py`:12 PASS. Real ASGI import and replay with FOREIGN and readonly TEAM prove decode is never invoked before rejection, using a decode trap; all return404 and publish no blobs. Additional actual intake tests cover bowtie, outside hole, huge coordinate, escaped invalid Unicode ID, boolean ID, duplicate member and deeply nested JSON:typed refusal/no private-value echo/no new blobs. Separate keys for the same declared source/conversion retain identical domain geometry IDs; removing the test original makes otherwise valid attachment fail VersionUnavailable. `independent-import-probe.log`.
- New frontend geographic/attachment domain tests:6 PASS, including real server fixture parsing, one history step, undo/redo, stale frame, unaligned frame, bad owner/hash/schema/base64. `frontend-domain.log`.
- Actual fixed source/build hash and versioned emitted ESM graph:1 PASS. `build-check.log`. No renderer/native/GPU proof is claimed.

## Source and authority checks

- `http_app.py:270` checks write ownership before base64 decoding; `http_replay.py:122–123` does the same. Asset APIs recheck ownership and permanent receipt; prepare checks an old receipt before any new PROJ capture. Logical options/original hash determine retry semantics and stable source/roof IDs. No provider URL fetch or rights resolver is introduced.
- Selected GeoJSON validates JSON ambiguity, feature/part indices,2D closed rings, range, vertex limits and public feature ID, then projects and checks real polygon topology before publication. Original bytes and immutable metadata are distinct authorities; precision stays null unless declared, engineering status is not_evaluated. The new user declaration is not licence verification.
- Project attachment uses same-project owned Assets, source association, purpose and original-byte availability; frontend applies source/roof/coordinate/attachment atomically behind a complete before-document guard, preserving unrelated inputs.
- Native allowlist/quota adds only geometry/import to the existing owned upload lane. No new browser Actor choice, PHP layout, style pipeline, customer wording or legacy code identifiers were found. Existing geometry helper changed only its structural plane interface, retaining its numerical expression.

At finalisation parent reported three **separate Spec P2** findings (antipodal/near-horizon folding, source hash association, absolute Up cancellation), accepted for correction. They are not independent findings of this Standards report and are not hidden by the passing tests. Combined release is not approved.

## Reproduction and boundary

```
cd services/engine
PYTHONPATH=src .venv/bin/python -m pytest tests/planning/test_geographic.py tests/planning/test_geometry_import.py tests/planning/test_private_http.py -q --basetemp=../../pytest-runtime
PYTHONPATH=src .venv/bin/python -m pytest tests/planning/standards_import_probe.py -q -s --basetemp=../../probe-runtime
cd ../../apps/planner
node --test src/domain/geographic.test.ts src/domain/geometryImports.test.ts
node --test src/domain/standards-geographic-pole-probe.mjs
npm run build:check
```

Reconstruct exact source/fixtures from archive-manifest.json before replaying retained probes; dependency links point only to installed package environments. Full accepted physics/editor suites were not rerun. Map/drawing/import recovery UI/provider acquisition/country/engineering/full A–D and deployment acceptance remain active. All owned synthetic runtime files, bytecode/cache and SHA-matched fixed reconstruction are reclaimed at completion; probes/results/report/logs remain, with cleanup.json detailing counts.
