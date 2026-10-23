# Native identity and browser recovery handover

2026-10-23. This implements application contract7/14 and path A. Native CUA
already proved saved guest projects transfer to the signed-in account and a
known owned project's unsaved draft can be compared/restored. Unknown creation
and upload intents need the following additional continuity; no mutation is
automatically resubmitted on login.

1. Query scopes remain session-specific, and native identity is rechecked before
   every read/write. Browser recovery records do not grant project access.
2. A private WP recovery-scope registry records only a native authenticated
   account's own query scope, or the exact guest query scope captured by Woo's
   verified guest→user event. The latter is registered only after the engine
   confirms complete claim and guest retirement. The outbox is retained if the
   registry write/readback fails. The signed transition ticket carries the
   captured scope through failed outbox insertion; old v1 tickets/events remain
   deliverable, without inventing a scope absent from their native evidence.
3. The native same-origin/nonce-protected recovery/scopes read returns only the
   current account's grants in sorted, bounded pages. Guests receive no previous
   identity's scope. Cursor strings and page size are transport policy, not
   authorization. All pages are consumed without silent truncation or eviction.
4. Browser creation/import records keep original scope, exact bytes and key.
   Only current scope and verified registry scopes may be listed. A changed
   identity hides previous data until current native grants and, for uploads,
   the current owner's project read succeed. Retry requires an explicit action
   and uses the original request. Exact conditional cleanup targets the original
   record; other scopes/parallel requests survive.
5. Permanent receipts survive guest claim. For supported project/asset/run
   command scopes, the verified account can replay its own receipt or a receipt
   from a guest retired to that account. Receipt lookup never moves a project,
   revives a guest or relaxes current project ownership. An ambiguous key or a
   different command conflicts; no receipt is overwritten. Existing native
   quota acknowledgement must not prevent an engine-confirmed recovered result.
   The original business key stays unchanged; the native resource journal is
   separately scoped to its principal/quota binding. A dispatched attempt with
   no engine receipt is not silently refunded; retry in a new native quota
   context admits that attempt, instead of colliding on a globally raw UUID.
6. Claim and mutations use the same DB transaction boundary. If a guest command
   committed before claim, retry returns its original resource/revision. If the
   guest never committed, retirement prevents a delayed guest write and the
   explicitly retried account intent can commit once. Same-account session
   renewal likewise reuses the permanent receipt, not a new request/key.
7. Recovery discovery failure preserves records and reports inability to check
   previous requests. It does not assert the queue is empty or deny an otherwise
   available server save. Identity changes fence async discovery/callbacks;
   native grants are not cached across identities. No account, test mail or
   production write is implied by this implementation contract.

Verification: real guest→account/lost-ack fixtures for create/revise/import;
claim-first and commit-first interleavings; another account/guest cannot list or
replay the records; collision, migration, pagination, storage failure and delayed
identity checks; native UI login, explicit retry, saved revision and source
readback, logout isolation; independent Spec/Standards and EN/DE native states.
