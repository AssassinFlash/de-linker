# Current production and Genie integration — #533 / #563

## Source boundary

The live WordPress atomic manifest observed on 22 October 2026 was `20261022T122802818764Z-af41f307` (archived), source `af41f307091fb3a72246d12cf726223878139caf`. Main incorporates that release at `340a11a9`. Its existing public-intake safeguards derive from `003cedd3`; that protection revision is not the whole-site revision.

The earlier WordPress deployment guard expected the old manifest and stopped before `steps.deploy` or any production write. Publishing the isolated Genie source would have replaced newer visual/contact work. This integration instead merges reviewed Genie PR #566 (`033b74a6`) onto main `340a11a9`, producing source merge `16a8052f` without conflicts or manual runtime edits.

[Source composition](source-composition.json) compares both parents against their shared base `1f054757`. The 33 runtime/test files changed on main and the 32 changed in the Genie branch do not overlap. All 65 final files match their corresponding parent exactly. The deployment-tool delta is empty. This proves source preservation, not combined execution, visual parity, CI or production acceptance.

## Existing execution evidence

The [Genie acceptance](../563/README.md) records the independent full-diff Spec and Standards passes at functional head `252f331b`, all native/unit/static checks, and the final eight-cell built workspace/Hero × EN/DE × desktop/mobile matrix. Its native completion/recovery path uses local provider stubs; each Retry adds zero turn POSTs or provider calls. That earlier source/instance evidence does not become a combined-site or live result merely because this merge is conflict-free.

Genie backend source `252f331b` was atomically activated separately at 13:32 UTC on 22 October 2026. Readiness returned HTTP 200 after 2.099 seconds; engine, judge and TLS processes were unchanged. The previous release is retained for rollback. This backend health check made no paid model call or mail attempt. WordPress was still on the newer visual/contact release at the time this document was written.

## Publication contract

Combined CI, native relevant checks, local browser checks and independent review must precede WordPress publication. The two active website chats have explicit owner permission to coordinate versions and publication windows. The current atomic publisher stages to a shared directory; the chats must serialize publication and verify the latest manifest again immediately before writing. A changed manifest requires re-integration rather than bypassing the guard.

The normal deployment makes a fresh local database snapshot, retains the prior code release and requires native WindPress compilation and final readback. Rollback restores the preceding atomic WordPress release; the backend has its independent prior symlink. No schema migration or existing inquiry deletion is part of this integration. Administrator MFA enrollment, aggregate intake/mail capacity and public-registration capacity remain separate, unshipped work. No production test mail is authorized by this integration.
