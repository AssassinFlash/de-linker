# Spec repair re-review: f1a0dee9

Full base: `252a022e41f8ca5426d6463206c8346eb89da5f1`. Previous review: `a1281d9d1e4829b866cef89f8c23e6aecb7b91ce`. Fixed pin: `f1a0dee90dd719ce5532724a9f6e9021f1555705`.

Reviewed `git diff a1281d9d1e4829b866cef89f8c23e6aecb7b91ce...f1a0dee90dd719ce5532724a9f6e9021f1555705`; one repair commit, `fix(planner): refuse boundary checks skipped by an invalid parent roof`. The original full-diff report and its two failing counterexamples remain preserved in `review-spec-a1281d9d/`.

**Original P2 closed; 0 new Spec findings.** `MapDrawingWorkspace.tsx:288–291` now refuses `invalid_roof_polygon` for the edited target's own parent roof. This satisfies [SPEC.md:33–36](/Users/chesterjohn/Documents/de-linker-worktrees/unified-planner-548/docs/acceptance/2026-10-24/548/map-ring-ui/SPEC.md:33): “an invalid edited polygon refuse application and retain the edit,” while “Other layout conflicts remain visible through the ordinary layout review.” It does not reject every unrelated diagnostic. The idle “Map drawing” heading describes the shared region; active new-roof and boundary headings remain distinct. No additional scope expansion found.

The [independent probe](engine-gate-probe.test.mjs) repeats the original actual-component, journal, installed Terra/adapter pointer transaction and real Python/Shapely checker. Both self-crossing child cases now produce **0 commits**, remain active, retain exact edited metric points and have no prepared result. Added real-engine controls for both child kinds use a valid selected parent plus a different invalid roof: each valid target commits exactly once. **4/4 pass**, with actual geometry diagnostics retained in [output](engine-gate-probe-output.txt); no geometry report is injected.

The related React/journal suite independently passes **23/23**, including exact uncertain-write retry, stale-tab protection, separate-copy identity, native-confirmed retirement and stale query/prepare guards. Those journal implementations are unchanged by this repair. `node bin/build-manifest.mjs check` passes; [identity](identity.json) verifies **121 source and 7 emitted files** against the commit and current disk, and records preserved prior-evidence hashes.

Commands: from repository root, `node --no-warnings=ExperimentalWarning --loader ./apps/planner/tests/tsx-loader.mjs --test docs/acceptance/2026-10-24/548/map-ring-ui/review-spec-f1a0dee9/engine-gate-probe.test.mjs`. From `apps/planner`, `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/map-roof-recovery.test.mjs tests/map-roof-workspace.test.mjs`; `node bin/build-manifest.mjs check`.

This is Spec source/fixture evidence only. Standards is pending separately; native GPU/provider/touch, EN/DE × 1440/390, engineering, production and whole-goal acceptance remain outside this result.
