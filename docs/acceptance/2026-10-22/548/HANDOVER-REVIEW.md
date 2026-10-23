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
