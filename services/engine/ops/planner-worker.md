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

## Bounded routine maintenance

`planner_maintenance.py` is a Mac one-shot caller of these same contracts.
`install_planner_maintenance.py` renders its launchd plist by default; installation
is a separate reviewed deployment using `--install`. No additional VPS service or
collector exists. The existing knowledge-publication schedule remains independent.

The default operational window is **02:00–03:00 UTC**, chosen as a bounded
European overnight maintenance period, rather than a measured capacity claim.
The native launchd job wakes hourly, but outside the window it performs only a
local time check. There is at most one real attempt per UTC day, including busy
or failed attempts; it does not retry within that day or use `KeepAlive`.
The hour/window and 600-second work budget are explicit installer options.
The caller reserves additional bounded time from the selected release's existing
start/stop/drain budgets for paired recovery and cleanup. A second work alarm
must not interrupt the native operator's `finally` recovery.

Before any backup or service action the caller reads the selected namespace,
actual paired readiness, queue state and complete native CAS plan. Busy,
closed-admission and zero-garbage results do not create a recovery point or stop
services. An unavailable source/registry/recovery or network failure remains a
diagnosable outcome. The existing registry's `source.host`/`source.root` must
match; a directory name alone cannot declare a backup's origin.

When work is necessary, reuse the latest independently verified archive's
immutable CAS bytes. A fresh SQLite backup-to-memory and missing CAS bytes travel
under the source's shared CAS lock until the Mac completes native verification,
atomic publish and acknowledgement. An identical complete archive is reused.
There is at most one incoming candidate; a lost publish reply is reconciled
against that verified candidate and the registry before another copy is made.
The owner is persisted for this namespace before any snapshot/staging work;
reuse it across utility-source upgrades rather than generating a daily owner.
Managed archives keep N=3, with explicit database baselines and current recovery
bindings protected. Unknown files and peer evidence are not retirement targets.
Original archives are never edited, and no extra full audit copy is created.

One owner-bound temporary remote root contains independent single-link DB and
manifest files plus immutable source CAS hardlinks. The selected native
`retention SPEC --apply --when-idle --recovery PATH` owns `operator.lock`, rechecks
idle/zero/independent coverage before closing admission, stops and verifies both
writers, recomputes the strict full closure offline, and restores the pair in
`finally`. Removing the temporary root after reliable recovery releases the
remaining hardlinks; only then can physical space be reported. An ambiguous
network outcome is not permission to replay deletion. The next invocation first
resolves the same single owned root against a verified local archive.

Safe events use the existing system syslog with prefix
`linker-planner-maintenance`; stdout is only a foreground convenience. Operators
can read the Mac unified log using that exact prefix. One private
`maintenance-<owner>.json` in the archive root holds the last local check,
last real maintenance result and most recent failure; hourly outside-window and
zero-work checks do not erase the failure. It has no customer data, credentials,
candidate lists, event-history array or user notification. The singleton lock
inode stays with the registry; temporary files and SSH process groups do not.

### Stable Mac deployment inputs

Do not install a plist pointing into a disposable development worktree or keep
its large development environment for this utility. Prepare a small immutable
source at
`~/de-linker-ops/planner-maintenance/releases/<merged-commit>/`, retaining only
current and previous utility sources. It needs engine `src/`, `schemas/`,
`pyproject.toml`, `uv.lock` and the three maintenance/release Python files in
`ops/`; exclude tests, node_modules, vendor, caches and a copied venv. The original
engine `RuntimeSnapshot` does not include these operator files, so this ops-only
change does not require relabelling numerical preparation fixtures.

Reuse the already retained shared interpreter
`~/de-linker-ops/knowledge-worker/releases/1418dc26e14c/.venv/bin/python`
only for dependencies. Its current Pydantic 2.14.0, jsonschema 4.26.0 and Pillow
12.3.0 successfully import this archive/verifier with an explicit engine `src`
path; no environment was created for that check. Deployment must repeat the
actual import from the newly prepared stable utility source before rendering or
installing its plist. The renderer accepts explicit interpreter/runner paths and
sets `PYTHONPATH` to the stable utility `src`, so a shared editable package cannot
select a development checkout. Retain this shared interpreter while either
deployed consumer depends on it; it is not a third utility-source release.

Rendering the plist changes no scheduler. Inspect the exact source, interpreter,
owner, archive root and UTC options before explicit installation. A failed or
interrupted bootstrap is read back: only the exact newly installed argument list
can be unloaded, and its label/process exit must be confirmed before restoring
the prior disk plist. An unknown/foreign loaded definition is left untouched and
reported as unconfirmed. Real scheduler installation, backup, GC and deployed
log/readiness readback are separate rollout acceptance, not local-test claims.

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
