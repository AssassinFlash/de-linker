# #336 part B — 100-question baseline + grading harness (smoke)

Campaign #329. Ticket #336 asks for the 20-question comparison set (`docs/research/2026-10-17-knocket/TRIAL.md`) expanded to 100 questions, scored by the trial's口径, repeatable.

## What is in the repository

| Path | What |
|---|---|
| `services/genie/eval/baseline/baseline100.jsonl` | 100 rows, EN/DE pairs, 10 categories. Smoke slice first (map #329 hard rows: trials 1, 8, 10, 14), then slots in id order. Trials 6 and 19 replaced slots b20 and b25, so documents is 14 rows and sizing and price are 8. |
| `services/genie/eval/baseline/grade.py` | The trial's口径 as pure functions: a product counts only inside a cards or compare block, every row's numbers are checked (empty means none may appear; catalogue model/SKU codes and unit conversions are the only other allowances), phase powers are tied to their phase label, next step, no fallback / no sales@ on hard rows, price-gate sentence off the card, page citation, forbidden words (AGENTS.md §3). |
| `services/genie/eval/baseline/qualitative.jsonl` | 30 rows, three per dossier Top-10 gap. Separate from the scored 100. Judge or human-review. #339 has no case ids, so the rows live here. |
| `services/genie/eval/baseline/run.py` | Runner: one real turn per row through `POST /wp-json/linker-ai/v1/genie/turn` (the bubble's own route), captures meta + blocks + seconds + `meta.timing`, writes JSONL, prints one table that includes `needs-judge` and `needs-review`. `--limit`, `--only`, `--lang`, `--category`, `--judge`, `--qualitative`, `--strict` (a failed row, or client p95 above 30 s). |
| `services/genie/tests/test_baseline.py` | Composition, all 20 trial seeds, hard-row presence, EN/DE criteria (not only slot and category), every expected product id in the catalogue fixture, and the round-2 gates: fabricated counts, a cardless hard row, swapped phase powers, trial 6 and 19 loopholes, judge-row content, the report, the p95 gate, meta timing, the qualitative section. |

The rows also reuse the existing sets' data conventions: `services/genie/index/eval/golden.jsonl` (document facts and the model codes), `services/genie/eval/knowledge/questions.json` (the #257 document floor), `services/genie/eval/page/questions.json` (page contexts and IDs), `services/genie/eval/contact/cases.json` (contact reasons), and `plugins/linker-commerce/data/compatibility.json` (pairing verdicts).

## Set composition

| Category | EN | DE |
|---|---|---|
| product-match (incl. trial 1, 8) | 5 | 5 |
| pairing | 5 | 5 |
| documents (incl. trials 6, 10, 19) | 7 | 7 |
| sizing (incl. trial 14) | 4 | 4 |
| price | 4 | 4 |
| inquiry | 5 | 5 |
| handoff | 5 | 5 |
| company-logistics | 5 | 5 |
| smalltalk | 5 | 5 |
| page-awareness | 5 | 5 |

Assertion split: 84 deterministic, 14 judge (reference answer points + the jev → deepseek-flash cascade), 2 human-review (polite closes).

All 20 trial questions are seeded, each as an EN/DE pair. Trial 6 (slots b20) is deterministic: the hosted L260-OMNI datasheets (sha256 270d7e015db5, bb6712735d77, bc2a88c8df17, portfolio fd58ff91d790; goldset 0121878b05 and 1579d71588) state nominal capacity 260 kWh and depth of discharge 98% (single string), and they do not state a usable capacity. The answer must say so and must cite nominal 260 kWh and DoD 98%. TRIAL.md's DoD 5–95% is stale against these sheets. Trial 19 (slots b25) is deterministic: the SAJ H2 datasheets, the 10–30K manual (770ccafa080c) and the H2/HS2/HS3 configuration note (a470d6e1be68) do not contain "14a" or "EnWG". The note's §6.14.1 RCR power control for Germany/Austria above 25 kW is not an EnWG 14a statement. The answer must say the documents do not state support and must not assert support.

Slots replaced, and why: **b20** (sizing, "6 kWp and 4500 kWh") was the same `open_configurator` assertion as the hard sizing row b16, with no extra branch (b17 still covers backup wording, b19 the missing-input ask). **b25** (price, "which is cheaper") was a judge row a guest cannot answer; b21–b24 and b23 already hold the price gate. Documents had no non-seed slot, so these two document trials take those slots and documents is 14 rows, sizing and price 8. Filing them under sizing or price would have kept 10 per category and scored document questions in the wrong bucket.

The map's hard four (1/8/10/14) are `hard: true` and carry `no_handoff` (no handoff block, no sales@de-linker.com in the text), and they stay first in the file.

Every scored row has `expect.numbers`. An empty list means the answer may not contain a number. A catalogue model or SKU, and a unit conversion of an expected value, are the only other numbers that pass.

EN and DE of one slot share the criteria, not only the category and the assertion kind: the same keys, the same product ids, the same number list, the same phase-to-power table. The regex text differs because the sentences do. Slot 46 is the pair this caught: the English row required product 6528 and the German row did not, so "Dieses Gerät hat 4 MPPT" passed German with no card.

## Qualitative section (dossier Top-10)

`qualitative.jsonl` is not part of the 100 and is not in the scored fraction. Three rows per gap:

| Gap | Dossier | Rows | How it is judged |
|---|---|---|---|
| topic-switch | #1 | q-topic-1..3 | judge, with the previous turn in `history` |
| prompt-injection | #2 | q-inject-1..3 | judge; an injected price, usable kWh, or "sent" claim fails the content check |
| latency | #3 | q-latency-1..3 | judge on the document facts; the p50/p95 numbers come from the runner |
| sse-break | #4 | q-sse-1..3 | human-review. The WordPress route buffers the body, so this runner cannot cut the stream. A stream with no `done` fails. The UI states are #332 |
| concurrency | #5 | q-conc-1..3 | human-review. Each row names both tabs in `tabs`. This runner sends one turn. The two-tab run is #331 |
| card-staleness | #6 | q-card-1..3 | human-review. No row clicks send |
| misspelling | #7 | q-spell-1..3 | judge |
| page-drift | #8 | q-drift-1..3 | human-review against the current page. The cache comparison is #335 |
| mixed-language | #9 | q-mix-1..3 | judge |
| series-ambiguity | #10 | q-series-1..3 | judge. The scored row for the OCEAN 2 case is b02 |

#339 is the regression-fixture ticket and has no case ids yet. These 30 rows are the qualitative section it can adopt. They are not mapped onto case ids that do not exist.

```
cd services/genie
uv run --locked python eval/baseline/run.py --wp http://127.0.0.1:9168 \
    --out ../../docs/acceptance/2026-10-19/336/qualitative --qualitative
```

## Smoke run (local instance c336b, live snapshot, this checkout's code)

`just up c336b`; `just pull load c336b latest` (the instance runs the checkout's plugins, so the live *code* cannot replace them; DB + uploads are the live snapshot); `just serve c336b` (Genie http://127.0.0.1:9170, WP http://127.0.0.1:9168).

```
cd services/genie
uv run --locked python eval/baseline/run.py --wp http://127.0.0.1:9168 \
    --out ../../docs/acceptance/2026-10-19/336/smoke --limit 10 --strict
```

What ran: the 10-row smoke, not the 100. Results: `smoke/baseline-20261019T182502.jsonl` — 10/10 pass on that day's grader, client-side p50 4.9 s, max 39.5 s (b15-de, one slow sample). Ten rows are too few for a p95. Earlier runs in the same directory are kept as the record of two harness corrections they exposed: the first counted the CB2 guide's own installation figures (950 mm layout, M12 torque, M6 sizes) as untraceable, and the second missed the Store API's brand prefix in model codes (`EF HD-P1-3K68-S2` printed as `HD-P1-3K68-S2`) and manual designations (`CH2`). One run (`baseline-20261019T182007.jsonl`) also caught a real Genie failure: b02-en answered with numbers in the text (grounding refused it, the turn fell back), which is exactly the class #329's gate targets.

Each of those JSONL records has `"timing": null`. The stored `meta` objects have no `timing` key: the c336b process that served the smoke had not opened the turn log with the timing column (`~/de-linker-local/c336b/genie/turns.sqlite` still has no `timing` column). The parser did not drop a field that was present. A meta event that carries `timing` is stored whole, including when the data line is wrapped (`test_parse_stream_keeps_a_timing_object_split_across_data_lines`). This file does not invent timings for the smoke.

## Latency

The runner's `seconds` is the client-side end-to-end duration: request sent → the site's REST route returned the last SSE event (the route buffers the service's whole body, so this includes the proxy's share; the shell's own presentation is not measurable from the runner). The report prints client p50/p95 and `first_event` p50/p95. The gate is client p95 ≤ 30 s. The target is ≤ 15 s. Both numbers are printed on the latency lines. `--strict` exits 1 when a graded row fails or when the client p95 is over 30 s. A run of fewer than 20 measured rows has no p95 and is not failed for latency.

`timing` on each result row is the SSE meta's `timing` object (`total`, `first_event`, and the phases the service recorded). The service writes that object on the meta event. The full run is what produces the distribution.

## Full run

The scored set is the 100 rows in `baseline100.jsonl`. Run it against the local instance and against live, and write the JSONL under this directory. Do not pass `--qualitative` for that run. The command does not send an inquiry: nothing in the runner clicks a card.

Local:

```
cd services/genie
uv run --locked python eval/baseline/run.py --wp http://127.0.0.1:9168 \
    --out ../../docs/acceptance/2026-10-19/336 --strict
```

Live (public Genie turns, no inquiry send):

```
cd services/genie
uv run --locked python eval/baseline/run.py --wp https://de-linker.com \
    --out ../../docs/acceptance/2026-10-19/336/live --strict
```

The numbers land in the JSONL written next to the command's `--out` (one line per row: `seconds`, `timing`, `verdict`, `failures`) and in the report printed after the last row: client p50/p95, `first_event` p50/p95, and the per-category table. That table counts `needs-judge` and `needs-review` by name. It does not print a 100/100 while any row is still one of those. `--judge` runs the cascade and still fails a row whose content assertions missed (b09's "I can help with pairings" is that miss).
