# Independent full-diff review

Base `4f722c2636a61861c74e1a39b58350c0c218af3d`.
Initial full head `eb59835616ecc12b2cae88642d371d655593f30a`.
Repaired full source head `36f9535f07ff8ad6b0e9066d7eddfde647c9f450`.
CI-only follow-up `066b37357d4a3f558b662b8a863ae774cb46c0a6`.
Two independent read-only agents under the code-review skill reviewed each axis.

## Standards

Initial: one P1. A wpdb reconnect could drop the connection-owned mutex between
journal read and UPDATE, allowing a stale whole-journal write to erase a peer's
reservation. Existing native conversation code demonstrated the mature failure
pattern. Repair: lock owner and binary original-value CAS in the UPDATE itself,
require one affected row for changed state, and require lock ownership on readback.
A real KILL CONNECTION/second-connection winning reservation fixture verifies this.

Final full source: **PASS, zero remaining actionable findings**, no material
Fowler smell. Reviewer separately checked the CI-only delta and retained PASS.
New observation accounting, account-owner privacy association, bounded diagnostics,
EN/DE native UI and absence of secret/customer CSS/model-route drift were checked.

## Spec

Initial: three P2 findings: observe skipped advisory admission records; diagnostics
omitted current remaining/recovery and quota/retry categories/source version;
verification-only signed-in visits lacked native privacy association.

Repairs: non-blocking shadow receipts, safe current dimension diagnostics and actual
lease recovery time, bounded UTC daily categories with source version, and atomic
account-owner association without an additional account quota. Real fixtures cover
each. Final full source: **PASS, zero remaining concrete Spec findings**. New
EN/DE text was also reviewed for privacy, false receipt/coverage claims and usable
failure/retry distinctions. Source review does not substitute for UI or production
verification. The final CI-only inclusion has no behavior or scope expansion.

No finding was deferred to another ticket. Planned native consumer integration in
#520/#521 is not falsely described as already delivered by the helper module.
