# Independent Spec review

Reviewer: `/root/pv_reference_spec_cbadc619`.
Complete nine-file diff:
`27386b7ecc50a3e9acea54392cb3141dee0d8b82...a1eaecfc46290743c67a50661e498f8a2de5dc03`.
Result: zero findings against the current foundation checkpoint.

The typed plan fixes the exercised Actor/build, official request, explicit
resources and non-leap reconstruction. Journal creation requires the exact
plan hash pinned by the immutable run. Intent and POST-permit writes use the
existing active-lease fence; the one consumed permit persists across lease
replacement and cannot be renewed by replaying a stale `may_start` value.
Its deadline remains persistent.

Acknowledgement/progress/abort replies preserve provider identity/storage,
retain the first acknowledgement and prevent late nonterminal observations
from erasing terminal facts. These evidence writes publish no task result or
owned asset. Capture uses the existing strict TMY interpreter, binds the
request/interpretation and succeeded run, and freezes original bytes/evidence.
Conflicting captures fail. Owned projection follows transfer. Archive checks
retain journal and flattened child references and accept older snapshots.

The tests exercise these actual foundation boundaries. Effective-INPUT/dataset
verification, real HTTP acquisition, orchestration/recovery/abort execution,
registered execution, native and live acceptance remain expressly unimplemented
stages of the same goal, and are not accepted by this review.

Read-only inspection: no edits, live actions, research or duplicate test run.
