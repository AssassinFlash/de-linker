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

## Matrix write-back batch (main = 06b46f6e3)

- 17 language/width variants flipped to pass, each on a parameterized suite
  green on review this batch: card-actions 9 (product-add hover/retry/unverified
  x en:390/de:1440/de:390), failure-ownership 5 (service-error-retry 3,
  ordinary-draft-owner-isolation 2 - its de:1440 was already pass),
  parts-card 3. genie-parts' csv de:1440 strict-mode ambiguity fixed in the
  same commit (sentence stands in three places; anchored on the attachment
  status), suite 8/8 after the fix.
- Correction of that commit's message: it says 20 variants; the honest count
  is 17 (the linked-product variants are home-family rows covered by
  genie-hero, which was not run green this batch and stays pending).
- Not flipped without real coverage: the 90 planner-chain variants (single
  shape EN chains) and every other family whose suite has not run green in
  the row's shape. Pending after this batch: 310.

## Batch: shape coverage to every language and width (main after PR #1050)

- Four suites extended from their single EN/1440 row-shape to full en/de x
  1440/390, all verified green on review before merge: home-hero-retry and
  genie-history-authority (PR #1048, 24 tests), genie-hero's answer and
  linked-product tests (PR #1049, 4/4 - with the spec catching up to the
  shipped hero: planner-entry capsule excluded from the hide assertion,
  three-tier card grid, layout poll), genie-cross-surface-entry (PR #1050,
  all four shapes - phone shapes open the dock through the chip).
- Matrix: pass 142 -> 145, pending 295. Honest exclusions recorded: the 90
  planner-chain variants (single-shape EN chains, not flipped without real
  coverage), save-readback DE (its cart notice is an untranslated catalog
  string; customer-visible copy goes through the copy review line, not a
  freelance translation - the gap is this note), account-family variants
  (sibling evidence is production JSON audits of one shape).
- Operational lesson recorded: a tool-level background timeout does not kill
  the process tree - a zombie full genie-hero run starved the review Genie
  and produced a batch of 400s test timeouts; killed, diagnosed by service
  log (turns 200 OK but minutes-slow), and the shapes re-verified green on
  the quiet instance.

## Batch: project-brief in German (PR #1051)

- planner-brief-chain parameterized over en/de (13 tests, all green on
  review 51.7s); every German word from the shipped catalog, no new copy.
  Root-caused on the way: the direct-goto sites built the DE configurator
  URL without its /de prefix (a 404 - the single cause of the three first
  DE failures), then a doubled slash in the staged-URL regex.
- Matrix: pass 145 -> 181 (all 36 project-brief language/width variants),
  pending 259.
- Remaining planner variants: map-chain 33 and report-chain 39 need the
  same treatment (bigger label surface: 21 and 37 strings) - next batches.

## Batch: the roof map chain in German (PR #1052)

- planner-map-chain parameterized over en/de (8 tests green on review).
  Three root causes root-caused by EN/DE diff probes before fixing: German
  number fields take a decimal comma (dot decimals left lat/lng invalid and
  the workspace-switch guard blocked the whole chain), two German
  substring/label collisions, and a hydration wait before the first section
  navigation.
- Matrix: pass 181 -> 214 (all 33 roof language/width variants), pending 226.
- Remaining planner variant block: report-chain 39 rows (37-label surface -
  the biggest of the three), same method.

## Batch: the full planner chain in German (PR #1053)

- planner-report-chain parameterized over en/de: the complete customer
  chain (site -> roof -> strings -> profiles -> PVGIS -> PV -> equipment ->
  scenario -> report -> transfer -> Woo draft) drives the German configurator
  end to end; en and de both 5.2m green on review. Nine root causes fixed on
  the way, each verified against the live German DOM (the duplicated
  hardcoded fill that waits forever, four option labels, three English-only
  assertions, the Betrieb/Speicher substring collisions, the hidden-tab
  report select copy, the MPPT sprintf self-collision, the English-only
  confirmation segment). This closes the planner trilogy: brief-chain (#1051),
  map-chain (#1052), report-chain (#1053) all bilingual.
- Matrix: pass 214 -> 241, pending 199. The planner-variant block that was
  90 rows at the start of the day is fully retired where the chains cover it.
- Operational note recorded: the shared public-connection limiter must be
  reset between chain runs (3/hour shared across runs) - already a handover
  discipline, now hit in practice.
