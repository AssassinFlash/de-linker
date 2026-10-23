# Standards recheck — b0080ec1

Fixed source: `b0080ec15eb2dcab6b2c22b7b029180a2c1f73c2`; full diff `8a4a80b1...b0080ec1`, repair diff `6c6680ad...b0080ec1`. Independent minimal archive; no parent worktree/native/production mutation.

**Standards PASS.** No remaining documented-rule violation or actionable heuristic smell found in this fixed increment. The Fowler baseline is a judgement aid, not a hard rule. Existing initial-editor review findings remain recorded in their original evidence; the active-transform unmount finding is now closed.

Standards read: repo AGENTS/CONTEXT/domain, accepted isolated-runtime ADR, interactive-design/geometry/workbench specs; current main AGENTS §0 and local-storage rule govern snapshot retention. Relevant responsibilities: disposable render state never becomes project authority; cancelled gestures never commit; atomic edits are checked against current inputs; React runtime remains app-isolated; built hashes and lazy chunks must match source; customer EN/DE text stays truthful.

## Independent evidence

- Original `standards-unmount-transform-probe.mjs` copied byte-for-byte, SHA recorded in results.json. Its old bug assertion fails at [7,2,3] because actual position now returns [1,2,3], cancel=1, finish=0. See original-transform.log.
- `standards-controls-recheck.mjs`: 8 PASS with actual locked Three TransformControls and actual React 19 StrictMode. Handles unmount, whole frame change, Escape/blur/pointercancel/lostcapture, and normal finish. Whole Panels unmount runs actual production callbacks; a test group host clears the ref in layout cleanup before passive controller cleanup, proving the null-ref path does not throw/submit. The no-GPU R3F host is explicit; this is not GPU/browser acceptance. See controls-recheck-final.log.
- `standards-plan-recheck.mjs`: 12 PASS, real PlanViewport event handlers. Cancel and camera/tool changes remove previews; document changes cancel; a changed module document **before React rerender** reaches commit but is refused by the whole-document guard. Normal completion commits once. Synthetic CTM and pointer capture are explicit; JSDOM does not implement native removal releasing capture, so that browser property is not asserted. See plan-recheck-final.log.
- Fixed `npm test`: 46 domain/data + 51 React DOM PASS. See suite-final.log. The first minimal archive omitted two fixture JSONs; they were fetched at the same fixed SHA before the final run. This was snapshot setup, not a product defect.
- Fixed `npm run build:check`: manifest/source hash check plus actual emitted queried entry and every dynamic entry PASS. The initial entry scans mounts once; lazy imports do not execute it again. The emitted entry and scene both import the same hashed core and runtime, and neither core nor scene imports planner.js. See build-check.log. No regeneration was needed.
- Added-code legacy identifier scan: no tv_b2b_/Linker_AI_/dlk- matches. Generated Three shader whitespace is not hand-written product formatting.

## Relevant source hunks

At fixed SHA, `apps/planner/src/components/design/SceneControls.tsx:101` cancels before detach/dispose; `SceneViewport.tsx:284` tolerates a null group during cancellation; `SceneViewport.tsx:291` blocks stale frame finish; `geometryCommands.ts:92` enforces atomic geometry_frame_changed. `PlanViewport.tsx:59` clears gesture/capture, `:212` carries the full before-document. `vite.config.ts:20` isolates initial dependencies in hashed core; build-manifest.mjs:89 refuses entry back-imports; tests/built-modules.mjs:48 imports the real WordPress-style queried entry.

## Final copy consistency

Copy PASS retained: no PO/script catalogue or design-copy-final.json delta since 6c6680ad. The earlier independent 259-message English/source/German PO/script-JSON comparison therefore remains applicable, including preserved existing translations. Canvas label/fallback now reuse the already translated “Roof design”; fallback text no longer announces renderer failure in accessibility content before a failure occurred. The runtime error path still has its truthful failure/retry/2D recovery text. No new unreviewed customer promise was introduced.

## Boundary and retention

This is Standards and copy consistency for the fixed increment. No claim of full B, the complete A–D tool, native GPU/browser matrix or production acceptance. Parent owns native evidence. Only unique probes, logs, manifest and report remain after per-file SHA reclamation of the 118 reconstructible fixed files and the dependency symlink; cleanup.json records the actual result.
