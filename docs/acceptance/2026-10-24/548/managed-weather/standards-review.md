# Standards review — managed weather integration

Base: `4140663f950999b55fe3c3b5bd0dfff0ebf9049b`. Source pin: `a2dc8b4260fc5c6e73fe9acf3e8cdfe7944cfb2a`.

Reviewed every hunk of all 31 changed files: context/spec, typed admission, shared registry/runtime identity, HTTP status/replay, managed source publication, cancellation/cleanup, schema migration and tests. Applied current main AGENTS, the isolated-planner exception, engine conventions and documented ownership/source boundaries. No tests, network, Actor, database or live-runtime actions were performed.

**One finding; worst severity P2.**

- **P2 — an ownership denial becomes a false status.** `services/engine/src/linker_engine/planning/weather_status.py:17–24` catches every `NotFound` from `WeatherJournal.view`. That method first calls `workspace.run(actor, run_id)` again (`weather_journal.py:310`), which can deny a transferred/retired guest. If transfer commits after the first owned lookup at `weather_status.py:12` but before this second lookup, that explicit denial is caught and returned as HTTP 200 with `acquisition_state="not_started"`, even when acquisition evidence exists. This conflicts with the owned-status/not-found boundary in `docs/specs/548-weather-acquisition.md:145–150` and conflates missing domain data with failed authority. Have one owned journal/status operation distinguish an absent acquisition row explicitly; propagate ownership `NotFound`. Add a regression that transfers/retires the guest between the current two lookups.

No additional actionable Fowler judgment. The feature services follow existing repository seams; shared weather metadata removes the import/acquisition duplication. The nonempty migration preserves/rebuilds the referencing child with its parent under the existing immediate transaction and enabled foreign keys; tests cover post-DROP rollback and old-archive restore. Prepared-source publication remains fenced and atomic with evaluation success. Cleanup cannot publish a source/result into the cancelled evaluation, and its tests exercise unique admission, rollback, terminal reconciliation and archive preservation.

Retained final output reports 797 passes; the prior 796-pass/one-failure version assertion remains separately identified under `initial-checks`. These are owner-run results, not reviewer execution. Native controls/recovery, paired live installation and full-goal/production acceptance remain outside this review. This report remains pinned if subsequent corrections are made.
