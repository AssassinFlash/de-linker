## Spec

Review pin: `9efd14fcb79687344d676a8fdb5fbd24c2e9aad8`; base: `43297ecf5673fa5f29c82f90fbe583666a5e3e15`. One commit, `feat(planner): mount recoverable manual map roof drawing`. Diff: `git diff 43297ecf...9efd14fc`. All source locations below refer to this pin.

**[P2] A newer buffer strands an uncertain journal write.** `apps/planner/src/data/useMapRoofDraft.ts:137–147,172–183,210–217,323–325`. [Incremental SPEC:15](../SPEC.md) requires: “Unknown write acknowledgement is retryable with exact bytes.” After A commits but its acknowledgement fails, `target.body` remains the older acknowledged body. Accepting B replaces `latest`, and the chain discards A's rejection without retaining an exact retry intent. Both B's queued write and public Retry then send B against that older body, conflicting with durable A. The public retry never settles A first.

The [executed probe](probe-unknown-ack.mjs), using real React, the hook, domain and journal with fake IndexedDB and one injected lost acknowledgement, reproduced **2 open points / 1 durable point**, with `storageFailed` still true after Retry. [Observed writes](unknown-ack.json): 0 acknowledged → 1 committed/unknown → 2 conflict → 2 conflict. Retain exact uncertain `{previous,next}` bytes; settle them before advancing to B. Preserve CAS refusal for genuinely competing tab versions and retain the newer raw buffer. The owner acknowledged this finding and plans a separate fix; this pin remains affected.

No additional confirmed Spec defect or scope creep was found in the inspected collection/resume, typed fields/fixed height reference, common grouped writer/history, owner/project fencing, prepared-result validation/retirement, geometry gate, source declarations, renderer disposal and lazy reentry. Existing-ring/hole/obstacle UI remains outside this explicitly new-roof increment ([SPEC:24](../SPEC.md)).

[Snapshot evidence](snapshot-evidence.json) records inspection of the 41-file diff, all 114 source and 7 emitted-build manifest digests, installed API versions, and all 44 final formal-German messages in the compiled MO. The reported 211-test/build/type/format suite was supplied by the owner, not rerun wholesale here. The independent fault probe checks pin equality for its application modules before execution.

[SPEC:22](../SPEC.md) requires native EN/DE at 1440/390 and recovery/application/history/save/provider evidence. The owner is performing that CUA separately. JSDOM, fake map ports, source and digest checks do not satisfy it. Later fixes require review against a new pin; the full goal remains active.

Spec findings: **1 P2**. Source conformance needs the uncertain-write repair; native acceptance remains separate.
