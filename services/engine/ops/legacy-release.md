# Legacy Engine reader release

`legacy_release.py` publishes only `linker-engine.service`. Run the reviewed
operator from the exact merged Git checkout after CI and the coordinated VPS
write window. It does not deploy the dedicated Planner, publish Woo data, claim
knowledge jobs, or restart Genie. `linker-cutover services --run` is retired;
Genie's `release.sh`/`activate.sh` reject managed Engine/Genie roots.

## Resource and source contract

Owner: the release operator responsible for this window. The local source tar
and Git batch output exist only in memory; no new checkout, disk archive or SSH
master is created. Git source comes from one `cat-file --batch`, verified against
`ls-tree` blob IDs. All tracked runtime inputs in `src`, `schemas`, **`data`**,
`ops`, `.python-version`, `pyproject.toml` and `uv.lock` are included. The seven
tracked geo/roof/imagery/HTW data originals therefore belong to the same immutable
Git identity. `status` reports their selected absolute paths and actual/Git IDs.

The remote root retains current + previous, at most one prepared unselected
candidate, and explicitly protected interpreter dependencies. Unknown existing
directories and contents are preserved and reported. The previous pytest
interpreter must be explicitly protected for this migration. The stable feed,
cache, customer data and worker remain outside release directories.

Prepare builds at the final path with `uv sync --locked --no-dev`; it never
selects a directory before its environment and native probe succeed. Each final
path has a nonce owner marker before unpacking. One private PREPARING journal
permits interrupted preparation to be reclaimed on the next prepare, only when
unselected, unpublished, unreferenced and containing proven source/build inputs.
Unknown or changed input blocks cleanup and preserves the journal for inspection.
Same-name/same-Git preparation reuses its directory. Another candidate name is
refused until the pending candidate is explicitly discarded. A published
current/previous directory cannot be discarded. Prune retains the pending
candidate, current, previous and persisted protections; it never deletes unknown
releases for space. It requires the new reader and a real successful timer pass.

Each command owns and reaps its subprocess group (30 seconds by default, locked
build 240 seconds, remote controller 480 seconds). Reader connection startup is
bounded to 45 seconds; an answered version/coverage/geo/process mismatch fails
once. Feed-worker drain is bounded to 90 seconds. Local fixture resources use a
single `linker-legacy-reader-*` temporary root, loopback server and owned child,
all closed/reaped/deleted on exit. Source/runbook/tests remain as the reviewed
implementation; no test payload or runtime resource is retained.

## Preconditions and commands

Required: local Python 3.10+, `git`, SSH authentication for `linker-services`;
remote Python 3.10+, `/root/.local/bin/uv`, systemd, native `busctl`, root access
to `/proc` and the existing root. The private existing environment file must
contain the actual service token/feed/compatibility/cache configuration. No
credentials are arguments or output. Ambient `APIFY_*` names are removed from
child environments; such investigation-only names in the systemd environment
file are rejected before deployment. Other needed values are preserved.

Read the current selector, service executable/cwd/version, feed/coverage, geo,
worker/timer and disk space before choosing the unique candidate name. Preserve
this readback and the actual old Git SHA in the existing release record. The
legacy predecessor may have **no source manifest**: prepare verifies its exact
Git content without modifying its files or modes. Never manufacture a receipt
inside that old runtime.

```sh
# From the clean, merged checkout; substitute exact reviewed source and name.
REPO=/absolute/path/to/clean/merged/checkout
REV=<full-merged-commit>
NAME=<unique-YYYYmmddTHHMMSSffffffZ-shortsha>
OLD=20261101T043648659112Z-90e9a5691
OP="$REPO/services/engine/ops/legacy_release.py"

python3 "$OP" status --host linker-services
python3 "$OP" prepare --host linker-services --repository "$REPO" \
  --revision "$REV" \
  --previous-revision 90e9a569156eade01ab7b0d40b94eda1e8f6476c \
  --name "$NAME" --expected-current "$OLD" \
  --protect 20261030T170107737048Z=Linux-fixture-pytest-interpreter
python3 "$OP" activate --host linker-services \
  --name "$NAME" --expected-current "$OLD"
python3 "$OP" verify --host linker-services --wait-worker-seconds 180
python3 "$OP" status --host linker-services
python3 "$OP" prune --host linker-services
```

The displayed OLD and predecessor SHA describe the migration baseline recorded
on 2026-11-01; re-read both before an actual later window. `archive` also verifies
that this operator's bytes equal its Git blob at REV. A dirty or different
operator cannot dispatch a release under that identity.

Activation verifies service selector binding and the stable worker's actual
`PROBE_PYTHON`, quiesces the original timer, drains the worker and obtains its
native publication lock. It re-probes the actual prior reader, then the
candidate against its prepare receipt before stopping Engine. Feed/coverage
changes during the build fail before that stop. The selector replacement is
atomic; only Engine is restarted. Loaded resource version, source/compatibility,
prepared-product coverage, geo and actual service PID/cwd must match. The
original timer state is restored on exit.

`verify --wait-worker-seconds 180` observes a natural timer pass; it does not
start the worker. Timer ticks come from D-Bus `LastTriggerUSecMonotonic` as a raw
uint64, since `systemctl show` formats this property as a duration. The worker's
start/exit must belong to that tick and finish successfully. Loaded identity is
read again before setting `worker_verified`; a stale worker success cannot
permit prune. If the bound expires, inspect and repeat verify for the same
release, with no new candidate or forced timer run.

Install any same-batch stable `ops/sync-feed.py` and installed unit changes using
the established [publication instructions](PUBLICATION.md), including actual
namespace/cache preflight and systemd validation. This controller intentionally
does not replace those stable definitions. Coordinate that installation once in
the same window and preserve its existing rollback definitions/log files.

## Failure and interrupted recovery

On ordinary activation failure after Engine stop, the same locked invocation
selects/restarts the prior reader, checks its exact loaded receipt, restores the
timer, and records `restored`. A failed restore remains an error. A broken SSH
reply does not authorize replaying activation: first run `status` and inspect
physical selector, recorded phase and actual process availability.

- If phase is `switching` and the physical selector is the candidate, use
  `verify` on the same state. It checks actual source/loaded identity and restores
  the original timer, including interruption immediately after selector switch.
- If killed while `quiescing`, or between stop and switch, the physical selector
  can still be OLD and Engine can be stopped. Run rollback using that **actual**
  selector as expected-current. This restarts and verifies the old reader and
  restores the timer without manually editing a symlink.
- For a deliberate rollback from the selected candidate, use the same command
  with NAME as freshly inspected expected-current. Rollback re-probes the
  previous runtime against its saved feed/coverage floor and refuses incompatible
  data drift before stopping Engine.

```sh
python3 "$OP" status --host linker-services
python3 "$OP" rollback --host linker-services --expected-current <actual-selector>
python3 "$OP" status --host linker-services
```

If starting the rollback target fails after switching away from the working
current reader, rollback reinstates that reader and checks it, then still returns
failure. If the interruption already left OLD selected and OLD cannot start,
there is no proven running fallback to claim: status reports actual unavailable,
the recovery journal remains, and the original timer state is restored. Diagnose
the reported action/exit code and fix that specific startup cause, then rerun
rollback with freshly read physical selector. Do not claim restored from a link
alone, clear journals, prepare another candidate, or delete either fallback.

A failed/abandoned unselected preparation can be removed explicitly only by its
exact name and reviewed revision; published current/previous and process
references remain protected:

```sh
python3 "$OP" discard --host linker-services --name "$NAME" --revision "$REV"
```

Cleanup checks cwd, executable, open descriptors, command arguments and mapped
files, including deleted mapped files. Explicitly protected pytest interpreters
are retained even with no active PID. Safe errors report phase, action/exit code,
known category and traceback file/line or stderr hash/size; complete stderr,
environment values and credentials are never printed.
