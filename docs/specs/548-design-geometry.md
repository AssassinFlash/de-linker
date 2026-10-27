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
