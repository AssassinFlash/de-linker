# Spec8e11c7c3 — FAIL, one P3 canonical-URL contract finding

Target`8e11c7c3dfbcf658765b53b5f7fa4074e03ed560`; full base`8a4a80b132f692062125807e509a57926fb0f518`, correction base`b0080ec15eb2dcab6b2c22b7b029180a2c1f73c2`. b008 PASS remains preserved. Requested548-workbench.md does not exist in this target; the actual548-workbench-application.md applies.

## Finding

`548-interactive-design.md:104–106` says “The client accepts only a query-free, credential-free SceneViewport-hash.js in the actual entry module's own origin and directory.” `DESIGN-REVIEW.md:130–132` also states that query/fragment additions are rejected.

`apps/planner/src/data/config.ts:39–46` checks truthiness of`asset.search`/`asset.hash`, then returns`asset.href`. A valid sibling path ending in a bare`?`,`#`or`?#` is accepted with that suffix retained. WHATWG URL exposes empty search/hash strings for these empty components, although href retains them. The exact original repro is`tests/spec-config-boundary.test.mjs`:20 foreign/malformed variants are rejected and4 canonical/missing cases accepted, but the3 empty-delimiter contract cases intentionally fail.

This is actionableP3 policy correctness, not a security exploit: actual native Application metadata never emits these suffixes; its strict filename regex rejects them. No arbitrary origin/path execution was demonstrated. Parent accepted this finding and is tightening the canonical-href comparison in a later fixed commit; do not reinterpret this fixed report as that later correction.

No additional missing/partial requirement, scope creep or implemented-wrong behaviour was found within this correction.

## Independent passed evidence

- `spec-scene-loader.test.mjs`: actual source loader uses real Node ESM caching. Concurrent requests share one promise; two controlled failures produce URL sequence bare→retry1→retry2; success and in-flight reuse are exact. Missing metadata never invents a URL.
- `spec-scene-view.test.mjs`: actual React/StrictMode/DesignEditor retains staged rows`2.5`, recovers from rejected module to a controlled successful component, and reuses it across3Plan↔3D view changes. No command or input rewrite occurs. Only returned scene transport is substituted; no GPU claim.
- `spec-built-retry.test.mjs`: actual emitted versioned entry and actual emitted queried scene/core modules execute. A cached failing bare scene (failure injected only for that URL) recovers at query1; two concurrent imports return the same module. Extra query2 also never re-executes the mount entry: mount scans stay1. Direct query2 after prior success deliberately bypasses source success reuse and gives Three's multiple-instance warning; this is not the normal loader path.
- `probe_native_config.php`: actual fixed PHP Application with native function stubs and local manifests.14 cases, including query/fragment/traversal/scheme/type variants, preserve the strict native boundary and one mount.
- `spec-plan-layering.test.mjs`: actual SVG DOM order places constraints above overlapping array projections; direct constraint selection emits0array commands; inputs, quantities and stable poses remain unchanged. This is DOM order/routing, not physical hit-testing.
-52target-tracked DOM cases pass (`target-dom.log`). A real TypeScript/Vite rebuild and source check pass (`target-build.log`); all7 emitted files match target blobs (`probe_build.results.json`). Accepted b008 physics/gesture results were not rerun.

## Reproduce

Run`python3 rebuild_snapshot.py`here, then in`apps/planner`:

```sh
node --test tests/spec-config-boundary.test.mjs
node --no-warnings=ExperimentalWarning --loader ./tests/spec-scene-controlled-loader.mjs --test tests/spec-scene-loader.test.mjs tests/spec-scene-view.test.mjs
node --no-warnings=ExperimentalWarning --loader ./tests/spec-built-failure-loader.mjs --test tests/spec-built-retry.test.mjs
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/spec-plan-layering.test.mjs
npm run build
npm run build:check
```

From this root:`php probe_native_config.php`. It regenerates its small native-manifest fixture. Fixed source copies/builds are reclaimed only after byte-for-byte target matching; unique probes/results/logs and exact rebuild manifest remain. No p548/native/browser/production action was performed. Parent's actual native GPU recovery proof is separate; full A–D, touch/device loss/max mobile performance are not accepted by this source review.
