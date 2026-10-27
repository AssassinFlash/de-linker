## Spec

Pin: `b48ffda68aeb2e9f17dd27b84f7449e05b321873`; base: `43297ecf5673fa5f29c82f90fbe583666a5e3e15`. Full diff: `git diff 43297ecf...b48ffda6`. Commits: `9efd14fc`, `02c87049`, `b48ffda6`. Locations below refer to this pin.

**Original P2 closed.** [SPEC:16](../SPEC.md) requires “Unknown write acknowledgement is retryable with exact bytes” and prevents stale overwrite/deletion. `apps/planner/src/data/useMapRoofDraft.ts:138–173` retains and acknowledges the exact pending intent before newer bytes; :254–281 settles an unknown write before exact deletion. Deterministic pre-mutation refusals clear that intent without weakening journal CAS.

An [independent probe](probe-final-recovery.mjs) injected two consecutive committed-but-unknown acknowledgements for one-point A, then entered two-point B with an invalid raw numeric string and called public Retry. [Results](final-recovery.json): exact A bytes replayed before B; **2 open / 2 durable points**, invalid raw pitch retained, failure cleared. Competing-tab edits then made edit/Retry/Discard refuse without overwriting or deleting that version; explicit fork preserved both. Discarding a separate unknown drawing settled its intent and removed only its owned record. The earlier failing probe/report remain byte-for-byte unchanged.

**Validation placement conforms at source/fixture level.** [SPEC:11](../SPEC.md) requires “value, focus and associated error message together.” `MapRoofProperties.tsx:33–38,57–76` keeps input focus and associates its adjacent alert through `aria-describedby`; :211–214 makes a generic refusal focusable beside submit. `MapRoofWorkspace.tsx:511–515` suppresses the distant duplicate while staged. Independent [focused execution](focused-tests.txt): **10/10 tests pass, no act warnings**, covering these associations/focus, staged refusal, recovery, scope fencing, prepared retirement and provider replacement. These use real React/domain/library code with fake browser/storage/map ports.

No further confirmed source Spec defects or scope creep were found against the original full increment. [Snapshot checks](snapshot-evidence.json) independently matched 114 source and 7 emitted-build digests, plus all 44 compiled formal-German messages.

Native acceptance under [SPEC:23](../SPEC.md) remains separate. The owner reports a native success-feedback scroll defect and plans a later repair; that delta requires a new pin review. This report grants no native, engineering, production or whole-goal acceptance. Existing-ring/hole/obstacle and other full-goal requirements remain active ([SPEC:25](../SPEC.md)).

Spec source findings: **0 new, 0 unresolved from the prior review**. Native acceptance remains open.
