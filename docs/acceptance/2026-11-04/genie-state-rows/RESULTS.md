# Genie/Configurator state rows — results, corrections and remainder (2026-11-04, round 3)

Environment: isolated local instance `geniestates` (production snapshot
`20261104-1914`, `http://127.0.0.1:8904`) with the local stack's real planner
engine (:8905) and Genie service (:8906), model channels fixed per AGENTS §5
(deepseek-flash official for the Genie conversation/vision, jev via
OpenRouter for understand/judge). No service mocks; the browser drives the
production WP proxy endpoints. Failure states were injected only as one-shot
network aborts and are labelled `failureInjection`.

## Counts (recomputed from `docs/acceptance/2026-10-22/full-site/state-matrix.json`)

1044 rows in total:

| Status | Rows | Before this round |
| --- | ---: | ---: |
| partially-verified | 694 | 642 |
| pending | **312** | 364 |
| not-applicable | 2 | 2 |
| pass | 20 | 20 |
| passed | 16 | 16 |

Target families — every row is now partially-verified, none pending:

| Family | Rows | pending before | pending now |
| --- | ---: | ---: | ---: |
| genie | 124 | 8 | **0** |
| roof | 44 | 44 | **0** |
| configurator | 60 | 0 | 0 |
| marketing-genie-entry | 32 | 0 | 0 |
| project-brief | 48 | 0 | 0 |

Which rows are round-3 evidence: **94 rows carry a round-3 receipt**
(`genie-family-fix*`, `genie-states-round3*`, `roof-family-<lang>-<width>`);
the other **214 target-family rows keep their earlier receipt**, because the
harness fix invalidated only the rows listed above and the instruction was to
re-run the affected rows, not the whole batch. Both kinds are real sessions
against this instance; none is inferred.

The 312 remaining pending rows belong to the parallel pass's families
(account 56, draft 48, inquiry 45, authentication 39, home 32,
global-navigation 12, product 28, contact 24, comparison 10,
files-and-feedback 8, content 5, product-archive 3, document-library 2).
This batch did not drive them and does not claim them.

What "partially-verified" means here: first-time real-behaviour evidence at
the state's real entry on the local production snapshot — real model turns
where the state needs them, real engine runs, real Woo draft writes — with
the state's remaining scope listed in the receipt. It is not full manual
visual approval and not the role/permission halves owned by the parallel
pass.

## What the first two rounds got wrong (corrected in round 3)

These were **harness defects, not product defects**. The findings they
produced were removed from the affected rows instead of being kept as
evidence.

1. **`copy-and-rating` recorded success unconditionally.** The driver passed
   `check("turn succeeded", true)`, so a turn that ended in "Genie did not
   answer" still counted as success, and the thumb controls (which only render
   on an answered turn — `VoteButtons` returns `null` without the meta
   `turn_id`) were reported as a documents-route UI gap. The DE rows were hit
   worst: their turns had failed. Round 3 requires proxy 2xx + `turn_id` +
   customer-visible answer text before any control check, and records a failed
   turn as a failed turn with the app's own error text.
2. **Recovery was read from the wrong Genie instance.** Pages carrying the
   home hero mount two instances (`#linker-genie-mount` dock and
   `.linker-genie-hero__surface` hero). The driver clicked the first
   `[data-genie-owned-recovery]` in DOM order — the hero's panel — and then
   read the dock composer, so restore looked broken. Scoped to
   `#linker-genie-mount`, restore puts the text back in the composer in ~0.6 s
   and survives a further reload.
3. **The roof workspace was never entered.** The driver looked for the
   overview's "Open roof workspace" button while the app sat in the site
   workspace, where the overview fieldset is hidden
   (`ProjectEditor.tsx`, `hidden={workspace !== "overview"}`). The real entries
   are the rail link `a[href="#lp-design"]` and the overview button. The
   workspace itself opens, builds faces, obstacles and saved revisions.
4. **The roof assertions proved clicks, not roofs.** "Add roof face control
   present: true" is not a roof. Round 3 reads the face back from the object
   tree and the reopened properties form, reads pitch/bearing from its own
   fields, moves a boundary vertex and reads it back, checks that undo removes
   the obstacle and redo restores it, and verifies Save through the revision
   the app reports plus a reload that still shows the face and the overview's
   "Current layout".
5. **The 390 layout is not the 1440 layout.** At 390 the planner replaces the
   rail with the `select.lp-mobile-workspace` ("Project sections"); clicking
   the rail times out because it is not rendered. Navigation now follows the
   layout that is actually shown.
6. **Numbers are typed in the interface's own decimal format.** `0.8` and
   `48.14` are refused in German with "A valid number is required"; the
   planner parses a decimal comma on `de_DE_formal`. The driver now formats
   every numeric entry per locale.
7. **The clipboard carries the answer's markdown, the DOM carries it
   rendered.** Comparing `### Title` against `Title` failed a working copy
   button. Syntax markers are stripped before the comparison.
8. **A state-name table in the merge turned failures into `scope`.** It
   reclassified every roof failure and several others as "scope" so they
   stopped counting. It is deleted. `scope` is now only what a driver declares
   explicitly with a reason; `not-applicable` likewise requires an explicit
   reason.
9. **Stale rounds outlived the round that replaced them.** The merge kept
   findings from superseded rounds, and it never loaded the
   `roof-family-<lang>-<width>.json` shards at all (the filename pattern
   covered three families). Both are fixed: a newer round supersedes an older
   one for the same row, this batch's findings are rewritten per row, and the
   roof shards are folded in.

## Defects and observations that remain (not hidden)

- **D1 — DE create-form untranslated** (product, i18n). On
  `/de/loesungskonfigurator/` the planner shell is German but the project
  create form renders English actions ("Create project", "Cancel"). Root
  cause: the planner app's form strings are not in the deployed DE set for
  this build (the `.po` carries "Projekt anlegen"; the rendered build does not
  use it). The drivers accept either locale's label; the observation stands.
- **Vote is one-shot and permanent.** `VoteButtons` allows one vote per turn
  and disables the other; the POST returns 200 and the button stays pressed.
  Verified, not a defect — noted because the matrix row's wording ("vote
  accepted") is satisfied by exactly one accepted vote.
- **A dropped save reports "The request status could not be confirmed."**
  (`GenieSaveUnconfirmedError`), not "Not saved": the write may have landed.
  Verified by injecting one abort on `/genie/solution` and then letting the
  retry run — the card then reads "Saved in this browser for now." Nothing is
  claimed about the account-side write, which needs an approved account
  (parallel pass).
- **The standing dock does not exist at ≤860px.** `.linker-genie` is
  `display:none` under the 861px switch by design ("The live page hides its
  bubble under 861px", `genie.css`); measured 0×0 at 390 and 860, 50×50 at
  861 and 1440. The 390 `dock` and `dock-keyboard-focus-escape-and-return`
  checks are recorded as `not-applicable` with that measurement — not as a
  pass, not as a defect.
- **`/genie/` prints no floating opener.** It is the workspace itself; the
  dock markup (`Entries::dock()`) belongs to every other page. The dock rows
  are driven on a marketing page, which is where the control exists.

### Findings left in place from earlier rounds (not re-driven this round)

These rows still carry object findings from the batch's first two rounds.
They are in families this round did not re-record, and a spot check shows at
least two of them are the same class of harness error, so they must not be
read as confirmed product defects:

- `configurator` (40 findings across 9 states): `calculation trigger present`
  — the real controls in that workspace are "Weather-based PV reference",
  "PVGIS annual AC reference", "Prepare weather settings", "Generate planning
  report"; the old check looked for a generic run label and found none.
  `roof-optional-entry` — the optional-roof copy is present in the project
  overview ("…Roof design is optional…"), the old selector missed it.
  `report` / `download-pdf` / `logo-upload` / `whole-parts-add` /
  `draft-readback` / `report-screen-pdf-content-and-current-revision` were
  never reached because the driver stopped at the stage before them.
- `marketing-genie-entry` (16) and `project-brief` (12): suggestion-prefill,
  busy-turn dedup, closed-refresh recovery, source-stage, report PDF and
  revision consumption. Not re-driven this round.

12 further findings are plain-text strings from earlier sessions
(`genie:dock-keyboard-focus-escape-and-return` ×4,
`genie:ordinary-draft-failure-owner-isolation` ×4, and four others outside
this family set). They predate this batch and are left untouched.

## Honest remainder

1. The `configurator` report/PDF/logo, whole-parts-add, draft-readback and
   calculation states need their own round with the real control labels above;
   this batch left their earlier findings untouched rather than re-stamping
   them.
2. `marketing-genie-entry` and `project-brief` states listed above are in the
   same position.
3. Voice granted-microphone dictation and multi-touch pinch/rotate have no
   headless synthesis; those halves are recorded as `scope` with the reason,
   never as passes.
4. Role/permission halves (approved accounts, cross-account reads, the
   account-side of a saved solution) belong to the parallel batch.
5. Manual visual review and live-vs-local pixel parity remain open for all
   rows (coverage contract).
6. The local host ran under memory pressure during this round (swap 7.1/8 GB
   used at the worst point); a few runs were interrupted by Chromium being
   reclaimed and were re-run — every recorded receipt in `evidence/` is from a
   completed run.

## Commands

```
# the record's own drivers (BASE=geniestates)
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:1440 node genie-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:1440 node genie-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:390  node genie-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:390  node genie-fix-driver.mjs

GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:1440 node genie-states-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:1440 node genie-states-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:390  node genie-states-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:390  node genie-states-driver.mjs

GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:1440 node roof-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:1440 node roof-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=en:390  node roof-fix-driver.mjs
GSTATES_BASE=http://127.0.0.1:8904 GSTATES_ONLY=de:390  node roof-fix-driver.mjs

node reset-invalidated-rows.mjs   # returns the re-recorded rows to pending
node merge-state-rows.mjs         # folds the receipts into the state matrix
```

## Resource report

- Instance `geniestates` (8904/8905/8906, DB `linker_geniestates`) was reused
  from the previous session under the owner's instruction ("复用
  geniestates"); it is **left running** for the next round. Snapshot
  `20261104-1914` reused, not re-pulled.
- Chromium processes from interrupted runs were killed twice during the round
  (18 processes, ~1 GB freed each time). No Chromium is left running.
- Screenshots: round 3's captures are committed in this record's
  `screenshots/` and referenced repo-relative (92 such references, all
  verified to resolve). The earlier rounds' captures were never committed
  (36 MB of PNGs); their matrix entries carry the **basename**, and the file
  lives in `~/de-linker-data/genie-state-rows-20261104/screenshots/<basename>`
  (202 such entries). Receipts in `evidence/*.json`.
- `/tmp` probe scripts used for diagnosis were removed
  (`gs-*.mjs`); nothing outside this worktree and `~/de-linker-local` was
  written.
- Model spend: bounded real turns — 2 per combo in `genie-fix-driver`, 3 per
  combo in `genie-states-driver`, 1 hero turn at en:1440, plus the roof
  family's none. No bulk sampling.
