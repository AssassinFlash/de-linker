# Unified workbench application contract

Date: 2026-10-23. The owner has approved the Journal dashboard direction,
authorised a modern isolated application and explicitly required the whole
software workflow to be considered beyond 3D. This contract composes the
existing workspace, time-series, energy, PVGIS and private identity contracts;
it does not replace them or reduce the end-to-end delivery under map #548.

The adopted capability inventory is
[`CAPABILITY-MAP.md`](../research/2026-10-23-modern-workbench/CAPABILITY-MAP.md),
W01–W22. Its evidence labels distinguish observed operation, fixed source,
official descriptions and our integration design. A library's presence or a
competitor's screenshot is not evidence that this application works.

## Product and data boundaries

1. One application and one project contain site facts, source assets, design,
   operating scenarios, equipment candidates, comparisons and deliverables.
   Roof design is optional. Residential, commercial and industrial projects,
   installers, existing PV and storage-only paths use this same authority;
   project type guides input without arbitrarily disabling roof capability.
2. Input sections and source assets are versioned. Raw bytes, units,
   measurement points, time conventions, coordinate references, assumptions,
   rights and quality are explicit. Upload, parse success and fitness for a
   particular calculation are separate states. Missing information is not 0.
3. Location/country/rule-set/timezone are independent of interface language.
   European scope must be implemented through actual data and qualification
   rules, including applicability and source versions. Interface support is
   not a grid, structural, fire, mounting or equipment release. Missing
   evidence remains an implementation/research obligation within this goal.

## Editing, saving and restoration

4. Four kinds of state are separate: temporary interaction state (selection,
   camera, drag preview); an editable document with command history; a draft
   based on a named confirmed server revision; and remote query/cache state.
   A Query cache hit is neither a saved project nor a valid engineering run.
5. Map, plan, 3D, object tree and property forms edit the same object IDs and
   metric geometry. Camera movement does not create an input revision. Drag
   previews commit one undoable command, with numeric/keyboard alternatives.
   Quantities come from actual included objects, not independent UI counters.
6. Saving carries the expected confirmed revision and one durable intent key.
   Retry after an unknown acknowledgement reuses the exact snapshot/key.
   Acknowledging an older in-flight snapshot does not overwrite newer local
   edits or mark them saved. Conflict preserves the local document and shows
   the competing version; no silent last-writer-wins merge is allowed.
7. Undo/redo affect the editable document, preserve old runs and invalidate
   redo after a new branch. Draft recovery carries its baseline revision,
   acknowledgement and pending intent. It is scoped to the verified session;
   login/logout/account switching cannot expose another identity's draft.
   Native project files preserve effective inputs and declared source rights;
   import rejects unsupported versions and never silently applies new defaults.
   Unknown creation intents use separate immutable scope/UUID records; two
   tabs cannot overwrite one another. Recovery lists the verified scope's
   pending creations for explicit selection/retry of the original bytes.
   Local storage upgrades preserve existing drafts and report invalid data;
   resource ceilings never silently evict an uncertain intent. Login cannot
   automatically resubmit an old guest intent as a new account mutation.

## Tasks, scenarios and results

8. Server task/artefact contracts declare their input dependencies, source
   hashes, model/runtime, parameters, outputs and reuse conditions. Geometry,
   layout, near shading, PV conversion, electrical constraints, dispatch,
   candidate qualification and reporting form an explicit dependency graph.
   Editing a load does not needlessly rerun unchanged geometry; a roof change
   must invalidate every dependent result. Unknown dependency coverage cannot
   authorise reuse. Historical results retain their original identity.
9. Progress reports durable task state. Leaving a page or aborting a fetch
   does not cancel a worker; cancellation needs an acknowledged server command.
   Pause/resume may be offered only with an actual durable checkpoint/restart
   implementation. A running browser animation is not calculation progress.
10. A scenario pins effective input, equipment topology, operating conditions
    and run references. Comparison checks weather, measurement boundary,
    timestep/reconstruction, model and initial/terminal conditions before
    presenting differences. Unequal conditions and unresolved requirements
    stay visible. Old output cannot be relabelled as the current calculation.
11. Equipment qualification precedes ranking and includes applicable modes,
    ports, limits, accessories, conditions, country and evidence. Real Woo
    product records are the sole maintenance authority for product facts,
    publication, document associations and their source versions. The existing
    publication manifest, engineering feed and preparation contracts supply
    the versioned capability projection; no independent product list,
    hand-entered capability pack or per-tool source is introduced. Missing
    product evidence is diagnosed against that Woo source and its preparation
    state before any change is proposed. A fixed-efficiency scenario replay
    is not SKU qualification. Search
    exhaustion, infeasibility, unresolved evidence and out-of-scope differ.
12. Summaries, detailed time windows, tables and exports use the same frozen
    result. Charts label units and resolution; display reduction cannot
    change the calculation or conceal peak failures. Undefined ratios have
    reasons. Lighting/shadow rendering is separate from geometric shading,
    irradiance and electrical-loss methods.

## Delivery, site integration and runtime

13. Screen report, PDF, parts list and engineering handoff carry the same
    project/revision/run/candidate and evidence. Non-saleable engineering
    components remain distinct from Woo products. Transfer to Solution draft
    or inquiry rechecks current product/account/stock rules, presents changes
    and obtains a real idempotent receipt without rewriting the old run.
14. WordPress owns native identity; a durable login transition claims and
    retires the verified guest, including in-flight requests. Genie and team
    readers use authorised current or explicitly selected historical results.
    No browser Actor or copied cart-session field grants project ownership.
15. Homepage, navigation, content/product links, old deep links, account,
    draft/inquiry/Proforma, language routes, SEO, consent and analytics are
    consumers of this change and must be updated and verified in this goal.
    Private projects/reports are not public indexing surfaces. Analytics
    permission does not control access to the design tool.
16. The isolated modern runtime follows
    [`0002-isolated-planner-runtime.md`](../adr/0002-isolated-planner-runtime.md).
    React Query manages server state and request signals; it does not replace
    domain history, server idempotency or worker cancellation. Ajv checks the
    declared wire schema without coercion/defaults. ECharts supplies result
    exploration with independent accessible tables. Map/3D/large result views
    load on demand. Site tokens and WindPress remain the style authority.
17. App-only modernisation must preserve other site runtimes. Tests cover
    lifecycle/resource disposal, unsupported GPU/map recovery, responsive
    interaction, keyboard/screen-reader paths and measured performance using
    actual project sizes. Data retention, backup/restore, schema/model
    upgrades and draining old service processes are real operational paths.

## Completion and implementation order

Build and verify four complete vertical paths: A native project/intake/save/
recovery; B synchronized editing/constraints/history/scenario branching;
C frozen linked calculations/qualification/comparison; D reports and every
site consumer through migration, review site, deployment and production readback.
Each path needs actual execution, both independent review axes and applicable
EN/DE × 1440/390 Computer Use evidence. Path boundaries organise implementation;
none is the completed tool. The overall goal stays active until all required
paths and site consequences pass, with no post-delivery follow-up debt.

## Shared Woo integration and collaboration handoff

Owner correction, 2026-10-25: consult the existing product-data work before
changing equipment inputs. The conversation “将 EcoFlow 产品下架为草稿”
has already delivered the shared product/publication/knowledge preparation
chain. Its contracts are [current publication](614-publication-contract.md),
[engineering consumption](617-publication-engine.md), and the explicit
[new-workbench integration boundary](618-planner-publication-alignment.md).
The old feed in this worktree is not evidence that current Woo maintenance
is missing product facts. Published permission, prepared evidence and model
applicability must be inspected separately.

This workstream integrates those existing contracts with its permanent
project/revision/run/candidate identities. It retains all candidate and
document dependencies, validates current permission before and after new
operations, preserves historical snapshots, and checks the complete set again
at report and Woo handoff boundaries. Derived typed values remain rebuildable
from Woo-maintained records and documents. They create no second editable
product authority.

The module intake consumes the current shared Woo reference projection. Its
dimensions, STC power, temperature coefficient, document bytes/page and
canonical product revision populate a selection form; customers do not enter
those product facts or document checksums. `ModuleSource.woo` is an optional
backward-compatible saved identity, not a maintenance surface. New/edited
module facts and newly prepared PV parameters must match the current approved,
prepared Woo record. Unchanged historical projects remain readable and editable
in their other fields. Exact completed command receipts replay privately even
after a source is withdrawn; they grant no new calculation.

PV preparation freezes a reference-only Woo proof in its context and validates
it before computation and before publishing its owned profile. Energy replay
of such a profile rechecks the same proof around execution. The numerical model
continues using its frozen inputs. Current source changes return a named
`product_evidence_changed` refusal; a new command rejected before writing does
not strand a frozen client intent or pretend to be a project-version conflict.
The deployment host and worker always enable the source policy; direct pure
algorithm fixtures have a distinct execution key and cannot enter that worker.
This binds the maintained module facts; it does not approve equipment pairings,
country rules or the remaining downstream report/handoff operations.

### Equipment evidence and proposed-topology task

The new `/runs/equipment` task is owned, revision-bound and idempotent through
the same permanent command receipt and worker registry. `equipment_selection`
contains selected Woo IDs and their exact current product revisions, physical
module/stack counts, accessory IDs, phase, operating mode and project demand
requirements. It contains no manufacturer limits or customer-editable product
facts. A changed or withdrawn selected product rejects a new command with
`product_evidence_changed`; completed private receipts still replay.

The task freezes the whole loaded/current/prepared candidate pool, its document
associations and the shared publication-filtered compatibility contract. It
checks current permission before and after worker evaluation. It uses no legacy
capacity ratios, postcode assumptions or old residential/commercial selection
function. Proposed configurations are assessed before ranking. The separate automatic search below enumerates the currently implemented
documented topology domain. Full-system topology expansion and ranking after
qualification remain in the same overall implementation.

Equipment needs figure projection version 2. The Woo producer preserves
`qualifier`, `evidence_refs`, explicit `columns` and existing language values;
an old feed which discarded them cannot be accepted by this task. The compiler
retains raw keys/values/units and current product/document revisions, source
bytes SHA, physical page and figure hash. SI-prefix conversion follows the
stored unit: active kW and apparent kVA stay distinct. Maximum and continuous
values, module/system energy and operating/fault current are never merged.

Ordered values remain table columns. Mapping to a module count requires
explicit Woo-maintained column labels; matching array length and ascending
numbers are insufficient evidence. A disjoint battery/converter voltage window
is violated; a partly overlapping window remains unresolved for usable energy.
A scalar whole-system window needs an explicit fixed-count fit. Free-text
conditions are retained as unresolved conditions, never approved by a regex or
language-model guess. A missing manufacturer listing is not proof of physical
incompatibility. Required accessories use current unambiguous Woo identities
and their documented per-system/stack/unit quantity basis.

A `sales_unit_kind` figure, cited and maintained in the same Woo product, is
required before converting an internal pack count into a saleable SKU count.
The compiler does not infer that a cabinet SKU is one pack because one figure
describes its internal module. Known conditional energy figures cannot become
unconditional capacity. Missing sales-unit identity keeps that BOM line
unresolved. No substitute capability pack is introduced.

Each result contains satisfied/violated/unresolved checks, the source facts,
manufacturer conditions and a provisional parts list. A successful task is
not an approved system. Detailed string/port/continuous battery conversion,
mode/transfer, integrated topology and country requirements remain explicit
unresolved checks until their corresponding models and current source facts
are implemented. The proposed-topology task alone never grants the final
country-qualified report, complete-BOM or commerce-handoff state. This is an
increment of path C, not completion of the full workbench or a scope reduction.

The owner has authorised notifying the collaborating conversation after the
shared integration is actually connected and verified. That handoff must name
the interfaces, source/runtime versions, relevant readback and remaining
integration responsibilities so the other work can continue. Keep this handoff
pending until those facts exist; importing shared code alone does not satisfy it.

### Automatic equipment search and candidate selection

Compatibility declarations are maintained on native Woo products, alongside
their cited document identities and revisions. The feed carries the shared
`compatibility_origin: "woocommerce"` projection and canonical product IDs;
new equipment commands require that projection. The former static contract is
an explicit one-time migration input only. It is not a runtime fallback or a
second maintenance source. Historical frozen results retain their original
evidence.

`/runs/equipment-search` uses the same revision-bound command journal, owned
worker, Woo preparation, pinned whole-product pool and before/after authority
checks as proposed-equipment checking. `equipment_requirements` holds only
project phase, mode, installed-array STC rating (kWp), required usable energy
and required continuous AC discharge power. Saved drafts can retain unprepared
settings; execution rejects requirements that differ from the current saved
settings. Search availability is explicitly advertised by the configured
service. The deployment supplies an operational work budget; it is never a
physical limit or an infeasibility claim.

The implemented template is one converter with one external battery assembly,
or no battery when both storage demands are explicitly zero. Current
manufacturer-listed pairings, intersected documented module-count bounds and
unambiguous required components generate selections. No missing count,
parallel capability, sales-unit identity or manufacturer condition is invented.
The same assessment function checks every selection. A single external
assembly does not require evidence for inter-assembly parallel operation.
Wp/kWp are PV nameplate quantities, distinct from continuous active AC power;
an unlabeled active-power field cannot establish an installed STC array limit.
Meter requirements apply even when no battery is chosen, and included
components retain their manufacturer conditions and document links.

The result distinguishes exhausted supported domain, unresolved evidence,
violated requirements and an unfinished search caused by its work budget. It
records its domain, omitted topology types, source gaps and every generated
selection. Canonical product/count order is a display order, not a performance
ranking. Country and remaining topology obligations continue to prevent a
fully qualified result; this increment cannot claim global search exhaustion,
optimality, complete engineering release or final BOM coverage.

Candidate checks are immutable. Common fact blobs are stored once and candidate
assessments refer to them, avoiding repeated large evidence payloads.
`/equipment/candidates/read` accepts a run and candidate identity, verifies
private run ownership and membership, and reassembles the stored checks without
fetching current products or recomputing a historical assessment.

Applying a candidate rechecks its exact Woo product revisions. It preserves
unrelated project edits and refuses a late application over changed equipment
settings. Current project demand is preserved. When the prepared selection
exactly matches the saved candidate, `equipment_candidate` binds its run,
candidate and assessment hash; project writes verify ownership, same-project
lineage and exact selection. Changed demand instead requires a new assessment
and is not relabelled as the old candidate. This binding is available for the
remaining report, BOM and commerce consumers.

### Frozen planning report and private PDF

`runs/report` uses the existing durable command journal, executor registry and
atomic asset publication. It accepts explicit completed energy/PV/equipment run
references plus locale and optional PNG/JPEG branding. Source runs must belong
to the project and match the relevant saved inputs; the adopted equipment
candidate remains bound to its original run and assessment hash. This command
does not recalculate weather, PV or energy and does not choose a different
historical analysis by a latest-result heuristic.

PV module quantities use the retained producer input/witness, its included
layout object identities and the matching Woo module/document proof. The
energy-only shared-DC report includes only its selected PV conversion group;
an explicitly selected complete PV result defines the complete saved PV-model
scope. The list preserves source revision, source document and STC rating.
Excluded slots and unconsumed groups do not become quantities. An absent layout
or missing Woo binding has an explicit unavailable state; counts are never
inferred from area, kWp or an editable current layout. These design-reference
modules stay separate from the sale-product list used by Woo draft transfer.

The report freezes project identity/revision, selected analysis references,
equipment checks and source documents. Each distinct current Woo permission
proof is checked at source capture and before/after rendering. Proofs and source
results are referenced by their existing content hashes; this does not create
another maintained product source or duplicate whole-product snapshots.
When the selected energy run already binds equipment and no separate equipment
analysis is selected, its frozen assessment and quantities supply the report's
equipment list and existing Woo handoff. The exact consumed Woo proof remains
the authority; report generation performs no new equipment calculation or
latest-product selection. Explicit separate analyses retain their existing
selection checks. Scenario-specific checks remain in their dedicated report
section and are not duplicated among the general equipment sections.
Screen and PDF consume one Report model, with a shared model hash. Only the
successful worker transaction publishes the owned PDF asset and result.
Existing receipts and generated files remain privately readable as history.

The generic Report schema and ReportLab renderer are reused; older sizing and
report assembly are not called. The new PDF supplies its actual source wording
instead of inheriting HTW/GeoNames credits for methods it does not use. Numeric
display rounding does not change the frozen source result. User-provided logos
are bounded by the existing 500 kB policy and image decoder checks.

This report presents the actual coverage of its selected analyses. Explicit
scenario energy remains distinct from selected-hardware performance; equipment
and country gaps remain open. Its provisional equipment list is not represented
as a complete installation BOM. Completing remaining engineering/country
constraints, hardware-coupled energy, the full BOM/report, comparison and all
commerce/site consumers remains part of the same full delivery goal.

For reports using a historical PV-derived energy profile, unrelated feed or
compatibility revisions may renew current permission only when the entire
frozen Woo module document (including facts, citations and product revision)
is identical to the current Woo module document. The old proof remains pinned
in the report source alongside the current permission proof. Changed module
facts or citations require a new matching result; numerical results are never
rewritten during permission renewal.


### Native draft and inquiry transfer

An owned completed report supplies an immutable handoff, using the existing
workspace handoff table and command receipts. It freezes the exact project,
revision, report/candidate, selected sale-product quantities, consumed Woo
permission scopes and private PDF hash. Preparing that record does not claim
current product eligibility or complete-system qualification. Different preview
keys reuse the same immutable report handoff; login recovery inherits the
original command through the existing verified guest claim.

Woo remains the writer and current publication/account/stock authority. Its
native cart is previewed before explicit confirmation. The preview shows the
old/new quantities of this project's group; the confirmed write replaces only
that group and preserves unrelated/manual products. A native cart fingerprint
refuses stale previews. The existing all-or-nothing cart writer performs the
actual write; native session content and its idempotent acknowledgement commit
together. An uncertain result retains the exact captured browser intent.
Read-only receipt discovery may confirm that result without resubmitting it.
Acknowledged browser intents are cleared; the native Woo receipt remains the
recovery authority for the session's native lifetime. No parallel product
registry, cart, report calculator or email sender is introduced.

Native Woo item metadata carries the report reference into the order. Inquiry
preparation resolves those order-line references against the trusted native
session before assessment/notification preparation and byte admission; missing
context refuses the inquiry. It does not depend on the cart still containing
those lines. Original planned quantities
and actual inquiry quantities remain distinct, with a visible change notice.
The native order retains a compact, checksummed reference (project/revision,
original handoff hash, report/PDF identities and selected quantities); the full
report and Woo evidence remain in the immutable planner record. This respects
the native HPOS `orders_meta.meta_value` TEXT limit of 65,535 bytes. A larger
encoded reference refuses submission before saving instead of silently losing
it. The actual native-read diagnosis found the earlier full 138,128-byte record
was refused with no database error. Private download resolves the original
handoff again and requires exact equality with the saved compact reference
before reading its PDF; a copied or changed reference cannot choose another
asset.
Current Woo permission is checked again before inquiry admission. Order-owner,
staff or the native inquiry key grants only that inquiry's non-priced report;
it does not grant project ownership/editing. The protected download selects a
server-stored PDF asset and verifies its hash, using the existing private
transport and a server-only team reader. Historical report downloads do not
recalculate or requalify a withdrawn product.

Native-first boundary: Woo's cart validation, order-line hooks, session storage,
translated page pairing and existing LC/Woo rendering surfaces carry the work.
They do not resolve an external owned planning run or keep its cross-service
receipt; the narrow Tools/Commerce bridge provides only that missing data
assembly. New fragments are semantic data with inherited tokens, with no new
page template, inline style, CSS channel or production mail test.

### Roof-object string wiring and cited electrical checks

The equipment task accepts an optional `pv_string_plan`: selected inverter ID,
unique string IDs, MPPT/project input labels, actual included module IDs, lowest
design ambient temperature and its stated source. No device specification is
entered by the customer. The task freezes a separate reference-only Woo proof
inside its existing sales-pool proof and confirms both around worker execution.
The reference fact compiler does not manufacture a sale SKU or device class.

Checks cover complete module assignment, the assigned STC nameplate, MPPT count,
allowed strings per MPPT, cold Voc against inverter and cited module DC/IEC limits,
and STC MPP/current/short-circuit limits. Parallel currents add by MPPT; series
modules affect voltage. Unequal string lengths or orientations remain unresolved.
String allowance does not establish physical connector count: input labels retain
an explicit outstanding manufacturer-map check. Hot/cold operating MPP, design
irradiance/rating rules, cables/connectors/protection and country release remain
separate obligations, never a pass inferred from STC or a typical weather year.

The same frozen wiring table, temperature/source, units, checks and citations
appear on screen and in the EN/DE report/PDF. A changed roof or string plan rejects
an old electrical assessment at report generation; export requires the retained
roof-source export permissions. Existing equipment tasks without a wiring plan,
energy replay, old reports and sales handoff quantities retain their prior scope.
The batch closes after one cited wiring representative and its failure boundaries,
changed-file type/lint/build checks, independent delta reviews and affected native
save → equipment task → report/PDF views. Unchanged physics/commerce evidence is
reused; no annual energy replay or full-site matrix is added.

### Cited compound I–V model and operating cases

Optional `pv_string_plan.operating_conditions` retains effective irradiance,
hot/cold cell temperatures and their project/mounting basis, with nulls allowed
while a project is being developed. No site extreme or mounting coefficient is
filled in. The original minimum ambient temperature remains a separate cold-Voc
input. Module operating-temperature limits and cold≤hot are checked explicitly.

The exact cited Woo STC Voc/Isc/Vmpp/Impp and Voc/Isc temperature coefficients,
plus a cited crystalline-cell basis, feed the public pvlib Batzelis estimator.
All five initial values then seed public De Soto refinement. The library's
required initialization argument is a numerical surrogate only; all five seeds
are overridden, no physical cell-series count is inferred, and the fit retains
its numerical settings, model assumptions and runtime identity. Acceptance
requires finite physical parameters, residual checks and STC curve readback;
solver success alone cannot authorize estimates. Details and primary sources
are in NUMERICAL-MODELS.md §14. The pinned API floor is pvlib0.16.1; no dependency
environment or unrelated runtime is added.

Hot/cold MPP estimates are compared with the cited MPPT window at the explicitly
stated uniform effective irradiance and cell temperatures. Model current sums
require equal parallel string length/orientation; short-circuit points stay
distinct. These are named operating cases, not all-weather maxima, shading
simulations, a protection design or manufacturer/country qualification. Fit
precision does not become physical accuracy. Source gamma and NOCT are held-out
diagnostics: differences, source cell-temperature interval and reference
irradiance are visible, without a fabricated pass tolerance or factory stamp.

The frozen result carries the model parameters/input facts, points, assumptions,
numerical residual/tolerance and diagnostics. Screen and EN/DE PDF consume that
same object; small diode currents retain scientific notation. Sources link to
the maintained documents and versioned method references. Missing inputs,
unadmissible fit or out-of-domain conditions retain the independent cold-Voc/STC
results with named unresolved/violated checks. Legacy v1 saved results remain
readable; optional operating output has an explicit v2 method tag.

This batch reuses prior saved energy and handoff/source-policy evidence. Its
verification is one existing wiring representative extended for the new model,
known false-success/negative-resistance rejection, domain/optional-schema checks,
necessary changed-layer type/build checks, independent delta reviews and the
new native operating/report views. No annual replay or full-site matrix repeats.


## Canonical site entry and carried requests

The existing `/solution-configurator/` and `/de/loesungskonfigurator/` pages
render `[linker_planner]`. Saved `[linker_configurator]` content delegates to
that same native application; it never enqueues a second configurator bundle.
The independent review pages remain local acceptance routes, not the site's
customer destinations. Existing navigation, content and Genie sizing links
therefore reach the unified application without creating a new public URL.

Historical sizing parameters are unverified customer inputs for a new project.
The new-project form previews valid PV kWp, annual kWh, grid phase, backup and
postal code and allows their exclusion before an explicit create action.
Duplicate/invalid values are diagnosed and never applied. They cannot modify
an existing project, select products, authorize compatibility or start a run.
Annual demand is marked as an estimate with its carried-link source. Postal
code does not imply a country, coordinates or timezone. Accessory permission
is retained as a project note, not a manufacturer approval. Existing durable
creation intents retain their original bytes and scope before any link input.

`step=roof` opens the same project's roof section, including after a new project
is created. A normal creation opens site inputs. Consumed parameters leave the
project URL; language navigation carries only validated link inputs before
creation and the owned project/result/section references afterward.
