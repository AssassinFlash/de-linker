Standards evidence for base `71b54073622117c12953cd40957ec1f5d4d827a6` → pin `1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb`.

Review scope was the complete 65-file diff, including all changed handwritten source, schemas, tests and fixtures, specification, EN/DE drafting/review/final evidence, compiled language delivery, emitted planner graph and source manifest. Generated vendor content was evaluated through the actual graph execution and source/hash guard rather than reverse-engineered minified vendor code. The 1,171-line saved-result fixture is also checked in full for JSON equality to its recorded managed HTTP result.

The initial HEAD and tracked source were verified at the requested pin before the fresh checks. The root agent subsequently changed `ScenarioForm.tsx`, `RunBasis.tsx` and added `batteryPresentation.ts` to repair the reported P3. Those changes are excluded from the original report and recorded separately in `addendum-4943aef7.md` at immutable pin `4943aef76d26a81cfc9ad035f689007995509dc3`. No source or tracked artifact was changed by this reviewer.

Standards sources read: owned `AGENTS.md`; current main-repository `AGENTS.md` storage/service overrides and `docs/agents/local-storage.md`; root `CONTEXT.md` and `README.md`; `docs/adr/0002-isolated-planner-runtime.md`. The task’s complete Fowler smell baseline was applied as a heuristic. The originating `docs/specs/548-energy-workspace.md` supplied feature context. Earlier approved copy evidence was read together with its final closure, not treated as an outstanding draft rejection.

Focused findings considered: durable intent storage before mutation dispatch; exact-body/idempotency receipts; account/scope/owner fences and unmount behavior; acknowledgement and safe release boundaries; the named pre-mutation revision refusal; explicit null/zero handling without manufacturer defaults; runtime/result/manifest/source identities; uncoerced schema parsing; immutable numerical output and undefined-ratio reasons; operational periods and loss-origin semantics; native localized delivery; scoped WindPress ownership. No physical model or numeric-result changes were introduced by the reviewed increment.

The P3 finding is a maintainability judgment about duplicated presentation shape, not a functional failure or a documented architecture violation. No line-count finding was raised: `AGENTS.md` explicitly defines modularity by framework and feature responsibility rather than line count. `ScenarioNumber` owns validity lifecycle behavior and is not a merely delegating wrapper. Contract types repeated across language boundaries were not automatically treated as speculative abstraction opportunities.

Fresh commands below used existing dependencies, performed no build/dependency sync, and started no site, service or native browser. Node fixtures use fake IndexedDB/jsdom and mocked transports. Python’s two focused tests exercise schema exports and do not instantiate the workspace DB fixture. Exact stdout is retained in the small logs alongside this file.

From `apps/planner`:

```sh
node bin/build-manifest.mjs check
node --test tests/built-modules.mjs
```

Result: source-manifest match, one graph test passed; see `build-graph.log`. Node emitted its module-type inference warning while importing the WordPress-served ESM entry in the test harness; the emitted graph executed and passed. No package configuration was changed to silence that warning.

```sh
node --test src/domain/energyScenario.test.ts src/domain/profileCoverage.test.ts src/data/energyProtocol.test.ts src/data/EnergyIntentStore.test.ts src/data/siteIntegration.test.ts
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/energy-operations.test.mjs tests/energy-workspace.test.mjs
```

Result: 18 + eight tests passed, zero failures; see `contracts.log`.

For the pinned `4943aef7` repair, the source-manifest check, emitted graph test and the eight React tests above were rerun independently and passed; see `closure-checks-4943aef7.log`. No rebuild or broad suite rerun was needed for this presentation-only extraction. The original 18 domain tests and two Python export tests are recorded at their original full pin, not claimed as newly run on the repair.

From `services/engine`:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -p no:cacheprovider tests/planning/test_browser_energy_contracts.py -q
```

Result: two passed; see `schema-exports.log`.

From repository root:

```sh
python3 -B docs/acceptance/2026-10-24/548/energy-workspace/review-standards-1b0b5d7d/artifact_probe.py
git diff 71b54073622117c12953cd40957ec1f5d4d827a6...1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb -- ':!docs/acceptance/**' ':!plugins/linker-tools/build/**' ':!plugins/linker-tools/languages/**' | rg -n '^\+.*(tv_b2b_|Linker_AI_|dlk-|TODO|FIXME)'
```

The small artifact probe reads immutable blobs with `git show` and writes nothing. Result: 187/187 final German entries match both compiled catalogs with placeholder parity; the complete run fixture equals the recorded managed HTTP finished result (`artifact-probe.log`). The legacy-marker scan returned no matches (rg exit 1), covering added runtime/source/test/spec lines. That scan supports this increment review; it is not a claim of whole-repository parity with a previous system.

No instances, dependencies, services, credentials, external research, native DB or browser were used. Only this owned review directory was written. Native UI, deployment and production acceptance remain the root task’s separate gates.

Action-error focus review and test repair:

The full `4943aef7...bd2cba70` diff was reviewed, including regenerated graph/manifests. The focus implementation followed the existing helper and ownership/scope pattern. A concrete test-quality P3 was reported because matching BODY text could pass without focus moving. The read-only owned `no-reveal-loader.mjs` replaces only `revealActionResult` with a no-op during module loading, with no source mutation. At `bd2cba70` the workspace test falsely remained green (`no-reveal-mutant-bd2cba70.log`).

The complete test-only repair `bd2cba70...cda1b7df188b78db561c3cbd6d475e2b968c8788` was reviewed. The final test explicitly focuses Prepare and checks exact error-wrapper identity with a boolean assertion. Actual component behavior is green and the identical no-reveal mutant is red at the intended assertion, rather than at a timeout. Final independent commands from `apps/planner`:

```sh
node bin/build-manifest.mjs check
node --test-timeout=10000 --test tests/built-modules.mjs
node --test-timeout=10000 --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/energy-workspace.test.mjs
node --test-timeout=10000 --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --loader ../../docs/acceptance/2026-10-24/548/energy-workspace/review-standards-1b0b5d7d/no-reveal-loader.mjs --test tests/energy-workspace.test.mjs
```

First three commands: exit 0, manifest match, one graph test and one real workspace workflow passed (`focus-actual-cda1b7df.log`). Final command: intentional exit 1, `ERR_ASSERTION` at line 220 with the exact-focus message, boolean false versus true, no timeout (`no-reveal-mutant-cda1b7df.log`). All checks used the final HEAD with no tracked modifications. No build or dependency sync occurred.

Storage/resource closure: the superseded intermediate `1ea2a5ab` actual workflow was green. Its direct DOM-object equality failure caused expensive Node assertion formatting (approximately 40 seconds and 1.3 GiB observed child RSS) and produced only a generic 304-byte child-failure log. The process had already exited before an attempted own-probe termination could reach it; no shared service was targeted or changed. Both superseded intermediate logs were removed after recording this compact metadata. Original unique false-green evidence and final compact RED/GREEN logs are retained. No probe child remains.

Native-driven source repair review:

Reviewed the entire 16-file delta `cda1b7df188b78db561c3cbd6d475e2b968c8788...443eb71d7a9245942aa0d9a6e6de53acde9a867c`, including all six source files, three fixtures/tests and seven emitted asset/manifest file changes. Full source/test hunks and manifest references were read. Generated minified code was checked through source/hash consistency and the real emitted graph test. No CSS, customer message, backend, physical model or numeric result was changed by this delta. HEAD and tracked cleanliness were checked before and after verification.

The review considered the full-context versus semantic-focus distinction; selected-run identity rather than poll response identity as the reveal trigger; animation-frame cleanup; connectedness, current focus and scope fences for late correction; bounded one-shot scheduling; existing observers' connect/disconnect and CSS-property ownership; and local validation state versus durable operation errors. Gathering native bar measurement in one function with three real consumers is a justified shared responsibility, not speculative generality. The small fixture animation-frame setup is not a material duplicated business-logic finding.

Fresh commands from `apps/planner`, without builds or dependency sync:

```sh
node bin/build-manifest.mjs check
node --test-timeout=15000 --test tests/built-modules.mjs
node --test-timeout=15000 --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/energy-workspace.test.mjs tests/workspace-lifecycle.test.mjs
```

All exited 0: source-manifest match; one emitted lazy-module graph test; 18 React workflow/lifecycle tests including subtests. The existing Node ESM inference warning is recorded as before; no configuration was changed. See `closure-checks-443eb71d.log`.

From repository root:

```sh
node docs/acceptance/2026-10-24/548/energy-workspace/review-standards-1b0b5d7d/reveal-lifecycle-probe.mjs
git diff cda1b7df188b78db561c3cbd6d475e2b968c8788...443eb71d -- apps/planner/src apps/planner/tests | rg -n '^\+.*(tv_b2b_|Linker_AI_|dlk-|TODO|FIXME)'
```

The owned probe imports the unchanged real helper using the existing application jsdom dependency, supplies only synthetic DOM geometry and frame delivery, and writes nothing. It verifies current measured heights before initial scrolling, full marked context selection, exactly one late correction for occlusion, no correction when clear/focus moved/scope withdrawn/target removed, and no initial work for unadmitted/disconnected targets. Six cases passed (`reveal-lifecycle-443eb71d.log`). The marker scan returned no matches, rg exit 1. The probe closes its synthetic windows and schedules no real timers. Existing workflow/lifecycle test processes exited successfully; no process or application was started for native acceptance.

These are fresh independent Standards checks at the pinned source, not a claim that the root's native viewport matrix or production acceptance is complete. All reviewer writes remain inside this assigned directory.

Automatic history-selection repair review:

Reviewed the complete eight-file delta `443eb71d7a9245942aa0d9a6e6de53acde9a867c...ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a`: every hook and new test hunk, emitted manifest references, source hashes and actual emitted graph. The unchanged `select`, `readRun`, `replacePlannerLocation` and native language-link integration were read for context. No customer copy, physical model, backend request contract, style, dependency or storage operation changed. The timestamp in the test is identified as an observed fixture value, not a product rule or threshold.

The new effect is attached to the hook that already owns selected-run state and URL navigation. It waits for the selected run's full reader validation, checks active/current admission and selected-null state, then uses the existing guarded selection method. That method rechecks scope and matching project immediately before changing URL or selected state. Reusing it is appropriate responsibility gathering rather than a middleman or unrelated divergent change. The effect's stable ID dependencies avoid a polling object becoming a navigation trigger; explicit selected IDs disable automatic selection.

Fresh commands from `apps/planner` at exact HEAD `ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a`, with no tracked modifications before or after:

```sh
node bin/build-manifest.mjs check
node --test-timeout=15000 --test tests/built-modules.mjs
node --test-timeout=15000 --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/energy-runs.test.mjs tests/energy-workspace.test.mjs tests/workspace-lifecycle.test.mjs
```

All exited 0: source-manifest match; one emitted lazy-module graph test; 19 hook/workflow/lifecycle tests including subtests. See `closure-checks-ceb4a896.log`. The existing Node ESM inference warning is recorded without a configuration change.

```sh
git diff 443eb71d7a9245942aa0d9a6e6de53acde9a867c...ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a -- apps/planner/src apps/planner/tests | rg -n '^\+.*(tv_b2b_|Linker_AI_|dlk-|TODO|FIXME)'
```

The added-line marker scan returned no matches (rg exit 1). No additional probe, broad suite, build, dependency sync, service, native database or browser action was necessary. These checks close the Standards axis for the small URL repair and retain the prior full-diff reviews; they do not claim the root's ongoing native or production acceptance.
