# Managed preparation of a project-bound PV profile

This extends the same complete workbench delivery. The existing explicit
roof/weather model becomes a real durable task, with trusted weather acquisition
and native source/task controls. A reference scenario still does not replace
detailed shading, electrical models, released equipment or country assessment.

## Task and source authority

Use the existing project, immutable revision, run, lease, cancellation and
history authority. Numerical PV generation must not execute in an HTTP request.
The command identifies the saved project revision and an idempotency key;
the server resolves model choices, resources and owned source dependencies.
Provider URLs, capture assertions, actor/build IDs and credentials are never
browser-selected authority.

Trusted TMY intake verifies the actual original response and capture against
the declared versioned request and interpretation before retaining an owned
weather asset. Preserve acquisition IDs/build, original bytes, units, both
time axes, provider/database attribution and permanent-retention basis. An
already captured exact weather source may be reused without another fetch.
Fresh external acquisition uses Apify as required by the owner, with explicit
build/resource/retry policy and no ordinary-search/direct-fetch bypass.
Indeterminate external start outcomes must not silently create repeated runs.

The PV task freezes the selected owned weather content/metadata, the exact
saved geometry/model parameters, runtime and operational settings. It reads
only those dependencies, generates the actual complete reference profile and
retains model input/witness bytes. A later project edit cannot alter it.
Profile preview projects the retained values and interval axis from hash-verified
artifacts without running the physical model again. A numerical worker still
reproduces the reference from its frozen original when using it in a calculation.

## Publication and multiple numerical tasks

A prepared profile becomes an owned project asset in the same transaction
that publishes the successful task result. Cancellation, expiry or a stale
worker must publish neither the result nor an owned-asset row. Immutable
unreferenced bytes from an interrupted attempt are distinct from publication.
An acknowledged completion is idempotent; a changed completion conflicts.
Project ownership transfer keeps the asset with its project, not the former
session. Another project's asset cannot be attached by a worker result.

The worker must support both actual energy and PV-preparation executors.
Execution routing remains exact: only registered runtime/model/settings keys
can be claimed, including after a routing-cache rebuild. A worker's capability
identity covers its complete registered executor set; HTTP and process startup
must agree on that identity and the same storage. A newest worker cannot spend
attempts on work belonging to a different executable or operational policy.
An evaluation dispatcher selects a registered executor from the verified
immutable manifest; the browser cannot register code or choose arbitrary keys.

## Native and operational acceptance

The workbench must distinguish source preparation from energy calculations,
retain confirmed task identity across refresh/language changes, and expose
queued/running/retry/success/failure/cancel/history states. A prepared profile
is selected into the draft explicitly and saved through the existing revision
mechanism; completing a background task cannot overwrite edits or silently
replace a chosen source. Source/model choices need clear units and provenance;
test-fixture values must not become manufacturer parameters or hidden defaults.

Verification uses real SQLite/CAS, the production Worker, actual source bytes
and independently checked physical cases. Cover shared publication atomicity,
cancel/expiry/concurrent completion, different project/owner, identical command
retry, complete-year PV-to-energy reuse, mixed executor routing, cache repair,
startup capability mismatch, actual provider capture and EN/DE at 1440/390.
Only the stages actually exercised are accepted; native/provider/production
proof cannot be inferred from a passing backend fixture.

## Implementation checkpoints within this same goal

The current backend increment implements retained, trusted TMY intake,
`pv_preparation.weather_asset_id` selection, private `/runs/pv` enqueue/receipt,
the frozen numerical executor, atomic owned-profile publication and the shared
energy/PV worker registry. `RuntimeConfig.pv_preparation` explicitly supplies
the resource limits to enable the extra executor; existing installed energy
policies remain readable. Private version/worker readiness/CLI identity all
cover the registered set. Native WordPress/browser projection is unchanged.

This checkpoint does not implement fresh external acquisition or its durable
start/recovery journal, nor the native model/source/task controls. Those are
required stages of this specification and full goal, not deferred follow-up
tickets or implied existing features. Their acquired primary contract and
actual component/thermal facts are in
`research/2026-10-24-pv-managed-intake/FINDINGS.md`. The running p548 instance
must retain its accepted version until the paired workflow is ready for a
controlled install and native acceptance.
