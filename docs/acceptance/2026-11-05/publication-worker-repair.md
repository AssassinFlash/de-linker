# Ordinary publication worker repair 2026-11-05 (broken poll → healthy schedule)

Executor: main session. Found while verifying the BAT-C association's index
rebuild: the ordinary publication worker had been failing every poll.

## Defect

`launchd com.linker.knowledge-publication` (15-min ordinary poll) exited 1 on
every run: `ImportError: cannot import name 'MIN_WRAPPED_STEM' from
'linker_genie.table_projection'`. The worker's own `index/` code came from
release `8c9e6d809eec`, but `linker_genie` resolved through the shared
interpreter's `.pth` to `releases/1418dc26e14c/src`, whose
`table_projection.py` predates that symbol. Cross-release source mismatch:
Woo changes never rebuilt the knowledge index on the ordinary schedule.

## Fix and verification

1. Ran the same worker with the self-consistent current source
   (`releases/06e2b8549a93`, main `06e2b854…`, has `MIN_WRAPPED_STEM`) and an
   explicit `PYTHONPATH=<release>/src:<release>:<release>/ops`: full poll →
   new generation built, uploaded (224.9 MB delta) and ACKed. Index current
   `20261105T064354Z-336809000` includes the BAT-C manual for product 1955.
2. Permanent: the launchd plist now points WorkingDirectory and the worker
   entry at `releases/06e2b8549a93` and carries that PYTHONPATH.
   `bootout`+`bootstrap` applied; the run-at-load ordinary poll completed with
   **last exit code 0**.

## Resource note

- The 15-minute schedule is unchanged; the ordinary worker keeps its existing
  role (the paired operator does not manage it).
- The stale ordinary-worker state files from October are superseded by the
  verified new generation; no customer data touched.
