# Full-matrix pass — results, coverage delta and remainder (2026-11-04)

Environment: isolated local snapshot instance `fullmatrix` (production snapshot
`20261104-1914`, loaded 19:18) + bounded read-only production checks.
All counts parsed from the matrix JSONs' top-level rows
(`docs/acceptance/2026-10-22/full-site/`), before = branch base `8c9e6d809`,
after = this branch's merge commit.

## Coverage delta (cumulative, after slice 2 same-day)

| Matrix | Column | Original | After slice 1 | After slice 2 |
| --- | --- | ---: | ---: | ---: |
| Page (708 rows) | interaction pending | 556 | 324 | **5** |
| | interaction partially-verified | 68 | 300 | **615** |
| | interaction not-applicable | 84 | 84 | **88** |
| | visual_review pending | 387 | 237 | **1** |
| | visual_review partially-verified | 236 | 382 | **609** |
| | visual_review partial-with-finding | 1 | 5 | **10** |
| | render pending | 4 | 4 | **0** |
| State (1,044 rows) | pending | 771 | 588 | **529** |
| | partially-verified | 235 | 418 | **477** |
| Template (31 rows) | pending | 29 | 1 | **1** (LC 30, empty content) |

Slice-2 specifics: the page sweep finished all 556 selected rows (547
basic-pass; 9 fails = 4× configurator no-H1 (F7, now also DE), 4× Trina
reference module 404 on snapshot AND production → rows moved to
not-applicable with the measured basis, 1× browser-crash row that makes no
claim). Role/submission passes contributed the registration chain, password
reset end-to-end, per-role account/price views, the draft chain, guest
inquiry to the native received endpoint with a valid key, contact success,
and the proforma status/document probe.

## Slice-1 coverage delta (kept for history)

| Matrix | Column | Before | After | Δ |
| --- | --- | ---: | ---: | ---: |
| Page (708 rows) | interaction pending | 556 | **324** | −232 |
| | interaction partially-verified | 68 | **300** | +232 |
| | visual_review pending | 387 | **237** | −150 |
| | visual_review partially-verified | 236 | **382** | +146 |
| | visual_review partial-with-finding | 1 | **5** | +4 |
| | render pending | 4 | 4 | 0 (crash row + configurator rows pending render upgrade) |
| State (1,044 rows) | pending | 771 | **588** | −183 |
| | partially-verified | 235 | **418** | +183 |
| Template (31 rows) | pending | 29 | **1** | −28 |
| | partially-verified | 2 | **30** | +28 |

Notes on the deltas:

- Every upgraded row carries the evidence path
  (`docs/acceptance/2026-11-04/full-matrix/evidence/*.json`), a scope note
  stating what the automated evidence does and does not prove, and — where
  applicable — `harness_notes` separating benign automation artifacts
  (correctly-disabled controls; clicks landing on the dismissible Genie
  floating prompt at auto-scroll positions) from real findings.
- Statuses stronger than the new evidence were never downgraded; no existing
  evidence was cleared. One crashed capture row (browser-context death) made
  no claim and stayed pending.
- The 4 new `partial-with-finding` page rows: 2 ×
  `/solution-configurator/` EN (no visible H1 at read — tool app renders its
  own headings; see DEFECTS.md F7 note) and 2 × EN legal pages at 390 (local
  CookieYes overflow artifact, DEFECTS.md F4; production measured clean).
- Template row 30 (`global-javascript-code`) is the single remaining pending
  template: empty post_content on production (DEFECTS.md F2).

## What the numbers do and do not mean

- "partially-verified" after this pass = first-time automated evidence at the
  row's real entry: render/readback, safe interactions, geometry, media,
  error-console capture (pages); anonymous state observation with pass/fail
  checks (states); runtime marker binding (templates). It is **not** full
  manual visual approval, live-vs-local pixel parity, or role/permission
  coverage — those remain open per the coverage contract.
- The page sweep completed 235 of 556 selected rows (~42%) before the pass's
  time budget ended; the harness (`local-page-sweep.mjs`) is resumable against
  the same matrix SHA and a rebuilt instance — `resume.json` records the exact
  completion state (matrix sha256
  `25a6599159c031d3e7199a24e5e17ed6224609ed4229b6c5a3ad47c7718dd`, base
  `http://127.0.0.1:8904`, selected 556). Unprocessed rows: term archives
  (brand/series taxonomies) and remaining 390 twins — they keep `pending`.

## Findings

See `DEFECTS.md` — F1 related products absent on production PDPs (template
root cause), F2 empty Global-JS partial on production, F3 410-vs-404
spec/code divergence, F4 local-only CookieYes 390 overflow artifact,
F5 quantified Genie floating-prompt interception observation, F6 harness-fact
records. State-level fail signals (30 rows) are recorded inline in
state-matrix `findings` with observed values; triage: selector/probe
mismatches since corrected or re-verified (compare family verified via
`evidence/comparison-sametab.json`), plus the F3 410 and F4 overflow facts.

## Honest remainder (not covered, with reasons)

1. **Engine/model-dependent families (308 state rows)**: `genie` (124),
   `marketing-genie-entry` (32), `project-brief` (48), `configurator` (60),
   `roof` (44) — require the Genie engine service and model calls, which this
   pass was not authorized to make (no model prompts). Executable in a
   follow-up with `just serve fullmatrix --service engine` and an authorized
   model budget.
2. ~~Role/permission and submission states~~ — **executed in slice 2** on
   the recreated isolated instance (see README "Slice 2"). Sub-items that
   remain open within this group:
   - Inquiry/contact **notification delivery** (receipt-and-notification-queue
     rows' delivery half): outbound jobs are authorized by the Jev assessment
     chain (`Inquiry/Assessment/SendAuthorization`) — engine/model-dependent.
   - Signed-in inquiry end state: F9 (order created as customer 0, no
     confirmation shown) — needs the main line's review before the row can
     close.
   - Proforma PDF content depth: the team status transition was simulated
     locally and the owner document surface probed; full document content
     verification stays with the engine-dependent chain.
   - DE-language submission rows carry refused-submission findings from the
     guard timing window (harness); the identical chains are proven on EN.
3. ~~Page sweep continuation~~ — **completed in slice 2**: all 556 selected
   rows captured (the sweep now covers every pending page row in the
   original matrix).
4. **Manual visual review (visual_review ≠ pass anywhere)**: no row claims
   full manual visual approval; automated geometry/media signals only.
5. **Live-vs-local pixel parity**: not run — requires the paired-capture
   harness (`tests/visual/pixel-parity.mjs`) against a frozen production
   window and a running local instance with per-page masks. Deferred with the
   matrices; the local instance was retired at pass end per the §0 resource
   contract.
6. **DE blog/legal/taxonomy-routing families**: already covered by earlier
   sessions; not re-run (no changes to their surfaces in this batch).

## Resource report

- Instance `fullmatrix`: created by the interrupted attempt, retired after
  slice 1, **recreated for slice 2** from the same snapshot (`just up` +
  `just pull load`, 2760/2760 attachments with 1 missing attachment file
  flagged) with this worktree's plugins linked, and **retired again at
  slice-2 end**. Slice-2 local writes (fixtures, submissions, orders,
  mail-capture files) lived only inside the instance and are destroyed with
  it; the evidence JSONs in this directory carry the durable record.
- Production snapshot `~/de-linker-data/20261104-1914/` kept subject to the
  shared latest-three successful-snapshot boundary (it is the newest pull;
  older snapshots 20261029-* are the rotation candidates for whoever owns
  them — not deleted by this pass because other tasks may hold baselines).
- Raw captures `~/de-linker-data/full-matrix-20261104/` (~250 MB: 235
  full-page screenshots + machine-readable receipts for page/state/template
  passes) kept as the evidence referenced by this record; machine-readable
  JSONs are also copied into the repo under
  `docs/acceptance/2026-11-04/full-matrix/evidence/`.
- All Playwright/Chromium processes verified exited after each run and at
  handoff; no browser tabs left open; /tmp probe scripts removed.
- Disk: baseline 1,272,147,264 KiB free → final measured in the handoff
  (instance ~5 GB reclaimed on retirement, captures ~250 MB retained).
