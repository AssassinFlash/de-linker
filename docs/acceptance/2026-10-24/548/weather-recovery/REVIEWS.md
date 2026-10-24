# Independent weather recovery reviews

Base: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664`.
Final source: `c1ddef08c34075f1667972a62a95e3a0d2f55a6d`.

Both axes independently reviewed every hunk of the cumulative 28-file diff and
all five source commits. Reviews ran serially because only one reviewer slot
was available; an attempted concurrent follow-up was rejected by the agent
thread limit. Neither axis consulted the other axis's report. Reviewers did not
run tests, use external sources or modify the runtime; owner test evidence is
separate. No parallel-review or production-acceptance claim is made.

| Axis | Initial source/verdict | Corrections | Final open findings |
| --- | --- | --- | --- |
| Standards | `704c4fdd`, two P2s | `dc613c36` constructor ordering; `0969e006` abort entry fence | 0 |
| Spec | `7be28fef`, one P2 | `c1ddef08` exact verified INPUT dependencies and archive regressions | 0 |

The original reports `standards-review.md` and `spec-review.md` remain intact.
Final reports below are reproduced from their independent closure files. The
Standards reviewer deliberately does not certify the final full test run;
`engine-commands.json` and the JUnit report independently record all 816 passes
at the final source pin, zero errors/failures/skips, lint/format165/types127.
The local 92-pass unit result remains at its actual source pin, with unchanged
local code hashes. Native/credential/paired-install/full-goal gates remain open.

## Standards

Base: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664`. Final source pin: `c1ddef08c34075f1667972a62a95e3a0d2f55a6d`.

Re-read every hunk of the cumulative 28-file diff and all five commits: `704c4fdd`, `dc613c36`, `0969e006`, `7be28fef`, `c1ddef08`. Coverage includes recovery/CLI, shared protocol, resume/cleanup, schema/archive, remote-aware draining, local consumer, context/spec and tests. Applied current main/owned AGENTS, the isolated-planner exception, engine/local conventions and the complete Fowler baseline. Independent serial Standards review; no Spec reports/messages consulted.

**Both initial P2s closed. No remaining documented-standard violation or actionable Fowler finding.**

- **Constructor ordering closed:** `services/engine/src/linker_engine/planning/weather_known_run.py:29` checks the task before reading journal state. An already-revoked control therefore reaches `LeaseLost` before a database outage; the existing adversarial acquisition regression remains intact.
- **Abort entry closed:** the same file at line 70 rechecks current authority after journal reads and immediately before abort. The elapsed-only guard remains inside the request to preserve a late reply. `tests/planning/test_weather_reconciliation.py:318` expires and reclaims the actual SQLite lease after observation, requires `LeaseLost`, permits only one GET, and preserves the replacement's running job with no abort/source publication.

The acknowledgement change retains the verified effective INPUT's original bytes and server-owned submitted input as explicit successful-job dependencies. Validation precedes retention. The FAILED/ABORTED cases at `test_weather_reconciliation.py:187` assert exact bytes, no capture/owned asset, unchanged failed producer, backup/restore fidelity and failure when a referenced INPUT child is removed. Existing archive verification also covers receipt-only dependencies.

No cumulative regression found in storage binding/idempotency, preserved resume budgets, disabled-feature maintenance, migration preservation, shared-snapshot remote status or legacy read-only drain proof. Documentation now distinguishes restoration of the retained schema-2 worker from installation of the new runtime, consistent with retained owner readbacks.

Completed owner evidence reports 814 engine passes at `0969e006` and 92 local unit passes for unchanged local code. Final-pin full-engine completion is not asserted here. Initial failed/broad diagnostic evidence remains separate. No reviewer tests, network, Actors, database/runtime mutations or implementation edits. Original report unchanged. Native UI/credential wiring, paired installation and full-goal/production acceptance remain required.

## Spec

**PASS for the scoped backend increment. The original P2 finding is closed; no new scoped Spec findings.**

Both refs resolve. Reviewed the complete 28-file cumulative diff `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664...c1ddef08c34075f1667972a62a95e3a0d2f55a6d` and all five commits: `704c4fdd`, `dc613c36`, `0969e006`, `7be28fef`, `c1ddef08`. Applied current main `AGENTS.md`, `CONTEXT.md`, weather-acquisition/managed-energy-worker specifications and relevant project/PV/private-hosting contracts. The original `spec-review.md` remains unchanged.

The requirement “Recovery outputs retain their exact evidence dependencies under that job” (`548-weather-acquisition.md:222`), clarified at lines 227–230 for acknowledgement INPUT, is now satisfied. `weather_reconciliation.py:77–85` retains the exact bytes returned by the validated `verified_input` call and the canonical server-owned submission; line 102 places both hashes directly in the successful job output's dependencies. The effective response is checked against the pinned safe full INPUT before retention, preserving its original whitespace without accepting arbitrary provider fields. Archive verification already checks job-output dependencies, so this evidence participates in backup validation and restoration without requiring a weather capture.

The new parametrized FAILED/ABORTED regression source exercises actual queued maintenance with simulated provider responses, exact whitespace-preserved INPUT, no capture or owned assets, retained original failure, archive restoration and rejection of a backup missing referenced INPUT bytes. This review inspected those tests; it did not execute them or independently certify the separately reported test counts.

No remaining missing/partial scoped requirement, unrequested scope creep or incorrectly implemented scoped behavior identified. Rechecked private admission/replay, finite budgets, producer-state restrictions, lease fences, separate evidence publication, matching-runtime resume, schema migration and remote-aware draining.

Native customer controls, actual-installation APIFY credential wiring, EN/DE 1440/390 proof, paired schema-4 installation/rollback and the full 548 goal remain open. The documentation correctly distinguishes the uninstalled new runtime from restoration of the absent old schema-2 worker, whose process identity changed. No Standards reports, external requests, Actors or live runtime/database actions were used in this review.

Final counts: Standards 0 open findings; Spec 0 open findings. The three initial P2s are closed.
