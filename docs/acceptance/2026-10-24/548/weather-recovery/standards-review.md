# Standards review — weather recovery

Base: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664`. Source pin: `704c4fddbe2e4de068f1d9f7fe9fd0ad3f16f914`.

Read every hunk of all 28 changed files and the single commit: leased recovery/CLI, known-run protocol, resume, cleanup, schema/archive changes, remote-aware status, local drain consumer and tests. Applied current main/owned AGENTS, CONTEXT, the isolated-planner exception, engine/local conventions and Fowler judgments. This is the independent serial Standards axis; no Spec report/messages were consulted.

**Two P2 correctness findings under the documented lease/checkpoint boundaries; no additional actionable Fowler smell.**

- **P2 — journal reads precede an already-known revocation.** `services/engine/src/linker_engine/planning/weather_known_run.py:29–30` reads current intent/plan before checking `WeatherTask`. After late start acknowledgement, revoked control plus a SQLite read outage consequently raises `OperationalError` instead of `LeaseLost` through `weather_acquisition.py:178`. This violates the checkpoint-first contract in `weather_task.py:33–39` and the preserved lease-loss boundary asserted by `tests/planning/test_weather_acquisition.py:316`. The completed owner engine run reproduces it. Check the task before constructor journal reads; retain the existing adversarial regression.

- **P2 — abort entry omits the lease fence.** `weather_known_run.py:66–71` refreshes and reads journal state, then starts abort with only `task.elapsed`. Revocation/lease replacement during those journal operations therefore allows the stale recovery job to send the abort POST; `terminal()` notices the loss afterward. Leased recovery is required by `docs/specs/548-weather-acquisition.md:196–214`. Recheck `task.check()` immediately before entering abort, while keeping the elapsed-only response guard for retaining a reply after loss during the request. Add a regression revoking control after refresh/journal observation and require zero abort POSTs.

The remaining seams are coherent by inspection: immutable capture cannot publish a source/result; resume preserves runtime/manifest/deadline/attempts; maintenance survives disabled acquisition; schema migration reuses transactional parent/child preservation; release status uses an actual shared read transaction; the legacy drain proof opens SQLite read-only.

Owner-run evidence at this pin: engine **812 passed/one failed**; scoped local unit checks **92 passed**. Broad local diagnostics retain 26 skips/19 setup errors and the unrelated format failure; they are not green acceptance. No reviewer tests, network, Actors or database/runtime mutations. Native controls, installation credential wiring, paired installation and full-goal/production acceptance remain required. Preserve this pinned report through subsequent corrections.
