# Fixed manual geometry editor Spec audit

Target `37f2acd3962e8da3f885b1dd669e831b96b1de9c`; base `8a4a80b132f692062125807e509a57926fb0f518`. Verdict: FAIL, six P2 findings. Only this manual-editor increment is assessed. No complete B/map/whole-goal acceptance is asserted.

## Reproduced findings

1. **pitch90_mismatched_range (P2)**. Contract `docs/specs/548-interactive-design.md:21-22`: “locale-specific decimals and required ranges are checked”. Fixed source `apps/planner/src/components/design/RoofForm.tsx:73,119; apps/planner/src/domain/validateGeometry.ts:154-156`. Actual React/StrictMode intake advertises0to90 and allows90 through field range checks, but actual command returns invalid_roof_basis. Edits0, generic refusal, raw form retained. Probe `apps/planner/tests/spec-editor-probe.test.mjs`.

2. **supported_hole_float32_collapse (P2)**. Contract `docs/specs/548-interactive-design.md:30-31`: “rebase-before-add ... Roof holes and extruded objects use real geometry”. Fixed source `apps/planner/src/components/design/SceneViewport.tsx:99-113`. Actual RoofMesh creates real Three ShapeGeometry with rawUV1e6. A supported0.01m square opening becomes4 Float32 entries at the same coordinate[1000001,1000001,0], distinct count1. GPU rendering cannot recover these lost vertices. Probe `apps/planner/tests/spec-scene-probe.test.mjs`.

3. **fit_camera_omits_obstacle_extent (P2)**. Contract `docs/specs/548-interactive-design.md:31-34`: “Roof holes and extruded objects use real geometry ... Camera/lighting/backend never become engineering inputs”. Fixed source `apps/planner/src/components/design/SceneViewport.tsx:370-406,419-425`. Implementation offers Fit3D view but bounds contain roofs/panels only. Actual component with2x2m roof and30m vertical obstacle chooses camera[2.697,1.838,.980], target[1,0,-1]; real Three camera transform places obstacle top behind camera, cameraSpaceZ+14.118. This is a view-fit defect, not an engineering calculation error. Probe `apps/planner/tests/spec-scene-probe.test.mjs`.

4. **failed_renderer_never_disposed (P2)**. Contract `docs/specs/548-interactive-design.md:35`: “Resources and controls clean up on unmount”. Fixed source `apps/planner/src/components/design/SceneViewport.tsx:482-491`. Controlled failure of actual WebGPURenderer.init during actual component callback produces2 owned renderer constructions in StrictMode, disposal0 even after owner unmount. Callback rejects without returning the instance to R3F. Fallback text is displayed. No claim about measured real GPU memory is made. Probe `apps/planner/tests/spec-scene-probe.test.mjs`.

5. **native_control_cancel_not_released (P2)**. Contract `docs/specs/548-interactive-design.md:31-35`: “camera controls paused during manipulation ... Failure/retry preserves numeric/plan editing”. Fixed source `apps/planner/src/components/design/SceneControls.tsx:61-79`. Real official TransformControls/OrbitControls on real DOM canvas, controlled entered drag state and native pointercancel: Orbit remains enabled=false, transform dragging=true, finish0. Correct pointer-capture fixture primitives are present. This tests cancellation handling, not GPU picking accuracy. Probe `apps/planner/tests/spec-controls-probe.test.mjs`.

6. **lazy_chunk_failure_unmounts_editor (P2)**. Contract `docs/specs/548-interactive-design.md:34-35`: “Failure/retry preserves numeric/plan editing”. Fixed source `apps/planner/src/components/design/DesignEditor.tsx:281-296; apps/planner/src/main.tsx:24-43`. Actual React.lazy import rejection simulating3D chunk failure escapes Suspense to outer workspace boundary. Staged rows text2.5 and Plan switch disappear; local scene boundary is not loaded yet. Whole-app reload is required. Probe `apps/planner/tests/spec-lazy-failure.test.mjs`.

## Reproduction and boundaries

Minimal source/spec/fixtures only; no acceptance/research/build asset copies. Reconstruct exact reviewed files with `python3 rebuild_snapshot.py`; every blob hash is verified and changed files are never overwritten. Dependencies are linked to the existing parent installation, never installed or copied.

From `apps/planner`:

- `node --test src/domain/*.test.ts src/data/*.test.ts` passed39.
- `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/design-editor.test.mjs` passed4 original design tests.
- `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/spec-editor-probe.test.mjs`:1 expected failure(pitch90),2 passes(actual SVG cancel/single move; full project staged guards and save/ack).
- `node --no-warnings=ExperimentalWarning --loader ./tests/spec-scene-loader.mjs --test tests/spec-scene-probe.test.mjs`:3 expected failures, real component/Three geometry/camera/renderer ownership. The loader substitutes only the Canvas/useThree host, does not replace actual SceneViewport, RoofMesh, Three ShapeGeometry or camera math. The hole case reads the real BufferGeometry through React host props. Custom-host React tag warnings are expected from this test-only host.
- `node --no-warnings=ExperimentalWarning --loader ./tests/spec-scene-loader.mjs --test tests/spec-controls-probe.test.mjs`:1 expected failure, real version-locked official controls and real DOM native pointercancel. Control drag-start state is intentionally controlled; no physical picking is claimed. The initial fixture lacked releasePointerCapture; after adding complete pointer-capture primitives the same product failure remained. That fixture omission is not reported as a product bug.
- `node --no-warnings=ExperimentalWarning --loader ./tests/spec-lazy-failure-loader.mjs --test tests/spec-lazy-failure.test.mjs`:1 expected failure, actual React.lazy3D import failure unmounts staged editor. Outer fixture boundary represents the real application-level boundary documented in main.tsx; no local design boundary catches the failed chunk.

Four JSON result files record actual observations: `probe_editor.results.json`, `probe_scene.results.json`, `probe_controls.results.json`, `probe_lazy_failure.results.json`. `review_results.json` contains fixed-source references and method limits.

No GPU rendering, native browser/touch, real backend device-loss memory measurement, EN/DE translation acceptance or production acceptance was attempted. Parent CUA and those release gates remain outstanding. No p548, other task instance or production surface was read/written. No parent source or draft copy records were modified. Review-generated reconstructable copies are reclaimed after SHA verification; only unique probes/results and this reproduction manifest remain.
