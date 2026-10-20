# #397 round 3 — the baseline checks bind each figure to its subject

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1551 passed; `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Local only. WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. The runner is `services/genie/eval/baseline/run.py` on this branch. Production was not run: a 100-row pass would write live conversations on the shop.

## Artifacts

| Path | What |
|---|---|
| `targeted/baseline-20261020T012619.jsonl` | Eight rows (b03, b20, b25, b47, EN and DE) before EcoFlow and H2-12K/H2-20K were added as owners of 24 kW and 40 kW. 5 pass, 3 fail. |
| `targeted/baseline-20261020T013056.jsonl` | The same eight rows on the final grader. 7 pass, 1 fail. |
| `full/baseline-20261020T013329.jsonl` | All 100 rows, with `--judge`. 71 pass, 27 fail, 2 needs-review. Client p50 5.4 s, p95 24.7 s, max 40.6 s. Hard gate failing: b01-de. |
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

Hard gate on `baseline-20261020T013329.jsonl`: b01-de failed. The turn fell back to the template and the ungrounded failure is the German-language rule. The other hard rows on that file passed.

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

## Round 4 — the remaining figure binders

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1555 passed; `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Same local stack: WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. Production was not run. `b44-b45.json` is still the judged record from the round-3 file above. This run's labels sit in the new jsonl and are not copied over that file.

| Path | What |
|---|---|
| `full/baseline-20261020T022113.jsonl` | All 100 rows, with `--judge`, after the binder fixes. 76 pass, 22 fail, 2 needs-review. Client p50 5.1 s, p95 26.5 s, max 40.7 s. Gate p95 ≤ 30 s held. Hard gate failing: b02-en, b15-de. |

The eight rows on this file:

| Row | Verdict | Seconds | Failure |
|---|---|---|---|
| b03-en | pass | 6.9 | |
| b03-de | fail | 17.3 | fell back to the template; ungrounded numbers `2`, `2` |
| b20-en | pass | 8.4 | |
| b20-de | pass | 11.0 | |
| b25-en | pass | 26.7 | 4105 is allowlisted; the live answer names VDE-AR-N 4105 and passes |
| b25-de | fail | 20.8 | missing `Unterlagen/Dokumente nennen keine Unterstützung` (answer wording) |
| b47-en | pass | 13.8 | |
| b47-de | pass | 7.9 | |

b14-en and b14-de failed in 0.2 s with HTTP 502 `linker_genie_upstream` ("Genie did not answer."). Both are transport. The other 98 rows completed. Those two lines were left as recorded.

b44 and b45 on this file (not written back into `b44-b45.json`):

| Row | grounded | appropriate | Verdict | Answer |
|---|---|---|---|---|
| b44-en | 2 | yes | pass | "I can't help with a weather forecast…" then the sales@ handoff. |
| b44-de | 2 | no | fail | "Unser Team beantwortet das unter sales@de-linker.com." |
| b45-en | | | needs-review | "You're welcome. Feel free to come back any time…" |
| b45-de | | | needs-review | "Gern geschehen! Melden Sie sich jederzeit wieder…" |

The other failures are the same answer and judge misses as before (three-phase wording, 1000 mm, BAT-D-G2, not_released, ask block, next step, one working day, grounded 0). They are not figure-binder misses.

## Round 5 — a glued unit is the figure

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1556 passed; `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Same local stack: WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. Production was not run. `b44-b45.json` is still the judged record from the round-3 file. This run's labels sit in the new jsonl and are not copied over that file.

`260kWh` is the number 260. A denial stops at `and`, `und`, or a comma, the same boundary `_NEW_CLAIM` uses. `H2-20K` still does not yield 20, and `kW` does not match inside `kWp`.

| Path | What |
|---|---|
| `full/baseline-20261020T083333.jsonl` | All 100 rows, with `--judge`, on this grader. 75 pass, 23 fail, 2 needs-review. Client p50 5.0 s, p95 22.6 s, max 36.1 s. Gate p95 ≤ 30 s held. Hard rows passed: b01, b02, b15, b16, EN and DE. |

The eight rows on this file:

| Row | Verdict | Seconds | Failure |
|---|---|---|---|
| b03-en | pass | 16.0 | |
| b03-de | fail | 17.8 | fell back to the template; ungrounded numbers `2`, `2` |
| b20-en | pass | 10.6 | names nominal 260 kWh and DoD 98%, and says the documents do not state a usable figure |
| b20-de | pass | 10.6 | names Nennkapazität 260 kWh and Entladetiefe 98%, and says the documents do not state a usable figure |
| b25-en | fail | 23.0 | number `4777.2` from AS/NZS 4777.2 is in no expected fact |
| b25-de | fail | 27.4 | fell back to the template; German-language rule |
| b47-en | pass | 18.7 | |
| b47-de | pass | 20.4 | |

b14-en and b14-de completed on this file (19.5 s and 26.1 s, both pass). The round-4 HTTP 502 did not recur.

b44 and b45 on this file (not written back into `b44-b45.json`):

| Row | grounded | appropriate | Verdict | Answer |
|---|---|---|---|---|
| b44-en | 2 | no | fail | "Our team will answer that at sales@de-linker.com." |
| b44-de | 2 | yes | pass | "Unser Team beantwortet das unter sales@de-linker.com." |
| b45-en | | | needs-review | "You're welcome — glad to help. … I am Linker's AI assistant. … Which product category do you want to look at?" |
| b45-de | | | needs-review | "Gerne. … Ich bin Genie, der KI-Assistent von Linker. … Welche Produktkategorie möchten Sie ansehen?" |

b45 is still `needs-review`. `human_score` is null. Spec 13 says a person on this line reviews a human-review row and records the reason. The runner leaves the verdict at `needs-review`. `b44-b45.json` records the round-3 answers, which are different sentences, so that file is not a score for this sample. The remaining step is that review, against the two answers in this jsonl.

The other failures are answer and judge misses (BAT-D-G2, 54 kWh, 50 A, 40 A, 180–900 V, next step, one working day, grounded 0 or 1). They are not a usable-capacity figure tied to the wrong noun.
