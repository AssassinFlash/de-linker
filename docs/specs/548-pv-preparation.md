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
Provider URLs, capture assertions and credentials are never
browser-selected authority.

Trusted TMY intake verifies the actual original response and capture against
the declared versioned request and interpretation before retaining an owned
weather asset. Preserve acquisition IDs/build, original bytes, units, both
time axes, provider/database attribution and permanent-retention basis. An
already captured exact weather source may be reused without another fetch.
Fresh customer acquisition uses the official JRC HTTPS API under the typed
weather request and independent runtime resource policy. The owner clarified
that Apify is exclusively an R&D research tool, so its account, token, Actor,
Dataset and billing cannot be customer-product dependencies. R&D-acquired
originals remain valid research/import evidence with their actual provenance.

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

## Retained-source direct-beam geometry witness

The optional `prepare_direct_beam_visibility_v1` executor is a separate
geometric calculation. Its saved `inputs.direct_beam_visibility` document
contains schema version 1, an owned `weather_asset_id`, strictly increasing
`row_indices`, and explicit coarse/fine equal-area midpoint grid sizes. The
fine grid must have more cells per module edge. There is no hidden physical
sampling default; the observed difference between grids is not an error bound.
The generated `direct-beam.schema.json` is the browser input contract.

`pv_string_links_direct_beam_visibility_v1` is the cumulative complete-input
writer token for these inputs and the existing PV string links. A client that
only understands the previous token cannot silently remove retained visibility
settings during a complete-input save. Omitting the additive option preserves
old command and report receipt hashes.

Owned `weather/assets` and `weather/preview` provide bounded source navigation;
preview reads retained originals without requesting new provider data or
running solar geometry. Synthetic interval boundaries, original TMY source
labels and actual irradiance instants remain separate axes. The selected asset
must match the saved acquisition request and interpretation. The task is
admitted through `runs/direct-beam` with the usual saved revision and command
key; an exact receipt replay acknowledges its original run before fresh Woo
source reads. It does not grant permission for a new calculation.

The worker resolves the owned asset, pins the original bytes, metadata,
canonical weather selection, geometry, current Woo module basis and executable
identity, and uses the source's irradiance instants for solar position. An AABB
BVH supplies candidates to the existing exact face intersections. Included
module volumes, declared opaque extrusions and roof surfaces can occlude a
receiver; only the receiving module itself is excluded. Non-opaque keepouts
do not become blockers. Current source and Woo permissions are checked again
after calculation, and the ordinary worker lease fences result publication.

`RuntimeConfig.direct_beam_visibility` conditionally enables this executor and
requires explicit weather limits. Its five operational limits are selected-row,
sample, exact ray-face and BVH-bound checks, and index leaf size; these are CPU
policies, not engineering tolerances. The private version and native browser
bootstrap expose the same model and resource limits. Existing policies without
this optional service remain usable.

The result retains frozen geometry for the table/3D overlay and may be selected
separately as `ReportOptions.direct_beam_run_id`. Reports, PDFs and bounded
Genie facts consume the same saved witness and hash-bound dependencies without
recalculating weather, visibility or PV generation. They keep owner, revision,
time-axis and current source-permission checks. Night and back-facing/tangent
modules have no reported geometric fraction. The result is not published as a
power profile and cannot be adopted into the energy replay as a loss factor.

This increment establishes selected-time geometric visibility only. It does
not model diffuse/reflected irradiance, partial-shading electrical mismatch,
bypass diodes, actual MPPT, annual shading loss or a complete equipment/country
assessment. The existing unshaded PV reference and equipment replay retain
their declared scopes. The next complete numerical chain must explicitly bind
a separately versioned irradiance/electrical model to the same geometry and
weather axes, preserve direct/sky/ground contributions separately, produce a
reproducible power-profile witness, and pass that owned profile through the
existing PV publication and energy/report consumers. A small set of selected
visibility rows cannot stand in for the complete time series or establish a
manufacturer performance curve.

## Full-axis direct-only geometric PV reference scenario

The separate model `opaque_direct_uniform_pvlib_reference_v1` uses every row of
one retained owned TMY source. Its executor is
`prepare_geometric_pv_reference_v1`, its native command is `runs/geometric-pv`,
and its published AC asset purpose is `geometric_pv_reference_profile_v1`.
The existing unshaded reference keeps its model identity and unchanged
no-geometry-factor calculation path. This model consumes the established ray
geometry and pvlib component/thermal/conversion methods described in
`research/2026-10-23-modern-workbench/CAPABILITY-MAP.md` section 8 and
`research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md` sections 4–5.

`inputs.geometric_pv_preparation` explicitly records the weather asset, coarse
and fine sampling, the existing full reference-coefficient document, and three
required policies: `retain_unobstructed_sky_and_ground_components_v1`,
`sapm_from_module_mean_poa_v1`, and
`uniform_module_pvwatts_independent_mpp_sum_v1`. These are scenario choices,
not extracted manufacturer circuit or mounting facts. The cumulative writer
token `pv_string_links_direct_beam_geometric_pv_v1` covers this field plus the
previous PV-string and diagnostic-visibility fields. Previous tokens keep
their original meanings and cannot erase retained new inputs.

For each actual included module and weather irradiance instant, the model
calculates the fine-grid direct-beam geometric fraction and retains the
coarse/fine difference and night/back-facing state. That fraction attenuates
only direct POA. The unoccluded sky and ground POA remain separate and
unchanged. SAPM uses the resulting mean total POA for the module's cell
temperature; PVWatts treats its effective irradiance as uniform across that
module. Modules sum to their actual array, then the already declared shared
converter model applies once. The result is an AC reference; an AC asset is
not accepted as a DC source. Module-source identity and temperature
coefficient still come through the current Woo reference authority.

Every source row produces an output interval under the existing explicit
representative-output reconstruction policy. Original TMY selected-month
irradiance instants drive solar geometry; the synthetic year defines the
energy interval axis. The selected source months, source databases, complete
PV calculation period and any separate energy operating period retain those
different meanings in reports and Genie source facts. No selected-row
interpolation, provider refetch or hidden conversion to measured generation
is performed.

`RuntimeConfig.geometric_pv_generation` independently enables the executor and
contains explicit module-step, sample, exact face-check, BVH bounds-check and
index-leaf policies. Its weather parsing is bounded by the existing explicit
PV weather policy. The diagnostic 24-row limit is not reused. Requested
coarse/fine sample work is checked conservatively over the complete axis;
actual intersection counters are independently bounded. Exceeding policy
fails the whole task, with no partially published profile. Cancellation is
checked throughout the source-row and module loops.

For a horizontal module's actual sample points, the full-axis worker may
prove an upward ray clear using the same outward scene bounds and negative
travel tolerance as the ordinary index. The proof is charged to the bounds
budget and includes every opaque surface other than that receiving module;
when it is unavailable or the direction is outside its safe range, the
original per-sample intersection path remains authoritative. Proven-clear
samples are still counted individually. The worker spells its private final
witness in place and keeps its original canonical JSON bytes and CAS format.
Large frozen witnesses can be read as a hash-verified projection that validates
each module independently; the series CSV retains its module fields and row
order, while legacy full-witness readers and old frozen reports remain valid.
Cancellation is checked during module spelling, projected-module reads and
CSV interval export. These optimizations do not change deployment limits or
authorize a larger production workload; the bounded scale results and the
remaining deployment-resource decision are recorded in the existing #548
acceptance index.

Admission freezes owner/revision, original weather and metadata, current Woo
basis and runtime. The worker checks source and Woo permissions again after
generation; the ordinary lease transaction publishes the profile only with
the successful run. The immutable asset manifest binds exact original project
parameters, normalized numerical inputs, numerical witness, original weather,
metadata and Woo basis. Reads verify those hashes, complete time axis,
interpretation and output energy without rerunning solar, geometry, thermal or
PV physics. A fresh energy calculation also checks the selected asset against
the saved geometry/parameters. Old-command acknowledgment remains possible
before fresh source permission checks and grants no new permission.

The existing AC profile selection, preview, energy, report/PDF and comparison
consumers recognize this new purpose. `pv_run_id` may explicitly select the
new preparation run. Frozen report references and bounded Genie facts keep
model scope and source periods, omit coordinates/provider URLs/private notes,
and retain current Woo permission checks for new consumers. This closes the
named scenario's calculation-to-profile seam, not the complete W12 goal:
obstructed diffuse light, cell/sub-string/bypass circuits, string I–V and real
MPPT, actual hardware operating performance, full shading precision and
equipment/country qualification remain outside this model.
