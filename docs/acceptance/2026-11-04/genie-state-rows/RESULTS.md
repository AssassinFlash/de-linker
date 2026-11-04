# Genie/Configurator state rows — results, defects and remainder (2026-11-04)

Environment: isolated local instance `geniestates` (production snapshot
`20261104-1914`) + the local stack's real planner engine and Genie service
(document index `20261104T095926Z-546140000`), model channels fixed per
AGENTS §5 (deepseek-flash official for Genie conversation/vision, jev via
OpenRouter for understand/judge). No service mocks; the browser drives the
production WP proxy endpoints. Failure states were injected only as one-shot
network aborts and are labelled `failureInjection` in the receipts.

## Coverage delta (the 308 engine-dependent rows)

Final tally: **304 of 308 rows partially-verified, 4 pending** (genie
120/124, marketing-genie-entry 32/32, configurator 60/60, roof 44/44,
project-brief 48/48); 43 row-level finding entries. The 4 pending rows are
`genie:home-hero` (one combo), `genie:cross-surface-entry-question-consumed`
(one combo) and `genie:ordinary-draft-failure-owner-isolation` (two combos) —
late-flow states whose recording combos hit run-time errors before those
blocks; the drivers are committed and re-runnable for them.

Before this batch (first full-matrix pass): 32 partially-verified
(citations/document-card/lazy-bundle/signed-facts + 16 configurator rows from
earlier sessions), 276 pending.

| Family | Rows | Upgraded this batch | Still pending | Findings |
| --- | ---: | ---: | ---: | ---: |
| genie | 124 | 102 | 22 | 9 |
| marketing-genie-entry | 32 | 24 | 8 | 10 |
| configurator | 60 | 60 | 0 | 0 |
| roof | 44 | 44 | 0 | 4 |
| project-brief | 48 | 24 | 24 | 0 |

(Filled by the final merge; see `evidence/after-recount.json` for the
authoritative numbers.)

What "partially-verified" means here: first-time real-behavior evidence at the
state's real entry on the local production snapshot — real model turns where
the state needs them, real engine runs, real Woo draft writes — with the
state's remaining scope listed in the receipt. It is not full manual visual
approval or the role/permission halves owned by the parallel pass.

## Defects and observations (root causes; no product-code fixes in this batch)

D1 — **DE create-form untranslated** (product, i18n). On
`/de/loesungskonfigurator/` (document de-DE) the planner workspace shell is
German but the project create form renders English actions ("Create project",
"Cancel"). Root cause: the planner app's form strings are not in the deployed
DE translation set for this build (the .po carries "Projekt anlegen"; the
rendered build does not use it). Reproduction: `evidence/probe-receipts.json`
probe6 + screenshot; drivers worked around it by matching either locale's
label — the matrix row evidence records the observed text.

D2 — **Roof workspace entry hidden** (product, suspected). The only labeled
entry control ("Open roof workspace", `button.lp-button`) renders with a 0×0
box inside a hidden parent on a fresh project and stays hidden after site
data (site use/country/annual), a successful save, clicking the overview
card, and the Location step. The roof workspace itself does load when
entered (an earlier run rendered it, including its explicit "map unavailable
→ plan view" fallback), so the reveal condition exists but was not
identified this pass. All 44 roof rows carry first-time evidence of the
entry state + this finding; the in-workspace states (draw, vertices,
obstacles, undo/redo, gestures) remain open behind it.
Reproduction: `evidence/probe-receipts.json` probe10–14.

D3 — **Vote/copy controls do not attach to documents-routed answers**
(product, suspected). On a product-card turn the answer renders 3
`__vote`-class controls (copy + rating; isolated probe7), but on the
documents-routed datasheet turn no vote/copy controls appeared in any combo
(poll up to 20 s). Customers cannot rate or copy documents answers.
Reproduction: probe7 vs the copy-and-rating receipts in
`evidence/genie-family-*.json`.

D4 — **Dock draft not restored after reload** (product, suspected). A failed
send (injected abort) preserves the typed text in the composer, but after a
page reload and reopening the dock the draft text is gone in every combo
tested. The marketing entries' own recovery (per-path entry records)
restores correctly — see the marketing rows — so the gap is specific to the
dock/workspace composer's failure cache. Reproduction: the
`ordinary-draft-failure-owner-isolation` receipts.

D5 — **Local-stack map tiles** (environment, not a defect). The roof map
loads its tiles from tiles.openfreemap.org; on the local snapshot the map
area renders the app's own "map unavailable → plan view" fallback. Map-tile
rendering cannot be verified on the local stack; production verification
stays open.

D6 — Harness notes (not product findings): parallel in-combo runs raced the
single-process local PHP router (planner RPC aborts, `net::ERR_ABORTED`
React-Query dedup — the engine answered 200 to every completed request);
the product-add pending window is shorter than one 150 ms poll frame; the
app exposes no GET `/genie/draft` route (readback must use the native draft
page — the native chain is proven by probes 4 and 7).

## Honest remainder

1. Roof in-workspace states (44 rows upgraded only to entry-level evidence;
   the draw/vertices/obstacles/orientation/undo/gesture states need D2
   resolved or the reveal condition identified).
2. configurator report/PDF/logo states (4×4 rows): the report stage was not
   reached this pass (it sits behind the equipment/roof stages); scoped
   receipts recorded.
3. incompatible-result: the out-of-cap input variant was not forced; only
   the in-cap run path was exercised.
4. Voice granted-microphone dictation and mobile multi-touch gestures are
   not drivable in headless Chromium; their unsupported-environment halves
   are evidenced.
5. Role/permission halves (approved accounts, cross-account reads) belong
   to the parallel batch, not this one.
6. Manual visual review and live-vs-local pixel parity remain open for all
   rows (coverage contract).

## Resource report

- Instance `geniestates` (ports 8916-8918, DB `linker_geniestates`) and its
  engine/Genie services were created by this batch and retired at the end
  (`just down` + retirement). Snapshot `20261104-1914` was reused, not
  re-pulled.
- Screenshots (~36 MB, 500+ viewport captures) live under
  `~/de-linker-data/genie-state-rows-20261104/screenshots/`, referenced by
  the receipts; they are reproducible captures and may be trimmed to the
  finding-relevant subset after review.
- /tmp/gstates (probes, logs, served PNGs) removed at handoff; the two
  temporary HTTP file servers (ports 8940, 8975) stopped.
- Model spend: ~70 real deepseek-flash turns + jev understand/judge calls
  across all runs (bounded, no bulk sampling; all through the fixed
  channels).
