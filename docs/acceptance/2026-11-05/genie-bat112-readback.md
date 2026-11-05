# Genie consumer read-back for the BAT-C association (2026-11-05)

Companion to `vendor-originals-integration.md`. The customer-facing proof of
the association fix + knowledge-generation rebuild.

## Real customer question (production)

Real Chrome on `/genie/`: "What is the maximum charge and discharge current of
the GoodWe GW112.6-BAT-AC-G10 battery?"

- Probe 400 → invisible challenge → retry **200**.
- Genie answered: maximum charge current **180 A**, maximum discharge current
  **220 A** — the correct values for this model — with the real citation link
  "GW112.6-BAT-AC-G10 · Datasheet (EN) · p. 2".

So the chain Woo product → document association (1955 added) → knowledge
generation (`20261105T064354Z`) → Genie answer is verified end to end for the
product that was missing its manual association.

Screenshot: `~/de-linker-data/genie-readback-20261105/bat112-answer.png`.

## F-line configuration check (same round)

`.github/workflows/check.yml`: `concurrency` + `cancel-in-progress: true`
(superseded runs cancel), and the `plan` job drives change-scoped lanes via
`tools/checks/ci_scope.py` (docs-only PRs skip every module lane, as observed
on the 2026-11-05 documentation PRs). Local checks run the same
`just ci-*-package` recipes as the lanes.
