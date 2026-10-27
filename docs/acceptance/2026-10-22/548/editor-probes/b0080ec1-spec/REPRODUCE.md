# Spec review: b0080ec1 — PASS

Fixed target `b0080ec15eb2dcab6b2c22b7b029180a2c1f73c2`; full base `8a4a80b132f692062125807e509a57926fb0f518`, fix base `6c6680ad4e2eb890b08c58b5a9bffd95ecb48957`. No missing/partial requirement within this declared increment, scope creep or incorrect behaviour found.

Spec `548-interactive-design.md:23–25`: “Apply is a guarded immutable command; stale before-values and changed roof dependents are rejected without overwriting current work. A group is atomic and produces one history step.” Lines85–90 require whole-document gesture guards and teardown cancellation; lines92–97 require a single versioned ESM mount identity. This is the manual-editor increment, not fullB/map/whole-tool acceptance.

`SceneViewport.tsx:273–324` now captures the document and frame, guards finish and emits a group with the original document. `geometryCommands.ts:87–95` independently checks that entire precondition. `SceneControls.tsx:97–114` aborts before detaching/disposal and recreates per frame. Plan follows the same whole-document precondition and explicit cancellation routes.

## Original failures and new independent challenges

The unchanged6c original probe is preserved as `apps/planner/tests/spec-r3f-reference.test.mjs`. The runnable `spec-r3f-b008.test.mjs` adds only newly required `document`/`frame` props and a separate result filename; inspect `original-probe-adapter.diff`. Same roof-origin and first-roof/reference mutations now retain UV`[1,2]`, commit0 instead of former `[11,2]`/`[-9,2]`. Its array-change control also passes.

`spec-r3f-b008-extra.test.mjs`:12 additional cases. Unchanged frame makes exactly one grouped move`[1,2]→[3,2]`. Module/other-array/north changes cancel and allow a subsequent real control finish. Parent document changes before child render (roof/reference/module/other-array/north) all reject at the atomic domain guard: attempt1/commit0/document unchanged. Deselect/disable/unmount all stop dragging, detach and emit0writes. The unmounted Group itself is no longer a live scene object; no claim about preserving its disposed transform is made.

`spec-plan-b008.test.mjs`:11 cases. Normal pointerup produces one group`[1,2]→[5,1]`; pointercancel/lostcapture/Escape/blur/Pan/zoom/fit/disable/module changes leave no preview or command; parent-before-child mutation is rejected.

## Reproduce after rebuilding the minimal snapshot

Run `python3 rebuild_snapshot.py` in this directory. In`apps/planner`:

```sh
node --no-warnings=ExperimentalWarning --loader ./tests/spec-expose-scene-loader.mjs --test tests/spec-r3f-b008.test.mjs tests/spec-r3f-b008-extra.test.mjs
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/spec-plan-b008.test.mjs
node --test src/domain/*.test.ts src/data/*.test.ts
npm run build
npm run build:check
```

All46 fixed domain/data and51 fixed DOM cases independently passed; the original3+extra12R3F+11Plan probes all passed. To rerun target DOM tests, select only target-tracked`apps/planner/tests/*.test.mjs` with`git ls-tree` (9files), excluding independent probes that require the exposing loader. Do not run an unrestricted wildcard that mixes the two loaders.

The actual fixed artifacts passed source-manifest and queried-entry/lazy execution checks. An independent TypeScript/Vite build succeeded and all7 emitted files matched the target blobs byte-for-byte; details in`probe_build.results.json`.

## Evidence boundary

Real React19/StrictMode, actual R3F reconciler/Three objects/official controls run here; only GPU render is a no-op, and gestures use controlled control events rather than native physical raycasts. Plan uses real React/DOM events with an explicit CTM/capture fixture. Built ESM graph execution is real but uses JSDOM with no application mount target. These are not native GPU, viewport or full customer-flow acceptance. No native/p548/production operations or parent-source edits were performed. The prior6c review remains historicalFAIL; its six earlier closures remain applicable to unchanged code. Harness-only corrections are recorded separately.
