# Fixed editor follow-up Spec evidence

Target `6c6680ad4e2eb890b08c58b5a9bffd95ecb48957`; full base `8a4a80b132f692062125807e509a57926fb0f518`; patch base `37f2acd3962e8da3f885b1dd669e831b96b1de9c`. Verdict: FAIL for one remaining P2 class with two independent frame-dependency variants. All six previously reproduced issue classes are closed against their original input data.

## Remaining P2: changing a gesture frame is accepted as movement

Contract `docs/specs/548-interactive-design.md:24-25`: “Apply is a guarded immutable command; stale before-values ... rejected without overwriting current work.” Lines30-33 require local-plane handles and the same final command path.

Fixed source `apps/planner/src/components/design/SceneViewport.tsx:266-303` stores the array and roof at start but its `put_array` command only compares `before.array`; `apps/planner/src/domain/geometryCommands.ts:114-117` has no roof/reference precondition. During a drag, R3F applies new group transforms, which finish then misinterprets as user displacement.

Variant1: active array on second roof, original UV[1,2]. Roof origin changes from[30,-20,4] to[40,-20,4], array unchanged. Finish commits array UV[11,2]. Variant2: selected roof unchanged, first roof origin changes from[10,-20,4] to[20,-20,4], changing SceneViewport's reference. Finish commits UV[-9,2]. An array.name change control correctly rejects the stale gesture. These are actual R3F scene objects and actual command application, not a DOM Group replacement.

`probe_r3f_cas.results.json` records both variants, the rejection control, and four passing cancellation cases. The source fixture controlled a valid drag-start state rather than claiming physical GPU picking.

## Reproduction

Only minimum fixed source/spec/fixtures were copied. Restore after SHA-verified reclamation with `python3 rebuild_snapshot.py`. Every blob SHA256 is checked and changed files are never overwritten. Dependencies are symlinked, not installed/copied; actual installed versions are recorded in `probe_environment.json` and match the fixed declaration.

From `apps/planner`:

- `node --test src/domain/*.test.ts src/data/*.test.ts`:45 passed.
- All target-tracked `tests/*.test.mjs` using `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test <tracked files>`:51 passed. Do not use an unrestricted wildcard after reconstruction: this evidence folder also contains intentionally red independent probes requiring separate loaders.
- `node --no-warnings=ExperimentalWarning --loader ./tests/spec-expose-scene-loader.mjs --test tests/spec-r3f-reference.test.mjs`: one control passes, both frame variants fail. The loader only appends exports of private functions, leaving implementation bodies unchanged. Actual R3F reconciles real Three Group/InstancedMesh and official controls. The provided renderer's render method is a no-op and frameloop is never; this does not exercise GPU rendering.
- Same loader with `tests/spec-r3f-cancel.test.mjs`: the same two failures plus passing pointercancel/lostpointercapture/Escape/blur cancellation after a changed frame; all cancellation routes yield0attempt/0commit and restore the current origin.
- `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/spec-signed-zero.test.mjs`: passes actual manual roof creation through full ProjectEditor, first503 uncertain save, same-wire explicit retry, canonical0 acknowledgement, revision2, pending cleared, local signed zero and Undo preserved.

The original37f2 probes remain byte-for-byte unchanged, with hashes in review_results.json. Separate `spec-editor-6c.test.mjs`, `spec-scene-6c.test.mjs`, `spec-controls-6c.test.mjs` adapt only the new contract/API/frame:90deg is explicitly refused at its field, actual local mesh positions are transformed back before comparing the same1cm hole, and the new required cancel callback is supplied. These adapters all pass. Existing `spec-lazy-failure.test.mjs` passes unchanged with its loader.

Adapter commands use the ordinary tsx loader for editor, `spec-scene-loader.mjs` for scene/controls, and `spec-lazy-failure-loader.mjs` for lazy failure. Scene host double tests inspect real Three BufferGeometry/camera and ownership behavior, but do not claim physical GPU results. Existing root module identity/query URL behavior is not exercised by direct source imports. Parent found that native issue separately and is fixing it; it is not counted as our independently verified finding.

No p548/native instance, production surface, browser automation or shared WIP was used. No parent files or copy records were changed. Full B/map/whole-goal acceptance is not asserted. Unique probes/results remain; reconstructable source copies are reclaimed by fixed Git blob identity.
