# Independent Standards review

Reviewer: `/root/managed_worker_standards`.
Exact complete diff:
`27386b7ecc50a3e9acea54392cb3141dee0d8b82...a1eaecfc46290743c67a50661e498f8a2de5dc03`.
Documented violations: zero. Actionable Fowler findings: zero.

The reviewer inspected every hunk in all nine files, the foundation checkpoint,
relevant lease/manifest/archive code and every new test. `begin` verifies the
exact frozen plan; creation and permit consumption share `Jobs.require_active`
inside the write transaction. Serialized consumption survives reopen/replacement.
Late provider facts require the private issued intent and preserve identity,
first acknowledgement and terminal observations. They grant no publication lease
and publish no successful task or owned asset.

The plan derives the official URL and pinned Actor/build. Selected provider
fields exclude account, billing and temporary access data. Explicit typed
operational limits retain source comments. The complete-TMY interpreter remains
the capture authority. Capture references are immutable and flattened for archive
checks; old core-v2 snapshots remain readable. Distinct responsibilities, grouped
intent identity and a shared lease fence avoid duplicate authority.

Public-seam tests meaningfully cover concurrency, replacement/cancellation,
plan/nonce mismatch, deadlines, provider identity conflicts, immutable capture,
transfer, missing child evidence and actual backup/restore. Added source contains
no specified legacy identifiers or TODO/FIXME markers.

Read-only review: no test rerun, network request, runtime/native or production
action. This accepts only the foundation; remaining integration stays in scope.
