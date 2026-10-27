# Independent camera Standards record

Reviewer: `/root/geographic_standards_e138`. Target `f48228a87894c23f68d180675d05b902139d531e`; base `eff8341d5a0eaf24999f42854da6339032c65c9c`. One commit: `fix(planner): frame roof surfaces for desktop and narrow 3D views`. All conclusions concern the fixed commit, not concurrent working-tree corrections. The accepted import review at eff8341d remains intact.

## Scope and rules

The tracked fixed tree contains `AGENTS.md` and no additional CONTRIBUTING/CODING_STANDARDS/CLAUDE instructions. `CONTEXT.md`, the accepted isolated-runtime decision, and the scoped roof-import specification supply domain/runtime boundaries. The current main-repository storage policy was read before creating the single bounded snapshot. The reviewer did not create a worktree, server, site, copied dependency directory, or external research request. The evidence and source hashes are in `source-evidence.json` and `snapshot-manifest.json`.

The accepted isolated runtime overrides the generic WordPress React rule for this application. This increment changes no package or lockfile, global React runtime, native WordPress mount, server endpoint, saved project data, engineering computation, WindPress stylesheet, or legacy application code. Source classes continue using the existing WindPress volume. Camera data is render state. The new camera domain function and effect component have consumed interfaces; they are not an unused replacement framework. New source has no `tv_b2b_`, `Linker_AI_`, or `dlk-` identifiers. No old custom code was introduced by this diff.

Composition weights 0.5 U and 0.75 project-Up, the 75-degree lens and 1.1 distance margin are explicitly internal display policies. Clipping scales with the scene and is described as display policy. The sphere-fit formula uses the smaller horizontal/vertical half angle; it is not a measurement, shading or engineering-release calculation. The unchanged metric data assertion passes in the independent control case. The module’s selection resolution and the UI’s stale extent are separate behavior defects described below, not evidence of an incorrect engineering kernel.

## Documented Standards finding

**S1 [P3] Incomplete shipped GNU catalog.** Fixed PO lines 4728–4741 and browser WP JSON contain the reviewed three messages, but fixed `linker-tools-de_DE_formal.mo` contains none. GNUTranslations returns the English inputs. Its SHA-256 is `a4ba4a4610901c3fc30d9b05ac4c875c624cfe1846a494ba6188c7e43f31c78c`. `AGENTS.md:60` requires synchronous language delivery; line 64 describes the i18n pipeline and line 72 explicitly ships `.po/.mo`. The source/emitted/PO/WP JSON comparisons all pass. Thus this is artifact consistency, not a claim that the current browser translation path is failing. The working `.mo` was already changed by the owner and was intentionally not substituted for the fixed file. `catalogs.py` is the executable check; complete original output is `catalogs.log`.

## Separate behavioral counterexamples supplied to the Spec axis

**B1 [P2] Geometry edit followed by resize uses stale extent.** New `SceneCamera` correctly computes perspective distance for the supplied framing. But the parent at `SceneViewport.tsx:493–496` captures initial bounds in state and updates them only when null or explicitly fitted/retried. Its child at lines 634–635 receives the old framing and Orbit target after ordinary geometry changes. The test mounts one actual validated roof, changes the real document to include another roof 1,000 metres away, retains the existing orbit as required, then resizes to 390×800. Actual camera direction is preserved, but the old centre/radius/far bound is used. Four of eight actual roof vertices project outside the frustum; NDC x reaches about −3.47 and far remains 86.8273, while the current Box3 centre has x=500. This contradicts spec lines 98–99. The test uses real React state/effects, application components and Three projection, with an explicit controlled useThree/Canvas boundary. It does not fake a successful native renderer or claim physical touch. The initial narrow whole-scene control and explicit selected-roof Fit pass on the same boundary.

**B2 [P2] Panel selection loses its owning roof.** Domain `sceneViewDirection` lines 17–24 recognizes array, obstacle, keepout, and roof IDs. Actual mesh selection at `SceneViewport.tsx:205–208` passes `pose.id`. A validated two-roof fixture with the actual pose `array:0:0` on `second` reproduces the mismatch. Selecting the array resolves the second roof; selecting its panel resolves the first. Expected direction is `[-0.31234752377721214,0.7808688094430304,0.5410017808004594]`, actual `[0.274721127897378,0.961523947640823,0]`, identical to roof one's direction. This violates spec lines 91–92, and it is not an invented panel ID. The existing `DesignEditor.tsx:94–96` already resolves actual poses to arrays; ownership can be resolved using that domain fact, not punctuation parsing. `selected-panel.test.mjs` and its original log preserve the counterexample.

S1 is the Standards gate. B1/B2 are forwarded to the separate Spec axis and are not silently recast as hard coding-style rules.

## All twelve Fowler judgments

The repository overrides these heuristics; none is a hard ban. Tool-enforced style/type checks are not restated as manual findings.

| Baseline | Judgment in this increment |
| --- | --- |
| Mysterious Name | No actionable naming finding. Camera/framing/request and display-policy comments identify the concepts; stale framing is a data-flow defect, not a renaming fix. |
| Duplicated Code | No separate actionable duplicate. Shared perspective math is extracted and consumed; the short pre-Canvas camera seed and effect have distinct initialization/lifecycle roles. |
| Feature Envy | No finding. Pure functions over validated domain DTOs match the functional domain model; adding methods to serialized geometry would not be justified. |
| Data Clumps | No finding. `SceneFraming` groups centre, extent and initial direction. Explicit Fit request is an event identity, not another geometric field. |
| Primitive Obsession | Possible smell: heterogeneous selected IDs are interpreted ad hoc in camera code. The panel counterexample demonstrates why a resolved selection/owner is useful. A typed resolver can express the current required variants; no speculative hierarchy is requested. |
| Repeated Switches | No recurring discriminator cascade in the new hunks. Backend identification remains a single existing classification. |
| Shotgun Surgery | No finding. Source, tests, emitted chunks and language artifacts are the repository’s required consumers, not an avoidable scattering of business behavior. The missing MO is S1. |
| Divergent Change | No finding. Domain camera math is separate from React camera effects; SceneViewport remains scene composition. No unrelated application feature is added. |
| Speculative Generality | No finding. New helpers and request state all have present consumers; no unused future renderer abstraction is introduced. |
| Message Chains | No finding. Three vector method chains are its intentional fluent math API, not hidden traversal through unrelated objects. |
| Middle Man | No finding. SceneCamera owns perspective mutation and invalidation effects, not mere forwarding; SceneFraming is a meaningful aggregate. |
| Refused Bequest | No new subtype with an ignored contract. Existing React error-boundary inheritance is framework-prescribed and unchanged. |

## Copy and controls

The approved draft SHA remains `d44b0cb0f5a415f12996ae429365d53a8343566bd50e0857265ec28966f9a008`. All three final pairs match the previous independent feedback exactly. The original Hard Stops/formal German judgment remains applicable; no new copy was silently substituted. New source/emitted strings agree with PO/WP JSON. Generic `3D` and existing Fit text retain their meaning; native renderer names now reside in a data attribute. Compatibility mode remains in the 3D disclosure with its explicit local help, without electrical-compatibility or universal-device claims. The controlled DOM case verifies native details/summary elements, an actual checkbox within a label, and its uniquely associated help. It does not certify screen-reader output, physical gestures, or native visual layout.

## Execution and retention

`targeted-domain.log`: seven real camera/buffer/lifetime cases pass. `emitted-graph.log`: source-manifest verification and the real emitted lazy ESM graph pass. `controlled-lifecycle.log`: one control passes, resize counterexample fails. `selected-panel.log`: actual pose counterexample fails. `catalogs.log`: all three fixed GNU entries are missing, while other consumers match. `execution-results.json` records commands and original full-log hashes. The controlled boundary deliberately does not execute WebGPU, install OrbitControls, or claim renderer resource identity; that remains the owner’s independent native/lifecycle acceptance responsibility.

The one temporary SHA snapshot contains only the minimum existing source/dependency graph required to execute these cases; dependencies are linked, never copied. `snapshot.py` records owner, purpose and a two-hour maximum lifetime. Rebuild without overwriting this FAIL: copy the unique executable scripts into a fresh review-owned evidence directory, run `python3 snapshot.py` and `python3 run.py` there, then `python3 cleanup.py`. The scripts refuse to replace existing manifests/results. It SHA-checks original source and exact generated test copies, verifies logs and the single dependency symlink, removes only this known temporary directory, and reads back absence/free space. Unique scripts, original red logs, metadata and reports remain here. Parent/native/production edits and earlier FAIL evidence remain protected. A camera increment verdict never accepts the full A–D workbench or production.
