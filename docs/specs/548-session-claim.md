# Verified login: whole-guest ownership transfer

Date: 2026-10-23. This increment closes the engine-side identity lifecycle
required by the unified workbench. It does not establish WordPress cookie,
nonce/Origin or login-hook verification; those remain the native gateway's
responsibility and must pass before browser mounting.

## Required behaviour

1. A trusted gateway proves both the former guest and the current account.
   A browser-selected guest, project ID or owner cannot authorise a transfer.
   This private RPC is not forwarded by the browser-facing route whitelist.
2. One transaction transfers every project still owned by that guest to the
   verified user, preserves all revisions/assets/jobs/results and records
   ownership history. It also permanently retires that guest principal.
   A session with zero projects is retired too.
3. Retirement and creation are serialised by the same write lock. A request
   admitted before login may publish unused immutable bytes, but cannot
   acknowledge a newly guest-owned project after the transfer. A project
   committed before the transfer is included. Retired guests cannot read,
   list, create, revise, enqueue, cancel or access private assets/results.
4. A durable receipt and idempotency record commit with the transfer.
   Re-delivery to the same user returns the original count/confirmation,
   including delivery with a new event key; it never transfers later user
   projects. A different user conflicts. Failed publication rolls everything
   back, without a partly transferred or partly retired session.
5. The private `/identity/claim-session` command accepts only schema version
   and event key. The authenticated current principal must be a user; the
   previous guest comes from one validated private gateway header. Missing,
   duplicate or invalid assertions fail closed; stale ASGI scope cannot
   substitute for the header. No raw cookie or service credential is returned.
6. Persistence schema 2 adds a guest-closure ledger. Schema 1 upgrades under
   an exclusive write transaction; unknown versions are rejected. Existing
   project/asset/result bytes are unchanged. Readers built for schema 1 must
   reject schema 2 instead of reopening a retired guest through old code.
7. Online backups include closure receipts as required byte dependencies.
   Verified schema-1 archives remain restorable and are upgraded in a private
   temporary directory before publication. The source archive stays unchanged.
   Restore/restart must preserve retirement and all transferred history.

## Integration and verification

WordPress must derive subjects from native verified sessions and the account,
record the login migration durably and retry the authenticated hop. Its hook,
outbox and race behaviour are separate acceptance paths; the engine's `Actor`
is not browser authentication. Partial per-project claiming remains an
internal legacy interface and is not exposed as the unified login protocol.

Use actual SQLite/CAS, concurrent connections, controlled interleavings and
fault injection: both create/claim orders, competing accounts, lost responses,
receipt corruption, failed commits, restart and archive restore. Use real ASGI
for both assertions, missing/duplicate headers, scope injection and denial of
the old guest. No numerical, SKU, country or user-interface capability follows
from these lifecycle tests.
