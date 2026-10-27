# Unified planner: source-pinned energy evaluation job

2026-10-23. This increment connects permanent owned assets, the reviewed time
and continuous-energy components, and the real durable Worker. It remains one
component of the active full European residential/commercial planner delivery.
It is not mounted as a public HTTP API and does not release actual equipment,
country compliance, PV/weather or geometry by itself.

## Intake and source authority

1. Project assets have opaque IDs and immutable content/metadata hashes. Every
   read, byte read, import, receipt and asset binding checks its project scope.
   A verified team reader cannot import into an owner's project. Concurrent
   identical imports produce one receipt/asset; a changed command conflicts.
2. Permanent CAS accepts only sources declared for permanent private retention,
   with label, fact basis and retention-rights basis. Temporary provider data
   is rejected rather than entering indefinite backups. The separate compliant
   provider cache/lifecycle required by MAP-ADAPTER.md remains in the same full
   implementation scope; this is not authority to omit maps/automatic roofs.
3. CSV intake validates the actual original bytes and explicit mapping. It
   captures the exact installed TZif once, preserving source origin, measurement,
   units, timestamp conventions, resolution and interpretation. Retry identity
   covers the user's original command, not recaptured OS data; an acknowledged
   import returns its first pinned asset after timezone updates or removal.
4. Child dependencies are explicitly declared in server-owned asset metadata
   and evaluation results. Intake/publication verifies their bytes. Online
   backup verifies children even for imported profiles never evaluated, and
   checks the referenced replay artifact before publishing a restorable backup.

## Frozen scenario and execution

5. Strict versioned JSON rejects unknown fields, string numbers, wrong types,
   missing units/measurement/mode/initial-source assumptions, and nonfinite
   values. Battery parameters are explicitly marked scenario parameters of the
   single-AC model; no hidden nominal SKU defaults or equipment release exist.
6. The server, not browser JSON, resolves project-owned profile/battery assets,
   source metadata/TZif, runtime bundle, named models and explicit numerical/
   resource settings into Context. The worker binds manifest to durable run,
   revision and input hash, and every dependency to the immutable selected asset
   IDs in that project; another existing hash is not a substitute for that ID.
7. Runtime capture contains actual planning source bytes, uv lock/pyproject,
   Python, platform/libc/machine, SQLite and Pydantic identities. Publishing must
   use immutable executable releases retained with their runtime bundles. This
   worker rejects a different runtime/model/settings; it does not reinterpret
   an old queued run with latest code. Historical result reads never recalculate.
8. The client evaluation intent is kind + expected revision + idempotency key.
   Server-resolved runtime settings/attempt policy are frozen on first receipt,
   not a changed user command on retry after a deployment/settings update.
9. Schedule intervals are explicit, real-time and continuous. All native profile
   and operating boundaries form a union within the requested horizon. Each
   connected block uses gross load; each outage block needs its critical-load
   profile. PV availability and AC auxiliaries retain their distinct identities.
   Missing coverage is an error. Refinement retains native/effective resolution
   and the constant-mean assumption; it cannot certify new measurement peaks.
10. Registered Worker executes actual profile interpretation, replay, independent
    verification and metrics with cooperative cancellation checkpoints and final
    durable publication fencing. Computation does not run under the write lock.
    A resource limit is explicit runtime policy, never silently coarser data.

## Output and verification

11. Execution success and scenario constraints are separate. A completed replay
    can have violated constraints. Result/trace retain project/revision/input/
    manifest/runtime hashes, model, source/mapping/timezone/transformations,
    verification residuals/allowances/witness intervals and scoped metrics.
    Equipment and country assessments remain explicitly not assessed by this
    handler; consumers must not turn a scenario pass into engineering release.
12. A private content-addressed replay artifact preserves every actual frame,
    command, source inventory and flow with unit-suffixed fields. Its dependency
    is included in the frozen result/backup verification. Old input edits cannot
    rewrite it; missing/tampered pinned bytes fail by name, without zero fill.

Nineteen real SQLite/file/Worker tests cover the analytic two-hour energy case
(4 kWh load, 3.62 solar-load kWh, .38 grid kWh at .9/.9), historical input edits,
reopen, actual backup/restore replay, no installed OS timezone during execution,
half-hour operating boundaries over native hourly means, critical/gross scope,
wrong runtime/model, missing bytes, same-command retries after server policy
changes, foreign/wrong asset IDs, net-import substitution, explicit resource
limits, concurrent import, team read-only authority and incomplete child backup.
Fixtures are synthetic and identified as such. They are not European weather,
manufacturer capability, production performance or UI acceptance evidence.
