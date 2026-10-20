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

`260kWh` is the number 260. A denial ended at `and`, `und`, or a comma; this round's regex also treated `although`/`though` as contrasts, which round 6 corrected (they are concessive and do not cancel a denial). `H2-20K` still does not yield 20, and `kW` does not match inside `kWp`.

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

## Round 6 — the punctuation inverter, the unbounded filler and the 4105 context

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1589 passed (the branch is rebased on `origin/main`, whose new tests are included); `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Same local stack: WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. Production was not run.

The review's probes, before → after on this head:

| Probe | Before | After |
|---|---|---|
| `260 kWh — the usable capacity` (EN and DE) | no failure | banned figure |
| `260 kWh: the usable capacity` (EN and DE) | no failure | banned figure |
| `… liegt nach Angaben im Datenblatt bei 260 kWh` | no failure | banned figure |
| `GW20K-ETA-G20 has 30 kW PV input` | no failure | not a figure of GW20K-ETA-G20 |
| `… not stated although the nominal capacity is 260 kWh` | banned figure (false positive) | clean |
| `… whether the SAJ H2, a three-phase hybrid, supports EnWG 14a` | clause assertion (false positive) | clean |
| `4105 kWh` / `4105000 Wh` / `4105 A/W/V` | allowed | not in the VDE-AR-N context |
| `VDE-AR-N 4105` | allowed | allowed |

`test_source_notes_cite_the_figure_that_owns_the_number` is removed; it asserted ground prose. The row expectations carry the corrections instead (the grounds keep the page notes).

Rows: b05 gets the L260 sheet's true figures (98/400/181 from p.2, plus 8500/50/40 and the rest of the p.1-2 table), b11 the H2 50 A short-circuit current, b12 40 A and 180-900 V, b25 the AS 4777.2 figure. 4105 leaves `numbers` and becomes `context_numbers` (VDE-AR-N clause only). b03 binds 30 kW to 3585/2063.

| Path | What |
|---|---|
| `full/baseline-20261020T093107.jsonl` | All 100 rows, with `--judge`, on this head. 76 pass, 22 fail, 2 needs-review. Client p50 4.9 s (median 5.0 s), p95 26.0 s, max 41.1 s. Gate p95 ≤ 30 s held. Hard gate failing: b02-en (phase powers). |
| `targeted-r5/baseline-20261020T092728.jsonl` | The 14 affected rows (b03, b05, b11, b12, b20, b25, b45, EN and DE). 9 pass, 3 fail, 2 needs-review. |
| `targeted-r5/baseline-20261020T093037.jsonl` | b05 after the rest of the L260 sheet's true figures were added. 2 pass. |
| `b45-human-review-r5.json` | The b45 review this round: both answers pass the human-review step, reasons in the file. |

The affected rows on the full file:

| Row | Verdict | Seconds | Failure |
|---|---|---|---|
| b03-en | pass | 7.2 | |
| b03-de | pass | 25.0 | |
| b05-en | pass | 12.5 | |
| b05-de | pass | 10.9 | |
| b11-en | pass | 9.3 | |
| b11-de | pass | 10.2 | |
| b12-en | pass | 9.5 | |
| b12-de | pass | 10.3 | |
| b20-en | pass | 8.3 | |
| b20-de | pass | 22.2 | |
| b25-en | pass | 18.8 | |
| b25-de | fail | 35.2 | missing the absence sentence `Unterlagen/Dokumente nennen keine Unterstützung` (answer wording) |
| b45-en | pass (human review) | 4.1 | |
| b45-de | pass (human review) | 2.3 | |

b25's ground now says the Standard row is on pages 1 and 2 of both H2 datasheets by `pdftotext` (the Docling table's provenance page is 2), and that 4105 is context-bound.

The remaining failures are answer and judge misses: b02-en (a grader miss, corrected in round 7: the answer labels 3/3.68/4.6 kW single-phase and 5/6/8 kW three-phase, but the phase check measured character distance across the bullet newline and read the next bullet's "Three-phase" as nearer), b04-de (number 10), b07 (BAT-D-G2), b08-de (no compare block), b09 (not_released/fallback), b19 (ask block), b23 (next step), b25-de (absence wording), b28 (one working day/next step), b30/b43/b44 (judge), b41/b42 (next step). None is a figure-binder hole.

## Round 7 — the separator, the line, the catalogue code and the code's own number

Checks on this commit, from `services/genie`: `uv run --locked pytest` 1701 passed, 1 skipped (147 deselected); `ruff check .`, `ruff format --check .`, and `mypy .` clean. The repo-wide `just check` / `just test` was not run.

Same local stack: WordPress `http://127.0.0.1:9177`, Genie `http://127.0.0.1:9179`. Production was not run. The branch is rebased on `origin/main` 97457426.

The review's probes, before → after on this head:

| Probe | Before | After |
|---|---|---|
| `260 kWh—the usable capacity` (EN and DE) | no failure | banned figure |
| `260 kWh - the usable capacity` (EN and DE) | no failure | banned figure |
| `260 kWh:the usable capacity` (EN and DE) | no failure | banned figure |
| `260 kWh —the usable capacity` (EN and DE) | no failure | banned figure |
| `260 kWh-the usable capacity` (unspaced hyphen) | no failure | banned figure |
| b02-en bullet answer (3/3.68/4.6 single-phase, 5/6/8 three-phase) | 4 phase failures | pass |
| b02-en prose answer (`single-phase … 3 kW, 3.68 kW and 4.6 kW, while the three-phase …`) | 2 phase failures | pass |
| `SAJ H2-25K-T3 (25 kW)` in the catalogue + "25 months" | 25 allowed | 25 in no expected fact |
| `BAT-D-G20-Serie`, `GW3K–10K-EHA-G20` | passed by a product-name accident | still codes |
| `VDE-AR-N 4105 … 4105 kWh` in one clause | no failure | the second 4105 fails |
| `VDE-AR-N 4105` | allowed | allowed |

b13-en/de now carry the warranty document's true figures: 2 (accessory modules, p.1), 12 (period start, p.1; extension window, p.4/p.5), 15 (15 May 2023, p.4/p.5), 16 (ET PLUS+ 16 A), 20 (20 kW cap), 25 (25 kW and above; RSD receiver 25 years), 30 (30 months; 30 December in the DE document), 40/50 (ET 40-50kW), 80/100 (ET 80-100k), 125 (PCS 125k / RSD receiver 100/125k), 1100/1500 (HT 1100V/1500V), with EN pages 1/2/4/5 and DE pages 1/2/5 in the ground. A fabricated 42 still fails.

Rows corrected this round, each with a page or feed source in the ground: b03 12; b04 60/110/61.4/112.6; b08 20; b11 3/600; b13 the figures above; b14 10/12/15/20/25/29.999; b21 10; b25 29.999; b46 20/26; b47 220/230/240/60.5. b20-en accepts "do not print"/"cannot state"; b20-de tolerates emphasis; b50-de accepts "hinzufügen" beside "bestehend/nachrüsten". The b20 grounds say the `liegt` filler is unbounded. The b25 grounds say 4105 passes only as the code's own number.

| Path | What |
|---|---|
| `full/baseline-20261020T115531.jsonl` | All 100 rows, with `--judge`, on this head. 82 pass, 16 fail, 2 needs-review. Client p50 5.7 s, p95 28.0 s, max 36.6 s. Gate p95 ≤ 30 s held. No hard row failed: b01, b02, b15 and b16 passed in both languages. |

The 16 failures are answer, transport and judge misses, not figure or expectation holes: b07-en (does not name BAT-D-G2), b09-en/de (not_released), b14-de (fell back; ungrounded), b19-en/de (no ask block), b22-de (signed net-price sentence repeated), b25-de (absence wording), b28-en (one working day), b30-en/de, b42-en, b43-en/de, b44-en/de (judge). b45-en/de stayed needs-review.
