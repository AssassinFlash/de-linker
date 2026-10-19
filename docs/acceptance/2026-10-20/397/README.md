# #397 round 3 — the baseline checks bind each figure to its subject

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1551 passed; `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Local only. WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. The runner is `services/genie/eval/baseline/run.py` on this branch. Production was not run: a 100-row pass would write live conversations on the shop.

## Artifacts

| Path | What |
|---|---|
| `targeted/baseline-20261020T012619.jsonl` | Eight rows (b03, b20, b25, b47, EN and DE) before EcoFlow and H2-12K/H2-20K were added as owners of 24 kW and 40 kW. 5 pass, 3 fail. |
| `targeted/baseline-20261020T013056.jsonl` | The same eight rows on the final grader. 7 pass, 1 fail. |
| `full/baseline-20261020T013329.jsonl` | All 100 rows, with `--judge`. 71 pass, 27 fail, 2 needs-review. Client p50 5.4 s, p95 24.7 s, max 40.6 s. |
| `b44-b45.json` | Judge labels for b44 and the floor result for b45. |

## Eight rows

Final grader (`baseline-20261020T013056.jsonl`):

| Row | Verdict | Failure |
|---|---|---|
| b03-en | pass | |
| b03-de | pass | |
| b20-en | pass | |
| b20-de | pass | |
| b25-en | pass | |
| b25-de | fail | missing the absence sentence `Unterlagen/Dokumente nennen keine Unterstützung` |
| b47-en | pass | |
| b47-de | pass | |

The earlier eight-row file is a different sample. b03-en had no cards block. b03-de stated 24 kW next to "OCEAN-Reihe", which is not a subject. b25-de missed the same absence sentence. b20 and b47 passed in both samples.

On the 100-row file the same eight are: b03, b20 and b47 pass in both languages. b25-en fails because the answer names the grid code VDE-AR-N 4105. b25-de fails on the absence sentence again. Neither failure is a figure tied to the wrong model.

## b44 judge

This run called the jev → deepseek-flash cascade. Content floors were clean on both rows. The judge labels are in `meta.judged` of the 100-row file and in `b44-b45.json`.

| Row | grounded | appropriate | Verdict | Answer |
|---|---|---|---|---|
| b44-en | 2 | no | fail | Handoff: "Our team will answer that at sales@de-linker.com." |
| b44-de | 1 | yes | fail | Handoff: "Unser Team beantwortet das unter sales@de-linker.com." |

The 2026-10-19 sample (`~/de-linker-data/baseline-100/fix-397/baseline-20261019T234236.jsonl`) had b44-en grounded 2 / appropriate no (fail) and b44-de grounded 2 / appropriate yes (pass). This run's German label is grounded 1.

## b45 human review

Both rows cleared the floors: no handoff block, no mailbox, no numbers, one text block. The runner's verdict is `needs-review`. A person did not score this sample. The 2026-10-19 sample was also `needs-review` (polite close, no handoff, no numbers). That earlier verdict is not a new score for these answers.

| Row | This run's answer |
|---|---|
| b45-en | "Thank you for reaching out. If anything else comes up — product details, documents, pairings or a solution draft — just get in touch. Have a good day!" |
| b45-de | "Gern geschehen! Wenn Ihnen später noch etwas einfällt – zu Produkten, Pairings, Dokumenten oder einem Lösungsentwurf – bin ich jederzeit für Sie da. Einen schönen Tag noch!" |
