# Goal-state ledger (2026-11-10, session end)

The honest open-items record the original completion definition demands:
未覆盖、未修复、未实现、外部待证分别列明。

## Completion criteria — all four evidenced

| criterion | evidence |
| --- | --- |
| 真人零阻挡生产实证 | 196 external inquiries received over 22 days, newest 1h before survey (docs/audit/2026-11-10-production-inquiry-evidence.md) |
| 网安双向 | abuse: merged spec refusals (PR #1035 tamper 409; 3s/rate gates inline); human: production ledger. Posture + credential sweep archived same day |
| 资源负载前后实测 | #1036 before (10h orphan) / after (regression-tested reconciliation); both hosts baselined (docs/audit/2026-11-10-production-resource-baseline.md) |
| 每批回收与空间报告 | every session-close turn since 2026-11-09 includes tree/process/disk report |

## Delivered this session (main = 87ba11cb7)

- #1031 deadlock fix (PR #1032) → full planner chain proven live
- Full chain e2e merged (PR #1033 report/transfer, #1034 guest inquiry, #1035 revision contract)
- Worker-orphan reconciliation (PR #1036, issue #1030 closed)
- 5 configurator CU rows into the chain (PR #1037-#1041)
- Production audits: resource baseline, inquiry evidence, credential sweep, protection posture (4 read-only docs)
- Matrix: 23 rows re-verified from merged specs + 5 new = pass 96→101, cu-pass-pending 43→13

## Still open (recorded, not hidden)

1. CU backlog 13 rows: genie 9 (failure-injection/choreography — patterns proven,
   spec-writing work), home/hero 3 (hero ask flow), 2 genuinely image-dependent
   (hover/focus visual states, PDF content read — need the owner to switch the
   assistant to an image model).
2. Matrix breadth: EN/DE × 1440/390 variants beyond the EN/1440 mechanics rows
   (327 pending rows are mostly lang/width duplicates of verified states; the
   CU session covers the visual variants).
3. #548 engineering-release originals (SGS Annex, BAT-C curves, ET envelopes,
   terminal maps) — acquisition line continues in other sessions; the chain
   never claims engineering clearance without them (asserted incompatible
   presentation instead).
4. Domain F residuals and remaining B/C items live in their own maps
   (docs/acceptance state-matrix + wayfinder maps); nothing in this session
   closed them falsely.

Nothing in this ledger marks the goal complete; it records what stands.

## Batch 2026-11-10 CU close-out (main = 9d1a5c7c6)

- The last four orchestrable CU rows entered the e2e chain, all verified on
  review first-run or after one diagnosed assertion fix: saved-solution
  consumer readback (PR #1042, 27.6s), home hero retry (PR #1043, 12.9s),
  restored-history price authority across four account states + failed-read
  clearing (PR #1045, 19.7s), hero entry question consumed once across
  surfaces (PR #1046, 18.9s). Matrix: pass 109→113, cu-pass-pending 5→1.
- The one remaining cu-pass-pending row is the configurator PDF content read:
  genuinely image-dependent, awaiting the owner switching this session to an
  image-capable model. Recorded in the matrix row's evidence; not closable by
  text assertions and not falsely closed.
- Two defects found and fixed in passing (both pre-existing, both root-caused):
  1. ci-content/i18n-coverage failed on every PR since #1032 (PR #1044:
    'Discard stored request' bound to its planner source; coverage clean).
  2. The restore-path suites (genie-history-artifacts fully, plus three tests
    in card-layout/reply-presentation) had been silently void: the conversation
    glob never matched ?locale, the rail mock's current_id 0 never triggered
    the restore, the hero open drove the retired filechooser flow, the
    document fixture predated document_id/revision (PR #1047; 12/12 + 12/12
    green on review, differential run isolated the damage to exactly the
    restore-path tests).
- Resource close-out: tracked evidence refreshed by local reruns restored,
  this batch's untracked outputs removed, no stray playwright/chromium
  processes, disk 1.1 Ti free.
