# Campaign #335 — i18n and page drift

Adversarial tests for issue #335. The harness grades answers. It does not change product code, open fix tickets, or send inquiry, contact, or mail.

## What it runs

Local instance `c335` (snapshot `20261019-1715`), Genie at the instance's own service. Turns go to `POST /turn` with the service token. Page suggestions are read from the dock's `data-prompts` on an anonymous GET. Nothing posts a contact or an inquiry.

| Group | Cases | What a defect is |
| --- | --- | --- |
| Twins | T-pair, T-mppt, T-cost, T-mail, T-address, T-ban, T-sie | Card set, block types (an `ask` block aside), cited numbers, banned words, du-form, or a handoff that is not the mailbox sentence. A document-count difference, and figures only one side adds, are notes |
| Prompts | product, category, draft, account, blog, FAQ, EN and DE | Fewer than two suggestions, or a suggestion that is not the reviewed string for that page |
| Drift | one product title, one blog paragraph, one German translation of that product | A rendered edit the answer still quotes from the previous copy |
| Language | mixed question, mid-thread switch, bare model code | Recorded against the #374 rule (the question's language, or the page when the question is mixed or neutral). Report only |

The product is the SAJ H2-10K-T3. The drift marker is `C335DRIFT`, placed before a trailing parenthesis so the short product name keeps it. The blog marker is a paragraph the question does not contain. Titles and the blog body are restored from files after the asks, including when a turn fails.

`D-blog-warm` runs before the blog edit, so `edit-not-rendered` there is the expected reading.

## Run

From this directory, after `just up c335`, `just pull load c335 latest`, and `just serve c335`:

```bash
uv run --locked python run_battery.py ~/de-linker-data/campaign-335
```

Production, question only, two turns, then delete:

```bash
uv run --locked python prod_smoke.py --confirm-production
```

Without `--confirm-production` the smoke refuses `de-linker.com` and `www.de-linker.com` and does not connect. It also refuses a redirect onto those hosts. A 307 or 308 would keep the POST body, so the hop is not followed, and the final host is checked again.

The battery exits 1 when the mail spool grows, or when the drift phase ran and the title and blog were not restored from the snapshot files written before the edit. Issue #406 is open, so this harness does not claim a successful `wp linker-i18n translate`. On a failed translate it records that the German title, the attribute numbers, and the prices after a successful re-translation were not measured. The 2026-10-19 reading is 15 passes, 5 defects, and 2 notes (`NOTES.md`). The files in `~/de-linker-data/campaign-335/` are that run and stay as they were.

Evidence stays in `~/de-linker-data/campaign-335/` (`turns.jsonl`, `prompts.jsonl`, `twins.jsonl`, `language.jsonl`, `drift.jsonl`, `drift.json`, `summary.json`). `home-de/` repeats the mailbox twin and the language cases after the hreflang parser accepts any attribute order. `address/` repeats the imprint twin against `/imprint/` and `/de/impressum/`. Evidence is not committed. `NOTES.md` is the reading of that evidence.
