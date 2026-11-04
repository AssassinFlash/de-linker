# Genie/Configurator engine-dependent state rows — 2026-11-04

Status: **engine/model-dependent batch of the full-matrix goal (domain B)**.
This record covers the 308 state rows the first full-matrix pass deferred
because they need the Genie engine service and authorized model calls:
`genie` (124), `marketing-genie-entry` (32), `project-brief` (48),
`configurator` (60), `roof` (44). The role/submission families and the page
sweep tail belong to the parallel pass and are untouched here.

## Method (decided with evidence)

- **Environment**: isolated local instance `geniestates`
  (`~/de-linker-local/geniestates/`, ports 8916-8918, DB `linker_geniestates`)
  built from the production snapshot `20261104-1914` (the newest pull; the
  same snapshot the first pass used), with this checkout's plugins. The
  instance was retired at the end of the batch (see the resource report).
- **Services**: the local stack's own real services via `just serve
  geniestates` — the planner engine (`linker_engine` on :8917 with its
  planner worker) and the real Genie service (`linker_genie` on :8918) with
  the newest local document index
  (`~/de-linker-data/index/builds/20261104T095926Z-546140000/index.sqlite`).
  No service mocks, no proxying to production; the browser drives the same
  WP proxy endpoints (`/wp-json/linker-ai/v1/genie/*`,
  `/wp-json/linker/v1/planner/*`) the production site uses.
- **Model channel**: `DEEPSEEK_API_KEY` (official api.deepseek.com, the
  Genie conversation + vision channel) and `OPENROUTER_API_KEY` (jev
  understand/judge) injected into the `just serve` environment — the fixed
  channels of AGENTS §5; no substitutes, no aihubmix. Bounded budget: the
  drivers send a small representative set of real turns (per family file in
  `evidence/`), never bulk sampling.
- **Failure states**: error/recovery UIs are exercised by one-shot network
  aborts (`page.route(... route.abort())`) at the browser boundary — the
  product's real behavior to an upstream failure; every such check is
  labelled `failureInjection` in the evidence. No product code was modified.
- **Mail**: no mail was sent; the local instance captures `wp_mail()` to
  files and blocks direct `mail()` (docs/local-stack.md). No form
  submissions outside the tools' own flows; no production writes.
- **Drivers** (committed here): `genie-driver.mjs`,
  `marketing-entry-driver.mjs`, `configurator-driver.mjs` (configurator +
  roof families), `project-brief-driver.mjs`, shared `lib.mjs`;
  `merge-state-rows.mjs` folds the receipts into the state matrix using the
  first pass's merge rules (pending → partially-verified with receipts,
  failing checks → findings, never downgrade, never clear evidence).

## Results

See `RESULTS.md` for the before/after counts, per-family coverage, defects
with root causes and the honest remainder. Machine-readable receipts are in
`evidence/*.json`; viewport screenshots for every recorded state are under
`screenshots/`.

## Resource report

See the end of `RESULTS.md`.
