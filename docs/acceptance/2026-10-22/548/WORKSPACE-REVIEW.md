# Project authority: independent review and repairs

2026-10-22. Code-review skill, fixed diff `02c34e5...588f3256`.
This reviews the private workspace increment, not the full production planner.
Both reviewers used separate temporary SQLite/files; neither edited the tree.

## Standards

Two blocking findings were independently reproduced:

1. P1: an existing blob path returned before reconfirming directory fsync. A
   prior interrupted publication could therefore be acknowledged on retry
   without a durability barrier. This violated the immutable publication
   commitment in the ADR/specification.
2. P1: the team read exception in the shared ownership helper also allowed
   editing/evaluation/cancellation of another owner's project. The contract
   grants named-project reads, not customer write authority.

No additional documented-standard breach or blocking code smell was reported.
The reviewer checked the existing Python distribution/imports and old-code
identifiers; no old residential/commercial selection algorithm was imported.

## Spec

Two wrong implementations, no separate scope-creep finding:

1. P1: the same team read/write problem, violating “every command checks
   ownership” and “may read a named customer's project”.
2. P2: an invalid persisted request hash raised `InvalidInput` outside the
   queue's damaged-request handling, rolling back the claim repeatedly and
   blocking later healthy work. This violated “A damaged queue request cannot
   block healthy work.”

Both axes distinguish the subsequent HTTP/numerical/UI work explicitly
outside this increment from defects in current promised behaviour.

## Repairs and verification

The implementation now distinguishes reads from owned writes in every current
command; retries reconfirm both the CAS root/prefix directory entries, including
the existing-file path; damaged persisted hash syntax is quarantined as a named
terminal job failure and the queue continues. Relative backup paths are also
resolved correctly before SQLite read-only URI creation.

Four additional real-file/SQLite regression cases cover team writes, fsync
failure/retry and invalid request hashes. All 31 planning tests, strict mypy,
ruff lint and formatting pass locally. Both independent reviewers rechecked
fixed commit `7591075a779e98ea700dcf62de2aa1141c57bc68` and reported no remaining
blocking findings. Each independently reran all 31 tests and repeated the
original ownership/fsync/queue reproductions; relative backup/restore also
passed. Neither changed files, committed, or deployed.

Axis totals at initial review: Standards 2, Spec 2 (one shared cause). Worst
within Standards: durability/ownership P1; within Spec: ownership P1. No claim
of full application acceptance or production deployment follows from this.
