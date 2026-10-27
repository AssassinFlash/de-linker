# Standards closure — managed weather integration

Base: `4140663f950999b55fe3c3b5bd0dfff0ebf9049b`. Final source pin: `cf310435d60749b89dd0de182c3bfe8189ef47a6`.

Re-read every hunk of the complete cumulative 31-file diff across both commits (`a2dc8b42`, `cf310435`): context/spec, typed admission, registry/runtime identity, HTTP status/replay, publication, cancellation/cleanup, migration and tests. Applied current main AGENTS, the isolated-planner exception, engine conventions and the stated Fowler baseline. This is an independent serial Standards review; no Spec review or Spec-agent messages were consulted.

**Initial P2 closed. No remaining documented-standard violations or actionable Fowler findings.**

`services/engine/src/linker_engine/planning/weather_status.py:17` now delegates without catching `NotFound`. `WeatherJournal.view` first performs its owned run lookup and returns `not_started` only when the acquisition row is absent and the caller explicitly permits that result (`weather_journal.py:309`). Ownership/retirement denials therefore propagate, preserving the boundary documented in `docs/specs/548-weather-acquisition.md:145–150`.

The regression at `services/engine/tests/planning/test_weather_kernel.py:531` performs an actual guest-project transfer before the second owned lookup, submits the private HTTP status request, and requires HTTP 404 with `not_found`, exactly two lookup calls and zero provider calls. Existing positive coverage still requires `not_started` for an owned queued acquisition. This distinguishes missing data from denied authority without changing strict journal callers.

The cumulative recheck found no regression in frozen-plan/runtime ownership, explicit saved selection, atomic source publication, cancelled-task/cleanup separation, bounded known-run cleanup, transactional migration or archive preservation. The shared metadata projection and registry follow existing module responsibilities.

Owner-run `commands.json` binds all final checks to this exact pin. Read-only stdout/XML inspection confirms **798 tests, zero failures/errors/skips**, plus successful lint, format and strict types. Initial failure evidence and the pre-ownership 797-pass result remain separately retained. No tests were executed by this reviewer.

The initial `standards-review.md` is unchanged. No source, network, Actor, live database/runtime or production actions occurred. Native/operator controls, paired local installation, detailed engineering, site and production/full-goal acceptance remain required and unaccepted here.
