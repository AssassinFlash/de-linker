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
