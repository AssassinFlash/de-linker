## Spec addendum

Pin: `726e326b5c3ce322a2e1471008483a10e9e3c3b1`; previous review: `786d0db99203d35010b6a7fdc38dc984b3058606`; full-base context: `43297ecf5673fa5f29c82f90fbe583666a5e3e15`. Reviewed delta: `git diff 786d0db9...726e326b`.

**Repeated-success P2 closed; no new confirmed delta findings.** [SPEC:12](../SPEC.md) requires “Successful addition brings its result into view after the property form collapses.” At `apps/planner/src/components/design/MapRoofWorkspace.tsx:71,97–99,270`, every accepted commit advances `completedApplications`; reveal depends on that advancing event count. Input changes and undo/redo do not reset or advance it. Status remains derived from actual protected geometry.

The [independent repeat-submit probe](probe-repeat-submit.mjs), running the fixed application with real React and the existing JSDOM/fake-map/synthetic-review fixture, now [passes both successful focus assertions](repeat-submit.json). After success → undo document restoration → Resume → unchanged submit, the second result receives focus and exactly reproduces the first geometry. Subsequent undo/redo updates status correctly and leaves an unrelated focused control alone. The earlier failing probe/report were preserved.

**Original journal P2 remains closed.** [SPEC:17](../SPEC.md) requires exact uncertain retries and rejects stale overwrite/deletion. Hook/store/domain bytes are unchanged from the reviewed repair. The existing independent journal probe was [re-executed successfully](journal-recheck.json): repeated unknown A acknowledgements settle exact A before newer B; raw invalid fields survive; competing-tab Retry/Discard refuse; explicit fork/discard preserve the other copy. Its embedded b48 baseline label and the 726 source-equivalence check are documented in [snapshot evidence](snapshot-evidence.json).

Independent [focused execution](focused-tests.txt): **3/3 pass, no act warnings**: two Workspace component fixtures and the exact emitted ESM identity fixture. Snapshot checks independently match all **114 source / 7 build** digests and **44 compiled formal-German messages**. Fixed application, test and emitted sources were loaded in memory; no application/test/build files changed.

Native geometry refusal remains unproven under [SPEC:24](../SPEC.md). Synthetic responses, fake ports and a Terra-refused gesture do not establish that native engine path. The owner's remaining native matrix is separate; no native, engineering, production or whole-goal pass is granted.

Spec delta findings: **0 new**. Both previously reported source P2 findings are closed; full goal remains active.
