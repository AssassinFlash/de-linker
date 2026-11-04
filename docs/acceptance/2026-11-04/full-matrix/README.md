# Full-matrix acceptance pass — 2026-11-04

Status: **this record covers the first-time-full-coverage run executed on
2026-11-04 by the acceptance/full-matrix-2026-11-04 worktree** (continuing an
interrupted earlier attempt on the same branch). The governing full-site goal
remains **in progress**; this pass does not claim its completion. Product code,
production content, forms and mail stayed outside this pass's write scope.

## Source artifacts and baseline recount

The authoritative matrix files are:

- `docs/acceptance/2026-10-22/full-site/page-matrix.json`
- `docs/acceptance/2026-10-22/full-site/state-matrix.json`
- `docs/acceptance/2026-10-22/full-site/template-matrix.json`
- Their execution rules: `docs/acceptance/2026-10-22/full-site/coverage-contract.md`
  and `GOAL.md` in the same directory.

The existing capture/comparison harness is `tests/visual/pixel-parity.mjs`, with
`tests/visual/compare.py`; browser regression fixtures live under `tests/e2e/`.
No matrix generator exists in `tools/`, `tests/`, or `.scratch/`.

**Independent recount at branch base `8c9e6d809` (before this pass's merges,
parsed from top-level rows, not grep):**

| Matrix | Rows | Before this pass |
| --- | ---: | --- |
| Page | 708 viewport rows, 354 unique URLs | interaction: 556 pending, 68 partially-verified, 84 not-applicable · visual_review: 387 pending, 236 partially-verified, 1 partial-with-finding, 84 not-applicable · render: 4 pending |
| State | 1,044 (22 families, 261 named states) | 771 pending, 235 partially-verified, 20 pass, 16 passed, 2 not-applicable |
| Template | 31 | 29 pending, 2 partially-verified |

The audit's headline numbers match this recount exactly.

Approved production copy changes were read from
`docs/acceptance/2026-11-04/905/copy-review.md`, `live-apply-plan.json`, and
`docs/acceptance/2026-11-04/899/ROUND.md` before triage so intended rewrites
are not flagged as defects.

## What this pass executed

All automated work ran against the isolated local snapshot instance
`fullmatrix` (port 8904, snapshot `20261104-1914` of production) plus bounded
read-only GET checks against production (8 requests + 2 SSH `wp db query`
reads). No forms were submitted, no draft mutations performed beyond
click-level probes, no mail, no model calls, no production writes.

1. **Template binding (31/31 templates)** — `template-binding.mjs` fetched
   every template's `post_content` via WP-CLI, extracted a distinctive marker,
   and requested each candidate route on the local snapshot:
   30 templates bound with marker-in-HTML proof; LC 30 "Global JavaScript Code"
   recorded `empty-content-local-and-production` (finding F2 in DEFECTS.md).
   Production corroborated markers for the 404 template and FAQ library.
2. **Page sweep (first-time render/interaction/automated-visual rows)** —
   `local-page-sweep.mjs` walked pending page-matrix rows (EN/DE × 1440/390):
   full-page screenshots, language/H1/title readback, control inventory,
   same-page anchors, disclosures/tabs, one internal-link consumer, console/
   page-error/request-failure capture, overflow and mojibake geometry.
   The run is resumable; see RESULTS.md for how far it got and the exact
   continuation point.
3. **State sweep (anonymous states, passes 1–4)** — `state-sweep.mjs`
   (pass 1), `state-sweep-pass2.mjs` (corrected selectors), 
   `state-sweep-pass3-de-content.mjs` (DE content family on the real
   `/de/loesung/` twin after quarantining an invented-URL capture),
   `state-sweep-pass4.mjs` (final corrections: filter drawer, locale-correct
   pagination selector, `.linker-library-empty` empty state, compare remove,
   chip hit-test, cookie reopen, standalone throttled load). Later passes
   supersede earlier ones per key; error rows never supersede.
4. **Merge** — `merge-evidence.mjs` copied machine-readable evidence into
   `docs/acceptance/2026-11-04/full-matrix/evidence/`, then updated the three
   matrix JSONs in place: pending rows with valid automated evidence became
   `partially-verified` with scope notes; rows with failure signals got
   findings entries; statuses stronger than the new evidence were never
   downgraded; existing evidence was never cleared.

## Results and remainder

See `RESULTS.md` for the final before/after counts, per-family coverage and
the honest remainder list, and `DEFECTS.md` for every defect/divergence with
root cause and reproduction evidence.

## Resource creation and reclamation contract

Baseline disk: 1,272,147,264 KiB available on `/dev/disk3s1`. One pre-existing
instance, `smoke` on port 8901, belongs to another checkout; this pass did not
stop or modify it.

| Resource | Purpose and owner | Retention limit | Reclaim condition | End state |
| --- | --- | --- | --- | --- |
| `~/de-linker-local/fullmatrix/`, DB `linker_fullmatrix`, ports 8904-8906 | Snapshot-backed local WordPress for first-time UI coverage; owner: this pass | One instance | Stop and retire after evidence is exported and verified; remove DB, files, registration | Retired at pass end |
| `~/de-linker-data/20261104-1914/` production pull snapshot | Feed the instance; created by the interrupted attempt, reused | Latest-three boundary per `docs/agents/local-storage.md` | Kept per shared snapshot retention (other tasks' baselines considered) | See RESULTS.md resource report |
| `~/de-linker-data/full-matrix-20261104/` | Raw screenshots + machine-readable receipts | Final run + unique failure evidence only | Keep only evidence referenced by the committed record; superseded partial captures may be trimmed by a follow-up | Kept (referenced) |
| Built-in browser / Playwright Chromium processes | Execute sweeps and probes | Active capture processes only | Exit verified after every run and at handoff | Verified at pass end |
| Committed files under this directory | Durable acceptance counts, findings, reproduction, remainder | Permanent project record | Not a runtime resource | Committed on the branch |

No production forms, inquiry/cart mutations, registrations, mail, model
prompts, or bulk production crawl were performed by this pass.
