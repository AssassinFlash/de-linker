# #336 part B — 100-question baseline + grading harness (smoke)

Campaign #329. Ticket #336 asks for the 20-question comparison set (`docs/research/2026-10-17-knocket/TRIAL.md`) expanded to 100 questions, scored by the trial's口径, repeatable.

## What is in the repository

| Path | What |
|---|---|
| `services/genie/eval/baseline/baseline100.jsonl` | 100 rows, EN/DE pairs, 10 categories. Smoke slice first (map #329 hard rows: trials 1, 8, 10, 14), then slots in id order. Trials 6 and 19 replaced slots b20 and b25, so documents is 14 rows and sizing and price are 8. |
| `services/genie/eval/baseline/grade.py` | The trial's口径 as pure functions: product hit (cards/compare/citation vs the target's Store API catalogue), traceable numbers, next step, no fallback / no sales@ on hard rows, price-gate sentence off the card, page citation, forbidden words (AGENTS.md §3), EN/DE parity in the set check. |
| `services/genie/eval/baseline/run.py` | Runner: one real turn per row through `POST /wp-json/linker-ai/v1/genie/turn` (the bubble's own route), captures meta + blocks + seconds, writes JSONL, prints score per category/lang. `--limit`, `--only`, `--lang`, `--category`, `--judge` (jev → deepseek-flash cascade), `--strict`. |
| `services/genie/tests/test_baseline.py` | 33 tests: composition, all 20 trial seeds, hard-row presence, EN/DE structure, every expected product id in the catalogue fixture, grading unit tests (fallback, deflection, numbers, price gate, page citation, language, trials 6 and 19). |

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

## Smoke run (local instance c336b, live snapshot, this checkout's code)

`just up c336b`; `just pull load c336b latest` (the instance runs the checkout's plugins, so the live *code* cannot replace them; DB + uploads are the live snapshot); `just serve c336b` (Genie http://127.0.0.1:9170, WP http://127.0.0.1:9168).

```
cd services/genie
uv run --locked python eval/baseline/run.py --wp http://127.0.0.1:9168 \
    --out ../../docs/acceptance/2026-10-19/336/smoke --limit 10 --strict
```

Results: `smoke/baseline-20261019T182502.jsonl` — 10/10 pass, client-side p50 4.9 s, max 39.5 s (b15-de, one slow sample; p95 needs the full 100-row run). Earlier runs in the same directory are kept as the record of two harness corrections they exposed: the first counted the CB2 guide's own installation figures (950 mm layout, M12 torque, M6 sizes) as untraceable, and the second missed the Store API's brand prefix in model codes (`EF HD-P1-3K68-S2` printed as `HD-P1-3K68-S2`) and manual designations (`CH2`). One run (`baseline-20261019T182007.jsonl`) also caught a real Genie failure: b02-en answered with numbers in the text (grounding refused it, the turn fell back), which is exactly the class #329's gate targets.

## Latency

The runner's `seconds` is the client-side end-to-end duration: request sent → the site's REST route returned the last SSE event (the route buffers the service's whole body, so this includes the proxy's share; the shell's own presentation is not measurable from the runner). Each record also carries `timing`, the service's per-turn phase breakdown from the SSE `meta` when it exists (the latency instrumentation PR); the report prints the client-side p50/p95 as the gate number (map #329: p95 ≤ 30 s, target ≤ 15 s) and the service phases as the breakdown beside it.

## Not in this PR

The full baseline (100 rows against live and local, with first-token and p50/p95 latency) runs after the latency instrumentation PR merges; this PR ships the set, the grading and the runner, and the 10-row smoke proof.
