# One metric design document and authoritative layout review

2026-10-23. Implements W02/W03/W05–07 of the existing workbench contract;
the whole A–D delivery remains active. This is a new implementation, not a
copy of the old roof service. Mature patterns and the installed Shapely/GEOS
implementation are recorded in `2026-10-23-design-geometry/`.

The first fixed-source increment covers the wire model, bounded placement,
owned storage and server plan-review service, plus shared browser contracts/
poses and native HTTP acceptance. Editor commands/renderers and their native
visual gates below remain the next composed part of this same delivery. A
service-only PASS does not assert those views or the full B path exist.

1. A project's optional `geometry` is a versioned JSON document. Missing
   geometry remains missing, including storage-only and incomplete projects.
   Roof faces, arrays, obstacles, keepout areas, modules and source records
   have unique stable IDs. Map, 2D, 3D, tree and numerical properties consume
   this document. Camera/hover/selection never change input revisions.
2. Coordinates use local ENU metres with explicit project-relative height and
   north reference. Each roof has an upward orthonormal U/V basis; UV lengths
   are slope lengths. An optional geographic anchor is WGS84 degrees and has
   its own source reference. No anchor is fabricated from a country or UI
   language. Three's renderer transform is `(east, up, -north)`.
3. Source records preserve kind, reference, acquisition time when known,
   spatial precision when known, calibration and separate derivation,
   retention and export claims. User attestations remain claims. An unknown
   precision is null, never inferred from decimal places. Persisting geometry
   requires an explicit permitted retention/derivation claim; a licensed
   dataset additionally needs a referenced licence. This does not establish
   a provider contract or engineering accuracy. Time-limited provider raw
   data must use its separate lifecycle, never this permanent-input route.
4. A strict Pydantic wire model publishes the browser JSON Schema. Extra
   fields, booleans-as-numbers/versions, strings-as-numbers, unsafe URLs,
   duplicate or foreign object/source references, nonfinite/unrepresentable
   coordinates and invalid bases are refused. Resource budgets are explicitly
   application policy, not European building limits. New saves check after
   owned permanent-receipt replay, preserving already-confirmed commands.
   Safe wire inputs may exceed the review/render arithmetic support domain.
   Its binary64 UV granularity budget is1e-9m (internal computational policy,
   not survey accuracy or a fitting epsilon). The checker returns actual
   granularity and its budget. Above it, review is explicitly incomplete with
   a numerical-limit diagnostic; the render-position helper refuses instead
   of returning an inaccurate position. Inputs and receipts are preserved.
5. Euclidean panel placement is deterministic: array/row/column identifies
   each slot; excluded slots retain identity. Every tilted row starts at its
   own lower edge, not on one continuously rising grid. Rotation and actual
   module width/length/thickness drive the same poses and quantity in every
   view. Displayed STC kWp is a declared module sum, not predicted output or
   a qualified sellable product.
6. Authoritative review uses Shapely/GEOS on each roof's local plane. Invalid
   boundaries/holes are reported without repair; holes are not filled. Fit
   uses the whole panel cuboid's projected footprint, including thickness.
   User-supplied roof-edge/obstacle clearances and keepout areas are explicit
   inputs with sources. Null clearance means unspecified, never a default
   country/fire/wind rule. Exact declared boundaries apply without a hidden
   acceptance epsilon or geometry snapping. Edge contact is permitted at
   zero declared clearance; positive-area projected overlap is reported.
   Layout uses roof-local UVN cuboid coordinates directly, without an ENU
   roundtrip or a silent UV-chart translation. Rotation first takes signed
   remainder360, then identical degree-to-radian operations; quadrants are
   exact. Renderers rebase normal supported local coordinates before adding
   large ENU origins. Unsupported UV charts require an explicit coordinate
   reference change, not an assumed first-vertex offset.
7. STRtree bounds candidate checks. Roof fit, openings, obstacle/keepout
   overlap and panel projected overlap are distinct diagnostics with stable
   object IDs. Projection overlap is a conservative plan-layout conflict,
   not a claim of solid-body collision or electrical/shading loss. Obstacles
   use base/top projection; excluded panels do not count or conflict.
   Cross-face collisions and engineering rules remain separate calculations.
8. A bounded private/native review endpoint verifies current project ownership
   before geometry work, accepts the open draft and returns its canonical
   geometry hash, checker/library versions and complete-or-explicitly-limited
   diagnostics. It does not save inputs, create a job, approve a system or
   let browser state choose an owner. Stale replies never label later edits
   checked. Malformed source geometry can be saved as unfinished work if its
   wire document is safe; diagnosed conflicts remain visible on reopening.
9. Tree/property/plan commands are immutable, undoable project edits. Numeric
   fields state units and preserve invalid text until corrected; pointer
   movement is preview only and one completed gesture is one history step.
   Deleting a roof handles dependent objects explicitly; imported source
   bytes are retained independently. A keyboard/numeric path must remain
   usable when GPU, map or third-party consent is unavailable.
10. Acceptance requires independent analytic slope/flat/hole/rotated/tilted/
    thickness fixtures, indexed-vs-brute-force crosschecks, schema identity,
    original receipts, ownership/no-orphan writes, server/browser pose parity,
    actual EN/DE × 1440/390 editing/save/reopen/undo and GPU fallback. Passing
    this contract alone does not close full design, calculation or delivery.

## Physical installation routes

`inputs.installation` is an optional strict schema-v1 project document. Its
shared browser contract is `apps/planner/src/contracts/installation.schema.json`.
Device instances have independent IDs even when they use the same canonical
Woo product ID and revision. Null product identity denotes a site connection.
Names and measured ports are project inputs; manufacturer ratings stay in Woo.
Circuits bind two saved instance/port IDs, paths hold local ENU metre vertices,
and every cable row identifies one physical cable or independently routed
conductor. The project source records remain in `geometry.sources`; a roof and
PV layout are optional. Missing sources can remain editable, with unconfirmed
quantities.

The owned, read-only `installation/review` RPC accepts `schema_version: 1`,
`project_id`, `geometry`, `installation`, and explicit `bind_geometry`. It returns
prepared inputs, the exact geometry hash, individual cable quantities and
reasons. It creates no job or product record. The source-aware native transport
uses the existing source-operation timeout. Current Woo revisions and scoped
publication permissions are checked before returning device identities.

For path vertices p0…pn with known heights, the measured-path length is
`sum(sqrt(dEast² + dNorth² + dHeight²))`. Explicit extra length is added once per
physical cable row and needs its own note; an explicit zero is permitted.
Multicore cable length has no core-count multiplier. Shared path geometry is
measured once, and distinct physical cable rows retain their own quantities.
Unknown height, missing source, mismatched endpoints, stale geometry binding or
missing extra-length basis keeps final quantity null. Existing-source export
permissions are checked independently of missing IDs. Reports additionally
check every displayed instance's source permission.

An explicitly selected routing report may use saved installation inputs without
an energy or equipment run. A mixed report rejects instance counts outside its
selected equipment assessment. The new lines are `installation_requirement`
items in `project_materials_v3`; they are not Woo sales items. Screen, PDF and
`planning_materials_csv_v3` use one frozen material projection; existing v1/v2
exports stay readable. Old report request identities remain unchanged when the
installation option is false. Routing-only reports use their actual scope and
omit empty analysis-reference sections.

Plan and 3D views consume these same positions. Numeric properties remain the
complete input path, and vertex insertion/removal preserves staged values.
Source, instance, circuit and path edits use the existing project history/save
boundary. The installation view survives EN/DE switching. This increment
calculates path lengths; cable specification, protection, earthing, mounting,
connector allocation, multi-device suitability and country qualification remain
separate, unresolved parts of the complete delivery goal. Its native specimen
and frozen exports are recorded in the existing 548 acceptance JSON.


## Multi-system PV strings and physical installation identity

The existing string-to-circuit-to-instance/port mapping already records physical endpoints. Its `linked` status is declared project identity, not manufacturer terminal approval. The missing capability is a plant-level electrical plan: the single-converter plan has globally unique MPPT/input labels and cannot represent two converters that both use MPPT1/input1. A normal equipment plant currently rejects that single-converter plan; it does not silently qualify a multi-converter design.

Add optional `inputs.pv_plant_string_plan` schema v1 with `units: [{unit_id, inverter_instance_id, plan}]`. `unit_id` addresses an existing prepared `equipment_plant.units` entry; `plan` is the unchanged single-converter `PvStringPlan`; `inverter_instance_id` is an explicit existing installation instance or null. This is one relation between a system and the existing physical network, not a second cable/port graph. The old single plan and new plant plan are exclusive. When the new field is absent, old project documents and retained reports keep their existing interpretation and bytes.

Within each unit, MPPT/input pairs are unique. Across the project, unit IDs, string IDs and assigned module IDs are unique. The same MPPT/input labels on different units are valid. Each child inverter product must match its unit selection; all equipment facts and revisions still come from the pinned current Woo basis. Global included-module coverage is checked once. Per-unit limits, STC and declared operating-condition currents use only that unit's strings; no artificial sub-roof or identity-changing geometry is generated. Missing unit plans, removed modules and stale choices remain explicit incomplete conditions, never an implicit reassignment.

Null instance identity leaves physical binding unrecorded while allowing the unit's electrical calculation. A declared binding must match an actual saved installation instance's inverter product and revision; each instance may belong to only one unit. Existing string links continue to identify a circuit. Reconciliation requires the circuit to touch the declared instance exactly once; a different instance of the same product is not equivalent. Ports remain project declarations until a cited manufacturer map establishes physical compatibility. Stale/missing bindings stay editable for recovery and cannot be used as completed installation evidence.

The equipment task pins the real module electrical basis for the plant plan, validates before queueing and re-evaluates against that frozen proof. Existing per-unit assessment consumers retain unit identities. Cached search assessments without roof wiring cannot stand in for a new wiring evaluation: edits clear the adopted candidate in the browser, and the server rejects that candidate-report bypass independently. Report freshness includes the saved roof, plant wiring and applicable instance binding. Frozen screen/PDF/CSV/material outputs share that assessment; historical reports are not recalculated. New installation reconciliation uses an explicit version and `pv_plant_string_plan_sha256`, rather than overloading the old single-plan hash field.

Cross-document recovery is explicit: structural duplicate assignments are rejected on save, while a removed unit, changed product or stale/missing installation instance may remain saved for correction. Installation review returns those stale/unbound states. Equipment evaluation rejects an unknown unit, mismatched selected inverter or an invalid non-null instance binding; a null binding does not block the unit electrical calculation. A unit whose selected PV nameplate is explicitly zero does not need a dummy plan. A positive or unknown PV nameplate without a plan remains unresolved, even if other units can be evaluated. Neither missing plans nor per-unit module subsets replace the separate global roof coverage check.

All complete-input writers advertise the new feature; an old writer must not erase a saved plant plan. Native installation review obtains the relevant saved plant and plan from the owned project revision. The English and German editor must preserve unaffected unit plans, expose conflicting/stale selections and retain values on failure. Mode changes cannot silently discard unresolved wiring. Only the affected geometry/equipment/report dependency is invalidated; unrelated annual energy tasks are not re-run.

Acceptance follows one complete chain: same-model two-unit plans both using MPPT1/input1 remain separate (the existing fixture's 10.14A per unit must not become a shared20.28A); different models use their own facts; genuine parallel strings on one unit still aggregate. Reject duplicate modules and wrong unit/product/revision assignments; a wrong same-model physical instance cannot close a circuit. Save/prepare/evaluate/review/report and screen/PDF/CSV consumers must agree, including stale report and candidate-bypass rejection. Reuse unchanged single-plan/hash/history coverage. This does not add manufacturer connector approval, cable ampacity, protection coordination, national/DSO approval or complete BOS.

Release ordering for this input capability follows the existing retained-input guard: activate a matching Planner HTTP/worker pair that advertises the new writer contract before exposing the new browser/PHP writer. No feed authority or knowledge-index identity is changed merely by this project input. After a retained revision contains the new field, an older executable that lacks its contract cannot be used as a rollback target; preserve the new project/history and use a compatible pair. The existing native compatibility check must refuse that downgrade, not strip the field. Browser artifacts and PHP contract registry ship together, followed by actual save/evaluate/report readback on the selected runtime.


## Source-bound conductor calculations

The optional `installation_circuit_electrical_v1` input contract adds explicit circuit operating conditions, physical cable core roles and a selected manufacturer cable reference. Woo remains the source of cable facts through noncommercial engineering references; these are not new sales SKUs. Each fact binds a hosted original document, its revision and bytes, page and quotation. Resistance/reactance parameters match the declared temperature, current type, frequency and arrangement exactly. Missing parameters do not authorize interpolation, an assumed temperature coefficient or a substituted material value. Historical omitted fields stay omitted; a null cable reference canonicalizes to absence consistently in the browser and service.

The supported methods are a DC resistive current loop, sinusoidal two-wire AC and balanced three-phase AC. Every physical core in a selected cable must be assigned, including PE, unused cores and a balanced neutral. Non-current cores require physical identity/specification agreement but no resistance parameter set. A multicore cable is purchased once by its physical length; active conductors contribute separately to impedance and loss. Parallel/branched conductor paths, unequal phase impedances and incomplete current paths remain explicit unsupported or insufficient states. Calculated signed voltage drop, end-minus-start voltage and conductor loss describe the recorded conductor segments. Maximum, nominal and mixed resistance bases remain distinct. A maximum resistance with leading AC power factor does not necessarily bound the absolute voltage change, so the affected project-limit comparison remains unassessed with its explanation. Project limits retain their declared source and are not national-rule approval.

The same saved revision and frozen source feed the review, screen report, PDF, materials and CSV. Current source withdrawal blocks a new calculation while retained reports preserve their original bytes. Full numerical precision remains in the frozen data; presentation rounding does not change that basis. Both languages expose conditions, source links/pages/revisions, input gaps and limit interpretation. Incomplete paths cannot claim a complete-circuit upper bound. Long valid names remain complete across PDF pages. Every result retains `qualified: false`: terminal losses, thermal ampacity, protection coordination, earthing, country/DSO requirements and complete installation approval are separate unfinished work within the unified goal.

Acceptance covers independent asymmetric DC resistance, distinct forward/return lengths, two-wire and balanced three-phase AC, multicore procurement versus active-core counts, source/specification mismatch and revocation, zero-current and leading-power-factor limit behavior, historical omission and input recovery, followed by the native EN/DE report/PDF/CSV chain and affected desktop/mobile UI. Synthetic acceptance sources must remain identified as fixtures; they do not establish production manufacturer-document publication.

### Manufacturer terminals on a project circuit

A connection point can explicitly select a terminal from a documented Woo installation fact. Its binding records the device instance, canonical product and revision, fact ID, terminal label and document identity and revision. Free-text port names keep their site meaning. Each end of a circuit is checked separately against the prepared Woo product and its associated publication document. A changed product, withdrawn fact, changed document or unavailable terminal leaves that endpoint unresolved. Existing reports remain tied to the source bytes they were prepared with.

For GoodWe battery systems 1956–1958 the manufacturer describes COM1 as an external communications port and COM2/3/4 as internal on page 23. Those two usage values may be maintained on the corresponding documented terminal-map facts. The two other battery products' COM/Alarm entries have no equivalent sourced usage classification. Only a control circuit with an explicitly declared communication use can be compared on this basis; an unclassified fact still identifies a terminal. The reviewer can read which endpoint and use matched, which differed and which lacks evidence. The result does not qualify the circuit, its pin assignment, protocol, protection or earthing.

When a project introduces a binding or communication use, it requires the terminal-binding input contract. The frozen report, PDF and materials CSV carry the endpoint assessment for that revision. The assessment has no purchase quantity. The provisional project materials and customer solution draft retain their existing sales semantics.
