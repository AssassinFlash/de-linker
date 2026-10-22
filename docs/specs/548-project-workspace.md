# Unified planner: project and durable execution contract

Date: 2026-10-22. Scope of this implementation increment: the private project
authority and durable execution boundary described below. The full delivery
continues under map #548 and `docs/acceptance/2026-10-22/548/EXECUTION.md`.
This document does not narrow the residential/commercial/Europe or whole-site
goal. Numerical models, HTTP identity adapters, UI and consumers are separate
subsequent increments of that same active delivery.

## Required behaviour

1. Verified actors own projects. Every project, revision and run read and
   every command checks ownership. Missing and foreign-owned IDs give the
   same error. A verified team subject may read a named customer's project;
   clients never choose the actor. Lists contain the caller's own projects.
2. Creating a project commits revision 1 and its finite canonical JSON bytes.
   Each edit uses `expected_revision`, creates an immutable next revision and
   atomically advances the project head. An old browser cannot overwrite a
   newer revision. Historical reads retain the original input/hash.
3. Create, edit and evaluation commands require idempotency keys. A lost
   acknowledgement/retry returns the same immutable reference; reusing that
   key for different command data conflicts. Receipt and state commit together.
   Parallel retries must not create additional projects, revisions or jobs.
4. Evaluation freezes its revision, input hash, code/model versions, named
   dependency asset hashes and parameters. Required pinned bytes must exist
   and be hash-verified. It only queues work; it performs no numerical work
   under the write lock. A run remains tied to its original revision after an
   edit and is explicitly historical, with no recalculation during reads.
5. Workers claim one eligible job with an expiring lease, attempt counter and
   unpredictable fencing token. Concurrent claims cannot own the same attempt.
   Expired, replaced, failed or cancelled attempts cannot renew or publish.
   A still-owned attempt may extend its lease. Attempt limits and timing are
   explicit caller/operator policy, not hidden scientific defaults.
6. Result publication and success commit atomically. A repeated completion
   from the same attempt and same bytes is safe; conflicting bytes or an old
   attempt cannot replace the result. Frozen task execution state is separate
   from feasibility/evidence in the result and current/historical relation.
7. Known transient failures may retry after a persisted delay, within the
   attempt budget. Named permanent errors do not retry. Unknown exceptions
   become `execution_failed`, with private logs and no raw customer exception
   disclosure. A process crash leaves reclaimable work; exhaustion becomes a
   named terminal failure. A damaged queue request cannot block healthy work.
8. The explicit worker uses registered handlers and a lease heartbeat. It
   never ties computation to the lifetime of a PHP or HTTP request. Losing
   heartbeat revokes publication. Long loops can cooperate through checkpoints;
   final publication still checks the durable lease and cancellation state.
9. Guest-to-account claiming requires both verified subjects, transfers the
   project atomically with a receipt, preserves history and revokes the former
   guest's access. A different account cannot claim by project ID alone.
10. Input, manifests, receipts, errors and results are private immutable bytes.
    Publication precedes DB references; an interrupted write may leave unused
    bytes, not acknowledged broken references. Missing/tampered bytes are
    `version_unavailable`, not zero data or an implicit latest dependency.
11. An online backup must contain committed WAL and all referenced bytes,
    verify hashes, SQLite integrity and foreign keys, and restore independently.
    Concurrent additions must not invalidate it. Damaged backups are rejected
    before publishing a restored workspace. Existing stores/backups are never
    overwritten. Backup/files/directories are private to the service account.

## Verification boundary

Use real temporary SQLite/files and separate connections for concurrent
claims/edits/retries. Inject only time and clearly marked non-physical fixture
handlers. Verify ownership, history, publication fencing, restart, delayed
retry, cancellation, corruption, failed commits, online backup and restore.
These tests cannot be cited as verification of PV, dispatch, compatibility,
reports or production identity. The private module is not yet an exposed API.
