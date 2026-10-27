## Spec addendum

Pin: `786d0db99203d35010b6a7fdc38dc984b3058606`; previous review: `b48ffda68aeb2e9f17dd27b84f7449e05b321873`; full-base context: `43297ecf5673fa5f29c82f90fbe583666a5e3e15`. Delta: `git diff b48ffda6...786d0db9`. Locations below refer to this pin.

**[P2] Reapplying an unchanged drawing does not reveal its second successful result.** `apps/planner/src/components/design/MapRoofWorkspace.tsx:71,97–99,271`. [SPEC:12](../SPEC.md) requires “Successful addition brings its result into view after the property form collapses.” Reveal depends on boolean `applied`. After success → common-undo document restoration → Resume drawing → unchanged submit, it remains true. The second `setApplied(true)` cannot rerun the effect.

The [independent actual-component probe](probe-repeat-submit.mjs) loaded frozen application code with installed React and the existing JSDOM/fake-map/synthetic-engine fixture. [Observed result](repeat-submit.json): two successful requests/commands; first result focused; after the unchanged second submission focus became `BODY`, not the result section. No native scroll claim is made. A monotonically advancing successful-application event can trigger every accepted submit without coupling focus to undo/redo. The owner acknowledged this defect and committed a later repair; that later pin is not reviewed here.

The geometry-derived status at Workspace:414 correctly follows restoration/reapplication; the generic-error wrapper at `MapRoofProperties.tsx:212` uses the existing sticky-offset class. No other delta defect or scope creep was found.

Independent [focused execution](focused-tests.txt): **14/14 pass**, no act warnings. The new repeat-submit probe exposes the uncovered path. [Built ESM identity execution](built-module-identity.txt): **1/1 pass** with the exact pinned manifest/chunks loaded in memory. [Snapshot evidence](snapshot-evidence.json) matches all 114 source and 7 build digests and 44 compiled German messages.

The original uncertain-write P2 remains closed: unchanged hook/store/domain bytes were re-executed through the [previous probe](../review-spec-b48ffda6/probe-final-recovery.mjs); [recheck results](p2-unchanged-hook-recheck.json) again preserve raw B, replay exact A, and refuse competing-tab overwrite/deletion. Its embedded b48 baseline label is explained in snapshot evidence. Earlier reports/probes were preserved.

Native geometry refusal remains open under [SPEC:24](../SPEC.md). A Terra-refused crossing gesture or injected engine response is not native engine-refusal proof. No native, engineering, production or whole-goal pass is granted.

Spec delta findings: **1 P2**; original journal P2 remains closed. A new-pin review is required.
