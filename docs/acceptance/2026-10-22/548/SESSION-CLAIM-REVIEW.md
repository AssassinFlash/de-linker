# Whole-guest claim: component acceptance

Date: 2026-10-23. Final fixed implementation:
`726557ac040450c01c98b77eb91288e8583c6a73`;
component base: `bc68b112cc7d1cb2a12ac8e539fb012dc2938b46`.
Contract: `docs/specs/548-session-claim.md`.

## Standards

Independent fixed archives passed with no documented-standard violations or
actionable baseline smells. The final review verified complete trigger DDL
while the migration transaction/write lock remained held, rollback on a later
trigger failure, unknown-version checks and the original old-process attack.
Its targeted guest/workspace/archive suite passed 28 cases.

## Spec

The initial candidate's application-only retirement had one serious gap: an
already-running schema-1 process could create a new guest-owned project after
the new service completed login transfer. This was reproduced independently
by both reviewers and fixed in the same batch with database owner guards,
complete-transfer enforcement and current-connection version checks.

The final reviewer kept an actual old-code process and an old SQLite
connection alive through migration. Late create and owner restoration were
rejected; no guest project or late idempotency receipt committed. Both
connection/transaction race windows rejected unknown versions. Real old
schema-1 archives upgraded privately; syntax/incomplete-DDL failures kept
source hashes unchanged, rolled back all new objects and published no restore.
The final targeted suites passed 30 cases, with no remaining spec defect.

Earlier fixed-archive evidence also verified independent competing processes,
complete eight-project transfer to exactly one account, same-user redelivery,
actual deferred-foreign-key COMMIT failure rollback, forged/stale assertions,
schema/body authority rejection, old-guest denial and restored retirement.

## Shared verification and boundary

At final source `726557ac`, root ran all engine tests: **395 passed, 29.03 s**.
Ruff and mypy passed (56 planning source files). This total includes other
engine tests; it is not 395 login/browser checks.

The private protocol trusts two server-verified assertions. Native Woo cookie
proof, registration/login hooks, durable WordPress migration outbox, Origin/
nonce checks, browser storage isolation and deployment process draining still
require actual integration and acceptance in this same goal. This component
does not itself implement those paths or establish equipment/country release.
