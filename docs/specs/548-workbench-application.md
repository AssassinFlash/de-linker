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
function. Proposed configurations are assessed before ranking. Automatic
candidate search and ranking remain part of the overall implementation; this
task does not claim to have implemented them.

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
