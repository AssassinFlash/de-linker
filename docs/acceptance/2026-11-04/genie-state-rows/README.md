# Genie/Configurator engine-dependent state rows — 2026-11-04

Status: **engine/model-dependent batch of the full-matrix goal (domain B)**.
This record covers the 308 state rows the first full-matrix pass deferred
because they need the Genie engine service and authorized model calls:
`genie` (124), `marketing-genie-entry` (32), `project-brief` (48),
`configurator` (60), `roof` (44). The role/submission families and the page
sweep tail belong to the parallel pass and are untouched here.

The first two rounds of this batch produced findings that were **the harness's
own defects**, not the product's. Round 3 (`fixRound: 3`) re-recorded the
affected rows with assertions that read the customer-visible result; the
earlier findings were removed from those rows rather than kept as evidence.
What was wrong and how it was corrected is in `RESULTS.md` §"What the first
two rounds got wrong".

## Method (decided with evidence)

- **Environment**: isolated local instance `geniestates`
  (`~/de-linker-local/geniestates/`, ports 8904-8906, DB
  `linker_geniestates`) built from the production snapshot `20261104-1914`,
  with this checkout's plugins. `just status` reads it as
  `http://127.0.0.1:8904` running `planner-worker, engine, genie`.
- **Services**: the local stack's own real services — the planner engine on
  :8905 (with its planner worker) and the real Genie service on :8906 with
  the local document index. No service mocks, no proxying to production; the
  browser drives the same WP proxy endpoints the production site uses
  (`/wp-json/linker-ai/v1/genie/*`, `/wp-json/linker/v1/planner/*`).
- **Model channel**: `DEEPSEEK_API_KEY` (official api.deepseek.com, the Genie
  conversation + vision channel) and `OPENROUTER_API_KEY` (jev
  understand/judge) in the service environment — the fixed channels of
  AGENTS §5; no substitutes, no aihubmix. Bounded budget: two real turns per
  combo plus one hero turn, never bulk sampling.
- **What counts as an answer** (`lib.mjs: askTurn`): the proxy answered 2xx,
  the answer meta carried a `turn_id`, and the assistant message the customer
  reads carries text. `VoteButtons` renders only when the meta has a
  `turn_id`, so a turn that failed has no thumb controls by construction; such
  a turn is recorded as a failed turn with the app's own error text, never as
  a missing control and never as a route gap. One bounded retry on the app's
  own "Try again" is allowed and named in the check detail.
- **Instance scoping**: pages that carry the home hero mount **two** Genie
  instances (`#linker-genie-mount` dock and `.linker-genie-hero__surface`
  hero). Every read and write is scoped to one of them; an unscoped
  `[data-genie-owned-recovery]` lookup reads the hero's panel while the dock
  composer stays empty.
- **Failure states**: error/recovery UIs are exercised by one-shot network
  aborts (`page.route(... route.abort())`) at the browser boundary — the
  product's real behaviour to an upstream failure; every such check is
  labelled `failureInjection` in the evidence. No product code was modified.
- **Mail**: no mail was sent; the local instance captures `wp_mail()` to
  files and blocks direct `mail()`. No production writes.
- **Drivers** (committed here): `genie-driver.mjs`,
  `marketing-entry-driver.mjs`, `configurator-driver.mjs`,
  `project-brief-driver.mjs`, the round-3
  `genie-fix-driver.mjs` + `roof-fix-driver.mjs`, shared `lib.mjs`;
  `reset-invalidated-rows.mjs` returns the re-recorded rows to `pending` and
  drops the invalidated findings; `merge-state-rows.mjs` folds the receipts
  into the state matrix.
- **Merge rules**: pending → partially-verified with the receipt, failing
  checks → findings with the observed value, stronger statuses never
  downgraded, existing evidence never cleared. A `scope` result is only what
  a driver declares explicitly with a reason (today: multi-touch pinch has no
  headless synthesis); there is no state-name table that turns failures into
  scopes.

## Results

See `RESULTS.md` for the counts, per-family coverage, the round-3 corrections,
the remaining defects with root causes, and the honest remainder.
Machine-readable receipts are in `evidence/*.json`; screenshots for every
recorded state are under `screenshots/`.

## Resource report

See the end of `RESULTS.md`.
