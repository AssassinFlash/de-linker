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
    facts and hosted source versions feed a versioned capability contract;
    a fixed-efficiency scenario replay is not SKU qualification. Search
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
