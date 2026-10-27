# Weather recovery and release quiescence checkpoint

Source: `c1ddef08c34075f1667972a62a95e3a0d2f55a6d`.
Base: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664`.
This is a backend checkpoint within the active complete unified-workbench goal.
It does not accept the unfinished customer workflow or install the new runtime.

## Implemented boundary

- Private trusted-team admission queues acknowledge, observe, capture and stop
  operations in the existing durable leased queue. Explicit storage binding is
  checked before opening a CLI target, keys replay the original receipt, and
  only one pending reconciliation exists per original run. Admission performs
  no provider request and exposes no new customer RPC.
- The managed worker executes maintenance even with new acquisition disabled.
  Known-run operations share the acquisition/cleanup protocol, have no Actor
  start method and retain bounded original-policy execution. A supplied run ID
  must match the pinned build and exact safe nonce-bearing INPUT.
- Successful acknowledgement retains both exact received effective INPUT bytes
  and the server-owned submitted input as output dependencies, including for
  failed/aborted remote runs that cannot supply a weather capture. Backup and
  restore verify these references independently of subsequent source capture.
- Recovery cannot publish a source asset or the original evaluation result,
  overwrite project inputs, or turn cancellation into success. Explicit resume
  requeues the original failed evaluation only with matching execution, a known
  provider run, remaining original attempts and the original elapsed deadline;
  a complete retained capture is required after that deadline.
- Core schema 4 adds reconciliation and active-operation uniqueness. Nonempty
  old schemas/archives retain parent/child queue records, leases, attempts,
  routing and receipts under the existing transactional migration mechanism.
- Release status checks all local pending job kinds and issued remote states
  in one database snapshot. Unknown starts and ABORTING remain unresolved.
  Missing/corrupt evidence fails closed. Legacy local draining verifies its
  configured store read-only, without creating or migrating it.

## Exact verification

`engine-commands.json` pins every final command to the source above. All four
commands passed: Ruff lint, format (**165 files**), strict mypy (**127 source
files**), and the complete engine suite (**816 passed, zero failures, errors or
skips**). The JUnit file and stdout are retained independently.

These are real SQLite/CAS/queue tests. They cover late acknowledgement, exact
safe INPUT retention for FAILED/ABORTED runs, nonce rejection, queue uniqueness,
actual lease expiry and replacement immediately before abort, finite persisted
recovery deadlines, unchanged producer attempts/runtime, capture/stop authority,
private CLI target binding, nonempty migration/rollback/archive restoration,
backup refusal for missing referenced bytes, remote-aware drain, and an actual
independent worker-host process with acquisition disabled. Provider responses
are simulated. This increment starts **zero external Actors** and makes no new
external research or weather acquisition claim.

`local-commands.json` records **92 unit passes**, local lint, format of source
plus the changed test (**18 files**) and mypy (**17 source files**) at
`704c4fddbe2e4de068f1d9f7fe9fd0ad3f16f914`. Both changed local files are byte
identical at the final pin; `source-scope-audit.json` records their hashes.
Those checks were not rerun or relabelled as a new full local-stack acceptance.

Historical outcomes retain their original pins and verdicts:

- `initial-engine-checks/`: 812 passes and one failure. Journal reads preceded
  an already-known revocation; `dc613c36` corrected the ordering.
- `pre-stop-fix-checks/`: 813 passes at `dc613c36`; the separate reviewed abort
  entry gap was still open. `0969e006` added the fresh fence and actual lease
  replacement regression.
- `pre-input-evidence-fix-checks/`: 814 passes at `0969e006`. The independent
  Spec review subsequently identified missing successful-ack INPUT dependencies;
  `c1ddef08` corrected them and added two terminal-run archive regressions.
- `initial-local-broad-checks/`: 92 passes, 26 skips, 19 setup errors. The direct
  broad invocation reached PHP 8.5 instead of the stack's required PHP 8.3;
  full-stack fixtures failed during setup. Its format diagnostic also found
  one unchanged baseline integration file. Neither diagnostic is green native
  acceptance; the baseline comparison and raw failures remain retained.

Independent full-diff Standards and Spec outcomes are recorded separately in
`REVIEWS.md`; the initial reports remain unchanged alongside their closures.

## Actual old-runtime recovery and preservation

Readback found the previously recorded worker PID 27398 and group leader 27394
absent. Its stale ready/PID files did not establish liveness. The cause of that
exit is not established. The existing HTTP engine, Genie and WordPress remained
listening at 9348, 9349 and 9347 respectively.

The live database was schema 2, with no weather-acquisition table or pending
jobs. Starting the current mutable schema-4 source against it was avoided.
Instead, the existing immutable CAS source/lock bundle was hash verified and
reconstructed into one bounded **689,144-byte** carrier. The existing Python
3.12.15 interpreter reproduced the exact old runtime, execution and storage
identities before worker launch. Only a package marker outside the captured
planning file set was added to seal imports to that carrier.

The restored worker is PID **71736**, generation
`4c0db985f9b248b08bf798cf043d254a`; its actual readiness was read back. Runtime
`9b66656acb26b65b88b09a44b8508a42094059af64b49e7038eedef0d92a10a1`,
execution `dfe60fc2089c920a945bb269da56dcb9debe6ccd5f6e9e7e70b46f6c08f55116`
and storage binding remained the same. **Process identity changed.** No new
weather runtime or schema migration was installed.

Every row of all live tables remained identical before and after restoration:
SHA-256 `b74d9b5e657e3180fc0182233bd1138e7a90f98fee47b3d62e1e9af4e5176295`,
165 projects, 228 revisions, and unchanged runtime/worker policies. The protected
roof project `82a84c56e50c4efb8497d1bfbe106bd1` remains revision 14 with input
SHA-256 `8a6394917a9a9e6b91db4bfc73c0299dcedd2c51619144a5beffa1664f010288`.
The before/preflight/restored/preservation JSON files retain the readbacks.

No new instance, worktree or full backup was created. There was no earlier
carrier to reclaim. `legacy-carrier-retention.json` records its sole purpose,
owner, exact path, review deadline (**2026-10-25 08:39:46 UTC**) and deletion
condition after the paired upgrade has no remaining process reference. The
original CAS bundle remains the unique immutable reconstruction source. Free
space at preservation readback was 903,044,235,264 bytes; no cleanup saving is
claimed. Credentials are absent from the changed/evidence scan, and engine/local
source has zero old custom-code identifier matches under the documented scan.

## Remaining same-goal acceptance

Native source/model/acquisition/progress/selection/recovery controls, correct
private credential injection for the managed process, EN/DE at 1440/390 and the
paired code/database install/rollback are still required. Actual installation
must quiesce every writer, reconcile remote uncertainty and verify the matching
recovery pair; this checkpoint is not an atomic deployment permission.

Detailed physical/electrical engineering, actual equipment compatibility and
country coverage, full bill of materials/report/PDF, site entries and Genie/Woo/
Solution draft/inquiry consumers, migration, review environment and production
readback remain within the same complete goal. Product identity remains at the
whole-system level; unaccepted capabilities are not advertised as available.
