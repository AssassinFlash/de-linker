# #336 part B — 100-question baseline + grading harness (smoke)

Campaign #329. Ticket #336 asks for the 20-question comparison set (`docs/research/2026-10-17-knocket/TRIAL.md`) expanded to 100 questions, scored by the trial's口径, repeatable.

## What is in the repository

| Path | What |
|---|---|
| `services/genie/eval/baseline/baseline100.jsonl` | 100 rows: 10 categories × 5 slots × EN/DE. Smoke slice first (map #329 hard rows: trials 1, 8, 10, 14), then slots in id order. |
| `services/genie/eval/baseline/grade.py` | The trial's口径 as pure functions: product hit (cards/compare/citation vs the target's Store API catalogue), traceable numbers, next step, no fallback / no sales@ on hard rows, price-gate sentence off the card, page citation, forbidden words (AGENTS.md §3), EN/DE parity in the set check. |
| `services/genie/eval/baseline/run.py` | Runner: one real turn per row through `POST /wp-json/linker-ai/v1/genie/turn` (the bubble's own route), captures meta + blocks + seconds, writes JSONL, prints score per category/lang. `--limit`, `--only`, `--lang`, `--category`, `--judge` (jev → deepseek-flash cascade), `--strict`. |
| `services/genie/tests/test_baseline.py` | 29 tests: composition, hard-row presence, EN/DE structure, every expected product id in the catalogue fixture, grading unit tests (fallback, deflection, numbers, price gate, page citation, language). |

The rows also reuse the existing sets' data conventions: `services/genie/index/eval/golden.jsonl` (document facts and the model codes), `services/genie/eval/knowledge/questions.json` (the #257 document floor), `services/genie/eval/page/questions.json` (page contexts and IDs), `services/genie/eval/contact/cases.json` (contact reasons), and `plugins/linker-commerce/data/compatibility.json` (pairing verdicts).

## Set composition

| Category | EN | DE |
|---|---|---|
| product-match (incl. trial 1, 8) | 5 | 5 |
| pairing | 5 | 5 |
| documents (incl. trial 10) | 5 | 5 |
| sizing (incl. trial 14) | 5 | 5 |
| price | 5 | 5 |
| inquiry | 5 | 5 |
| handoff | 5 | 5 |
| company-logistics | 5 | 5 |
| smalltalk | 5 | 5 |
| page-awareness | 5 | 5 |

Assertion split: 82 deterministic, 16 judge (reference answer points + the jev → deepseek-flash cascade), 2 human-review (polite closes).

Trial rows carried as twins: 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20. The map's hard four (1/8/10/14) are `hard: true` and carry `no_handoff` (no handoff block, no sales@de-linker.com in the text).

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
