# Managed weather acquisition: backend checkpoint

Source: `cf310435d60749b89dd0de182c3bfe8189ef47a6`, compared with
`4140663f950999b55fe3c3b5bd0dfff0ebf9049b`. This is a 31-file cumulative
source change in the existing unified-planner branch. Exact file hashes and
both source commits are in [source-pin.json](source-pin.json).

This continues the complete unified-workbench goal. It proves managed backend
execution and its integration boundaries; it does not claim native weather
controls, operator recovery commands, a live installation, or production
acceptance. The system-wide product identity and its prior native evidence
remain described in [the energy-workspace record](../energy-workspace/VALIDATION.md).
Provider credits do not stand in for Linker's contribution to the whole system.

## Implemented behavior

- Saved weather choices contain a typed official request and its declared time
  interpretation. Actor/build, credentials, headers and resource limits remain
  deployment policy. Private HTTP freezes the exact project revision, plan and
  runtime before queuing; it does not call the provider or calculate PV.
- The existing registry now supplies energy, PV and weather consistently to
  HTTP, worker startup and identity. The actual installed transport, numerical
  and geospatial library versions contribute to runtime identity. A worker with
  a changed identity leaves old work unclaimed.
- The managed weather kernel reuses the durable acquisition module and strict
  original-TMY interpretation. Capture, metadata and dependencies are retained
  before atomic owned-source publication with successful evaluation. Crashes,
  replaced leases, cancellation and failed publication cannot publish a source.
  A replacement can publish an already retained capture without another Actor
  start, including after the acquisition network deadline.
- Completion leaves saved project inputs intact. Selection uses an explicit
  saved revision. When acquisition choices exist, a selected source must match
  their exact request and time interpretation; a location/year/horizon change
  cannot silently retain an incompatible selection. The existing PV task then
  consumes this source and produces the 8,760-hour input used by energy flow.
- Status distinguishes original task, provider observations, capture and
  cleanup. Disabled acquisition does not erase owned history or prevent receipt
  replay. Guest ownership transfer preserves records and enforces the existing
  not-found response for the former owner.
- Cancellation admits one `abort_weather` job in the same transaction. It uses
  the existing leased queue and the producer's attempt budget, including when
  the producer is inactive or waiting to retry. Repeated cancellation neither
  resets nor cancels cleanup. The cleanup reads the same acknowledged remote
  run, retains actual abort/terminal observations and cannot publish assets,
  change the cancelled evaluation result, or start an Actor. Unknown remote
  starts fail visibly pending verified recovery; ABORTING is not ABORTED.

## Actual verification

[commands.json](commands.json) binds the final commands to the exact source pin.
Lint passed; format checked **156 files**; strict types checked **119 source
files**. The complete engine suite passed **798 tests**, with zero failures,
errors or skips, including **22 new integration/migration cases**. Raw output
and independent JUnit counts are retained in [engine-tests.stdout.txt](engine-tests.stdout.txt)
and [engine-tests.xml](engine-tests.xml).

Tests use real SQLite/CAS and private HTTP. They cover atomic publication and
rollback, stale-source rejection, historical completion, cancellation between
capture and commit, replacement leases, guest transfer, receipt replay and
disabled-policy history. One regression performs a real guest claim between
the two status ownership reads; the former guest must receive HTTP 404 rather
than `not_started`.

An actual independent `worker_host` process runs against the fixture workspace,
finishes a retained weather capture, executes energy work, and consumes the
explicitly selected source in PV preparation. The child has no Apify token and
therefore demonstrates recovery from retained bytes rather than new network
acquisition. Its process is stopped by the fixture. Cancellation cases exercise
the real leased cleanup worker, inactive producers, an abort/finish race,
already-terminal runs, lost abort acknowledgement, unknown-start failure and
backup/restore of cleanup dependencies.

Provider HTTP responses in this increment are **simulated**. The original TMY
bytes and earlier real external capture are retained; this increment starts
**zero Actors** and makes no new external acquisition claim. The prior real
transport evidence remains in [weather-transport](../weather-transport/VALIDATION.md).

## Schema and release boundary

Core schema 3 adds the cleanup job kind. Real nonempty schema-2 fixtures retain
queue IDs, leases, attempts, routing rows, receipts and references on migration;
the existing schema-1 archive test also restores into the current schema.
Foreign keys stay enabled during migration. A failure injected after dropping
the old parent rolls back schema and all records. Old archives are verified
before restoring and migrate only in their new destination.

This requires a **paired code/database release and rollback**. Before an actual
install, close writes, drain compute and cleanup, verify the prior matching
code/database recovery point, then migrate and read back. An old schema-2
executable is not a code-only rollback after migration. Uncertain remote starts
need explicit operator reconciliation; a local failed job does not prove the
remote operation never started.

[preservation.json](preservation.json) is a fresh read-only check: all **164**
baseline project rows are unchanged; the workspace still contains **165**
projects including the prior synthetic scenario. The protected roof project
remains saved revision **14**, with the same input hash. Runtime policy,
readiness identity and all four actual worker identity arguments match the
previous readback. The live database is still **schema 2** and has no weather
acquisition table. No new instance, worktree or full backup was created, and
no live code or database migration was performed.

## Corrections and remaining full-goal work

The first full run retained **796 passes and one failure**: an older archive test
still expected schema 2 after the explicit schema-3 change. That expectation
was corrected, and the next full run passed **797**. Its raw logs are preserved
in [pre-ownership-fix-checks](pre-ownership-fix-checks/commands.json); the failed
run remains in [initial-checks](initial-checks/commands.json). Neither is relabelled
as the final 798-test result.

The independent Standards review then identified the ownership/status error.
The narrow correction and regression are the second source commit; initial
and final review reports remain separately retained in [REVIEWS.md](REVIEWS.md).
[legacy-and-marker-audit.json](legacy-and-marker-audit.json) records the complete
changed-source search scope and zero legacy-identifier, unfinished-marker or
Apify-secret pattern findings. It supplements independent structural review.

Native source/model entry, explicit selection and recovery interactions,
operator recovery operations, EN/DE at 1440/390, and the paired local install
remain required next within this same goal. Detailed shading/electrical
calculation, actual equipment/country coverage, BOM/report/PDF, site entries,
Genie/Woo/Solution draft/inquiry, migration and production readback also remain
required. This checkpoint does not narrow those obligations.

Progress was recorded on the existing [unified-workbench map](https://github.com/AssassinFlash/de-linker/issues/548#issuecomment-6381577608).
[map-readback.json](map-readback.json) verifies the exact comment and the targeted
frontier replacement; all other map content, including the whole-system Linker
identity and complete delivery scope, was preserved. Both temporary request
files were deleted after the readback.
