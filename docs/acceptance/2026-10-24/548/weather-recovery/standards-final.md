# Standards closure — weather recovery

Base: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664`. Final source pin: `c1ddef08c34075f1667972a62a95e3a0d2f55a6d`.

Re-read every hunk of the cumulative 28-file diff and all five commits: `704c4fdd`, `dc613c36`, `0969e006`, `7be28fef`, `c1ddef08`. Coverage includes recovery/CLI, shared protocol, resume/cleanup, schema/archive, remote-aware draining, local consumer, context/spec and tests. Applied current main/owned AGENTS, the isolated-planner exception, engine/local conventions and the complete Fowler baseline. Independent serial Standards review; no Spec reports/messages consulted.

**Both initial P2s closed. No remaining documented-standard violation or actionable Fowler finding.**

- **Constructor ordering closed:** `services/engine/src/linker_engine/planning/weather_known_run.py:29` checks the task before reading journal state. An already-revoked control therefore reaches `LeaseLost` before a database outage; the existing adversarial acquisition regression remains intact.
- **Abort entry closed:** the same file at line 70 rechecks current authority after journal reads and immediately before abort. The elapsed-only guard remains inside the request to preserve a late reply. `tests/planning/test_weather_reconciliation.py:318` expires and reclaims the actual SQLite lease after observation, requires `LeaseLost`, permits only one GET, and preserves the replacement's running job with no abort/source publication.

The acknowledgement change retains the verified effective INPUT's original bytes and server-owned submitted input as explicit successful-job dependencies. Validation precedes retention. The FAILED/ABORTED cases at `test_weather_reconciliation.py:187` assert exact bytes, no capture/owned asset, unchanged failed producer, backup/restore fidelity and failure when a referenced INPUT child is removed. Existing archive verification also covers receipt-only dependencies.

No cumulative regression found in storage binding/idempotency, preserved resume budgets, disabled-feature maintenance, migration preservation, shared-snapshot remote status or legacy read-only drain proof. Documentation now distinguishes restoration of the retained schema-2 worker from installation of the new runtime, consistent with retained owner readbacks.

Completed owner evidence reports 814 engine passes at `0969e006` and 92 local unit passes for unchanged local code. Final-pin full-engine completion is not asserted here. Initial failed/broad diagnostic evidence remains separate. No reviewer tests, network, Actors, database/runtime mutations or implementation edits. Original report unchanged. Native UI/credential wiring, paired installation and full-goal/production acceptance remain required.
