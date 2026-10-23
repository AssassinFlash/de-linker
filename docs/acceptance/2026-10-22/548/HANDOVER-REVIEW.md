# Native recovery handover increment

2026-10-23. Implements [the handover contract](../../../specs/548-native-recovery-handover.md).
Fixed-source independent axes and final browser paths remain separate gates.
Path A and the whole delivery remain active.

Native CUA used an isolated synthetic customer account and the real site login,
without a production account, mail or password disclosure. The existing Oslo
project/revision7 transferred into Account workspace. A pre-login unsaved note
was restored only after the owned project read; the user could compare and keep
it, then save revision8. A refresh exposed stale old-scope edits reappearing as
unsaved although their effective inputs already matched revision8. That defect
was corrected: redundant known edits no longer shadow the saved server version;
an uncertain pending intent remains reviewable, not silently acknowledged.

New native recovery grants are account-bound and exposed through same-origin,
nonce-protected, ordered pages. The original guest query scope is captured only
in Woo's verified migration event, signed through insertion failures and granted
only after complete engine claim/retirement. Legacy tickets/outboxes remain
deliverable without inventing a missing scope. Account session scopes are also
registered under the authenticated native account. Exact original browser
scope/body/key survive explicit retry and cleanup; aggregate recovery limits
raise visible errors without truncation or eviction. Native quota lookup already
treats a prior actor's unmatched fingerprint as an unknown local receipt; the
permanent owned engine receipt is recovered before any new charge/dispatch.

Engine permanent replay now admits receipts from guests retired to this exact
account for supported project/asset/run commands. Current ownership remains
mandatory. Same-key ambiguity and changed commands conflict rather than choosing
a resource or overwriting history. No guest is revived, old receipt owner changed
or browser Actor accepted.

Implementer verification: 330 planning tests pass14.91s, including real HTTP CSV
and create receipts after claim, commit-first/claim-first, collisions, isolation,
run/assets and verified archive restore. Native p548 HTTP tests15 pass43.48s,
including outage/insert recovery, guest/account transitions, original creation
receipt, account switching and67-scope pagination. PHP289/2357, WPCS, PHPStan512MiB,
mypy67 modules and ruff pass. Current Node31 and React36 cover exact prior-scope
intents, no automatic send, late native admission, pagination/refusal, bounded
recovery, aggregate limits and stale/uncertain drafts. Native render/unknown-ack
paths and independent fixed-source review will be added after actual execution.

The only new customer message passed independent adversarial copy review and
parent selection in [HANDOVER-COPY.md](HANDOVER-COPY.md). It does not promise a
new local write succeeded. New creation waits on failed discovery; available
project saves are unaffected. Modern React/Vite build is187 modules,
484.32kB/gzip142.56kB. No formal route cutover or production deployment occurred.

## Rejected fixed source ffb8489a

Both independent axes rejected ffb8489a for the known current-scope recovery
defect: a previous recovery already persisted into the new scope still used the
old baseline and falsely became unsaved. Standards separately reproduced a
native401 dead end: recovery lookup withdrew admission, while Try again only
refetched and never obtained a new native session. Its original probe is kept
in [handover-probes](handover-probes/recovery-auth.original.mjs). Independent
330 planning/31 Node/36 DOM and the original live-admission/focus probes otherwise
passed. Spec additionally challenged two retired guests' colliding same-body
receipts,12 concurrent create/claim races and scope refresh during creation or
open/awaiting CSV work. Standards verified moved-owner receipts remain NotFound.
None of those checks was represented as native CUA by the reviewers.

The correction ignores only known nonpending effective inputs already saved at
the current server revision, in both local and previous-scope paths. Clean old
history is not offered as new edits. Five DOM cases cover current/prior,
pending/known, and a clean previous revision. Native401/403 now trigger one
bounded recheck; persistent refusal waits for explicit native retry. Successful
native confirmation refreshes the index, recovery grants and failed active
reads, while successful opening snapshots stay pinned. The former probe's
required transient error may now disappear through automatic recovery before
its retry click; its final outcome is tested more strongly by transient,
persistent401 and ordinary503 real-client DOM cases. No mutation is replayed.

An additional real native fault was deliberately injected after quota dispatch,
before engine create. It reproduced zero engine projects followed by login and
409 operation_changed. The raw UUID had been a global native-ledger key across
different principal/quota bindings. Transport IDs now use an opaque native
principal+binding+exact-key namespace in Ledger's accepted UUID shape; the
engine's business key/body remain unchanged. A committed engine receipt still
bypasses new admission. An uncommitted dispatch retains its resource charge and
an explicitly retried new native context is separately admitted, without
rewriting/refunding old receipts or reviving the guest. The native contract was
clarified with this executable evidence. Ledger fixtures discover the actual
inserted transport ID; they do not recompute the implementation's hash.

The16 native cases pass after this correction. An added owner/key namespace
case confirmed distinct owners are independently metered, and native WordPress
rejects uppercase UUID input before new admission; its initial expectation of
200 was corrected to that observed400 without altering product validation.
The case passes in isolation and the other16 are unchanged. Current31 Node and
42 React cases pass;187-module build is484.76kB/gzip142.69kB. WPCS/PHPStan pass.
Native refresh now shows the original Oslo project Saved·revision8, no stale
conflict, with its source data retained. Final fixed-source reviews and remaining
native unknown-ack paths are still required before this increment is accepted.

## Rejected fixed source 7d9af42c

Spec passed the complete dee1aaac→7d9af42c increment; Standards found one P2
legacy-journal compatibility defect. Its unchanged independent real-class PHP
probe showed a matching raw-UUID dispatched receipt was ignored: absent engine
receipt caused used1→2/receipts1→2, and confirmed engine replay left the old
receipt dispatched. Both axes independently passed330 planning,31 Node and42
React cases; this did not cover the missing legacy representation.

The correction adds an atomic context lookup to the native Ledger without
changing its existing lookup/reserve/transition contracts. Send and confirmed
acknowledgement share legacy-ID resolution. Matching purpose/binding/intent
reuses the original journal entry, including a full bucket; different binding
or purpose is unknown. Changed input in the same legacy context conflicts.
Old records cannot independently identify a different guest principal with
that same binding, so mismatched fingerprints conservatively conflict before
admission. An engine-confirmed permanent result retains precedence and never
completes an unrelated legacy entry. No receipt migration/refund/key rewrite
is performed.

The unchanged independent probe now shows used1→1/receipts1→1 and completed old
status in both absent and confirmed branches; mutation calls are respectively
one and zero. Actual native HTTP now passes19 cases82.64s, including both legacy
representations, unchanged buckets/debits/count, exact successful replay and a
changed-body409 before the absent receipt commits. The native shared-Ledger
database fixture additionally covers a full bucket, purpose/binding isolation
and conflict:13 tests109 assertions2.888s. Both plugins' WPCS and PHPStan pass.
The unchanged [independent probe](handover-probes/review-legacy-journal.original.php)
can be copied into a temporary directory with `plugins` symlinked to the fixed
checkout, then run with PHP assertions enabled, with/without `replayed` argument.
Final independent fixed-source review and remaining native CUA
unknown-ack paths are still pending.

## Rejected fixed source 07d616af

Standards passed the full increment, including both unchanged legacy probes,
full-bucket reuse and six context/confirmed-result precedence challenges. Spec
found one P2: an unused legacy reservation could expire before dispatch. Its
real Ledger clock-injected probe showed lookup correctly refunded it, but ID
resolution still chose the terminal raw entry and returned409 indefinitely.
The same latent boundary existed for a new-style attempt interrupted between
reserve and dispatch, so the correction covers both representations.

Only matched, definitely unused expired/cancelled entries can acquire stable
successors. The original terminal receipt remains unchanged, while concurrent
explicit retries select the same successor before atomic admission. No random
or time-based retry key is generated, the engine body/key remain frozen, and
dispatched/unresolved receipts remain charged and reusable. Erasure tombstones
cannot restart admission. A bounded traversal refuses temporarily rather than
discarding the original intent. The unchanged Spec expired probe now gives200,
mutation1, used1→1, receipts1→2 and the original expired receipt unchanged;
confirmed mismatch/binding probes retain200 with no mutation or extra charge.
The [unchanged expired probe](handover-probes/probe-legacy-edges.original.php)
uses the same temporary-directory launcher as the earlier probe, with `expired`.
Native HTTP legacy/new-style × expired/cancelled cases and the two prior legacy
paths pass6/17 deselected36.14s. They prove native refund+replacement consumes
one attempt, preserves the complete original terminal record and exact business
replay, and does not create a second project. The shared native database suite
passes13 tests112 assertions1.989s, including erasure refusal. WPCS, PHPStan in
both plugins and ruff pass. Unchanged browser/engine source retains previous
evidence. Final independent review and remaining native CUA paths are pending.

## Rejected fixed source c484d444

Both independent axes reproduced one remaining P2:32 unused terminal attempts
could exhaust local traversal and incorrectly turn an already-confirmed engine
result into receipt_persistence503. Spec also proved five-layer expiry/cancel
continuation, erasure refusal/confirmed precedence, and actual two-process
successor convergence under a barrier between lookup and atomic reservation:
one new admission, browser/site each used1, old records unchanged. Two transport
calls can still occur with the same business intent; engine idempotency, not
network-call counting, guarantees one resource.

The correction distinguishes the local traversal bound from a journal storage
failure in confirmed acknowledgement. Only capacity exhaustion returns the
already-confirmed result without inventing a settlement; actual persistence
failures remain explicit. The [unchanged chain probe](handover-probes/probe-attempt-chain.original.php)
now proves32-layer confirmed200/no mutation/no charge/unchanged records, while
absent still503. Five-layer expired/cancelled create one new attempt; erased
absent refuses and confirmed succeeds without changing the tombstone. All six
outcomes were asserted. WPCS and PHPStan pass. Final fixed-source axes follow.
