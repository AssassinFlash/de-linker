# Independent Standards addendum

**PASS: 0 documented-standard breaches; 0 actionable Fowler heuristic concerns.** This supplements, rather than replaces, the complete review at `review-standards-f1a0dee9/REVIEW.md`.

Reviewed the complete diff `f1a0dee90dd719ce5532724a9f6e9021f1555705...6b2a8a4cc43c95d4710fcb42f16d1bd1e4a8c100`: `df750434` restores map-property links; `6b2a8a4c` repairs the browser-timer fixture. Actual HEAD and both source files plus the changed test matched the final pin. Generated module/source-manifest identity also passed independently; hashes are in `CHECKS.json`.

The original standards sources and full Fowler baseline remain applicable. Under AGENTS §4, CONTEXT's shared-model boundary and the isolated-planner runtime decision, this is a routing/presentation change: neither domain geometry nor project history, persistence, identity admission, engine or site-wide React changes. `ProjectEditor` recognizes the two existing public fragments using one shared constant. `DesignEditor` consumes `initialMapView` only in its `useState` initializer; later prop/render changes cannot force the customer back to Map. Default entry remains Plan. No new package, CSS channel, customer text, translation or external fact was introduced.

AGENTS §5 requires evidence at the changed layer. The fixture now supplies observers and a timer-backed animation-frame pair that plain JSDOM supports, and restores original global descriptors after disposal. It does not emulate a successful geometry calculation or claim native rendering. No documented rule is breached. The narrow boolean initialization input expresses the present requirement; it is not speculative generality or a separate saved scene. No actionable duplication, naming, responsibility or other baseline smell was found in this increment.

Independent commands, both in `apps/planner`:

- `npm run build:check`: exit 0, 1 test passes.
- `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/workspace-lifecycle.test.mjs`: exit 0, all 16 tests pass, including both property fragments and existing ownership/lifecycle cases. No act/uncaught failures appeared.

The existing Node module-type warning remains non-fatal. I did not rerun the full suite or use the other reviewer's probes as my evidence. No native browser/GPU/touch, engineering or production acceptance is asserted. Only this small report directory was written; the instance, browser, dependencies, other evidence and source were untouched. Review work is finished and released.
