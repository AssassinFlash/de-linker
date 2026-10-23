# Spec47bb44d6 — PASS, narrow correction

Target`47bb44d6ca2ff664d0bf638e394ab6fa842ac2fd`; correction base`8e11c7c3dfbcf658765b53b5f7fa4074e03ed560`; full base`8a4a80b132f692062125807e509a57926fb0f518`. The8e11 fixed report remains FAIL/P3, not rewritten. Its evidence is in the sibling`planning-spec-editor-8e11-ug7iol_l`directory.

Spec`548-interactive-design.md:104–106` requires a query-free scene URL in the actual entry's origin/directory. Acceptance additionally requires fragment-free metadata. `config.ts` now compares canonical resolved href to`origin + pathname`, retaining its other checks. Bare`?`,`#`,`?#`are rejected, without changing legitimate canonical HTTP(S) sibling resources.

No missing/partial requirement, scope creep or incorrect implementation remains in this narrow correction. The exact original`spec-config-boundary.test.mjs`is copied byte-for-byte from the8e11 evidence; its3red cases are now green. Together with the target's config test,5tests pass. Additional default-port normalisation, local HTTP port, encoded plugin directory and same-resource dot-path normalisation cases pass.

A real TypeScript/Vite rebuild and source check pass (`target-build.log`); all7 generated artifacts match fixed target blobs (`probe_build.results.json`). The real emitted versioned entry/lazy graph passes. Original independent emitted-graph failure/queried-retry probe passes under the new hashes: a failing cached bare URL is recovered via query1, repeated same-query modules share identity and entry mount scans stay1. Its extra direct query2 deliberately bypasses the normal loader's successful-cache path and causes Three's multiple-instance warning; this is not normal-loader behaviour or an entry/React duplication.

Only config source and its regression changed in this patch. Hash-equal loader, lazy boundary, DesignEditor, PlanViewport and PHP Application carry forward8e11's independent concurrency/success-reuse, React raw retention, PHP manifest boundary and SVG routing results. The52targetDOM run belongs to8e11 and was not represented as rerun here; accepted physics/native cases were not repeated.

## Reproduce

Run`python3 rebuild_snapshot.py`in this directory, then in`apps/planner`:

```sh
node --test tests/config.test.mjs tests/spec-config-boundary.test.mjs tests/spec-canonical-valid.test.mjs
npm run build
npm run build:check
node --no-warnings=ExperimentalWarning --loader ./tests/spec-built-failure-loader.mjs --test tests/spec-built-retry.test.mjs
```

This is fixed-source/config/actual-built-graph proof. JSDOM has no application mount target; the bare scene failure is injected and no native GPU/browser operation is claimed. Parent source, nativep548 and production were untouched. The source-only correction does not complete the active fullA–D goal or unproved touch/device-loss/mobile-capacity acceptance.
