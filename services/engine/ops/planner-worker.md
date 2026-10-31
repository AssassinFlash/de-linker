# Managed planning worker deployment contract

The paired deployment operator is [planner_release.py](planner_release.py).
Its source/configuration and activation contract is in
[548-service-hosting](../../../docs/specs/548-service-hosting.md). It prepares
and controls a dedicated non-root HTTP/worker namespace without restarting the
existing engine or Genie. The [candidate unit](linker-planner-worker.service.in)
remains the standalone template reference. Its systemd semantics are in the
[hosting research](../../../docs/research/2026-10-24-managed-worker/HOSTING.md).
The complete workbench still needs production workload limits, staged site
acceptance and deployment/readback. The existing HTTP service alone does not
execute queued numerical jobs.

Before staging a unit, replace `@RELEASE_PATH@` with the absolute immutable
engine release path whose environment was installed at that location. Replace
`@STOP_BUDGET_SECONDS@` with the measured/approved operator stop budget. The
2-second restart delay is an operational choice inherited from the existing
engine unit; neither it nor the local 30-second drain is a production capacity
claim. Do not point retained workers at `current` or move a virtual environment.
Bind executable, working directory and imported package/source to that release.
Reject unexpanded placeholders, whitespace/control characters in the release
path and nonpositive/nonfinite stop budgets before installing a rendered file.

The private `/etc/linker-planner-worker.env` contains five non-secret settings:
`LINKER_PLANNER_CONFIG`, `LINKER_PLANNER_WORKER_CONFIG`,
`LINKER_PLANNER_RUNTIME_SHA256`, `LINKER_PLANNER_EXECUTION_KEY` and
`LINKER_PLANNER_STORAGE_BINDING`. The two JSON paths must identify the intended
workspace and worker policy. The three hashes must match the authenticated
HTTP `/planning/version` response. Do not supply `INVOCATION_ID`; systemd
generates it. Do not copy service, provider or model credentials into this file.
Distinct retained workers need distinct policy names/readiness paths and unit
names; their execution keys route their tasks within the same compatible store.

For a planned replacement, use the **currently retained executable** and its
configuration to run `python -m linker_engine.planning.worker_host control
drain`. This closes new evaluations transactionally while preserving exact
receipt replay, reads, cancellation and already queued execution. Read `control
status` until pending is zero. A deadline, missing matching executor or a
foreign-version queued task refuses replacement: preserve the executable,
configuration and queue, resolve the missing version, and keep admission closed.
Do not infer queue completion from `systemctl stop` or a clean SIGTERM.

After the queue is drained, keep the prior executable/configuration recoverable
and stage the new matching HTTP and worker. Validate the rendered unit with the
actual host's `systemd-analyze verify` before installation. `Type=exec` proves
invocation only. Read the worker readiness record and verify its live process,
systemd invocation ID, runtime hash, execution key and storage binding against
the new HTTP identity. Exercise an authenticated synthetic queue/result and
lease/cancellation check in the staging environment. Only then use the matching
executable's `control resume` and publish the site's service address.

Unexpected process loss leaves leases durable. Restart the retained matching
release so it can recover its tasks; a new release cannot silently relabel or
calculate an old job. Keep each release/configuration while a pending job needs
its execution key. Schema compatibility and routing tests are prerequisites
for retained releases sharing a store. Rollback likewise uses the previous
executable and matching configuration after a successful drain; never rewrite
frozen request or result bytes to make a version appear compatible.

## Preparation fixture exports

Run the existing exporter from `services/engine` with that host's existing
environment and `PYTHONPATH=src:tests`:

```sh
python -c 'from tests.planning.export_preparation_fixture import rendered; print(rendered(), end="")'
```

An isolated Linux export needs `src/`, `tests/` (including its fixtures),
`schemas/`, `pyproject.toml` and `uv.lock` at their original engine paths.
Its helpers also read exactly these four repository-relative originals:

- `fixtures/planning/geometry-flat.json`
- `docs/research/2026-10-24-pv-generation/raw/berlin-2005-2023-nohorizon.tmy.json`
- `docs/research/2026-10-24-pv-generation/raw/weather-provenance.json`
- `docs/research/2026-10-23-pv-inputs/raw/era5-berlin-2020.seriescalc.json`

Reuse the existing Linux interpreter only for dependencies; ensure imports
resolve to the isolated `src`, rather than installed production code. Keep one
task-owned temporary repository, set its `TMPDIR` inside it, run at nice 19
with numerical library threads set to one and a 60-second exporter deadline.
Terminate and reap the owned process group on timeout/cancellation. Remove the
source package and synthetic SQLite/CAS in `finally`, with caller-side cleanup
and a final absence check. Do not copy a venv or touch live workspaces/services.
