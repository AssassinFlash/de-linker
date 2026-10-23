# Map drawing: metric commands and interaction controller

This is an internal source increment of the active **unified solution workspace
and whole-site delivery** map. It does not replace the full map's destination or
declare drawing, roof planning, calculation or the application delivered.
Starting source: `66324a39fb449425dd1144b46b4d3abc21dc52d0`.

The immediate contract comes from the existing
[implementation route](../../../../research/2026-10-23-map-workbench-integration/IMPLEMENTATION.md)
and the installed-library
[drawing controller evidence](../../../../research/2026-10-23-map-workbench-integration/DRAW-CONTROLLER.md).
The controller is deliberately not mounted by the customer UI in this increment.
Only source/library/domain acceptance can pass here; browser recovery, a complete
customer drawing flow and native acceptance still belong to the active map.

## Source contract

1. Geographic drawing is an interaction buffer. Metric UV/ENU geometry remains
   the project's authority. Renderer/helper IDs and properties never become
   project inputs. There is no separate Terra project history.
2. Bind one explicit roof boundary, roof hole, obstacle footprint or keep-out
   footprint to a frozen whole geometry document. A hole index is scoped to that
   base; it is not promoted to a permanent ID. The whole-frame `group.before`
   refusal must protect later changes to coordinates, holes and other objects.
3. Reconcile cyclic start changes and reversed winding. A moved vertex projects
   exactly one changed point; insertion projects only the new point; deletion
   projects none. All untouched metric points, holes, source statements and
   unrelated inputs retain their exact values. Ambiguous or merged display
   identity and unrelated multi-point changes are explicit refusals.
4. The pinned adapter uses nine decimal places for display handles. Quantise
   that copy with the same `Math.round` rule as the library; this is not a survey
   accuracy claim. Refuse collapsed handles. Retain numeric editing as a future
   consumer fallback; do not snap original UV values to make the SDK accept them.
5. Reuse the accepted WGS84 topocentric/geodetic-vertical-to-plane operation and
   numerical support policy. Require a recorded anchor and true north. A map
   cannot supply invented roof pitch, height, bearing, source permission or
   obstacle extrusion. New shapes require those explicit fields; existing
   source and reference checks run through the same geometry writer.
6. Project history receives one grouped command per completed/confirmed edit.
   A midpoint insertion plus its subsequent drag is one pointer transaction,
   with separate immutable library snapshots reconciled in order. The drag
   must affect the newly inserted point, never an unrelated old vertex.
7. Raw/provisional polygon changes and helper selection never submit a domain
   transaction. Toolbar completion copies only committed vertices and uses
   public mode/feature APIs. There is no fabricated SDK `finishDrawing` API.
8. Disable SDK feature deletion and browser-conflicting rotate/scale shortcuts.
   Whole-object deletion and rigid metric transforms remain domain operations;
   the geographic select mode does not invent their metric semantics.
9. Capture pointerup's actual geographic endpoint and quantise it explicitly.
   The completed action's unique before/after vertex difference identifies
   which point to correct, independently of raw helper indices. Reclose the
   ring, reject duplicates/ambiguous differences and API-fill only that display
   point. A library backfill success is not a polygon topology/engineering pass.
10. Cancel, lost capture, outside release, blur, hidden document, secondary
    pointer and disposal invalidate pending transactions. Raw input previously
    handed to the caller remains available. Restore the exact original map
    pan/rotate/double-click and cursor state, including originally disabled
    handlers. Stop and detach the controller while its old map/style still
    exists; late microtasks cannot call the project writer.
11. The viewport owns a completion-click pick gate that outlives the controller.
    A completion click cannot become a fresh object selection; reset the gate
    only at a later physical pointerdown.
12. All pinned-library callbacks/API replies are inspected; initial projection
    cannot create commands. Tests use the real installed Terra Draw library,
    not a replacement implementation. Test adapters and JSDOM prove library
    and application boundaries, not actual WebGL, map-provider or touch UI.

## Acceptance boundary

Tests cover winding permutations, exact untouched point identity, every
insertion/deletion edge, the configured 20,000-vertex resource window, sloped
roof planes, retained holes/extrusion/source data, grouped project undo/redo,
provisional-vs-completed library events, midpoint coalescing, last-endpoint
correction, cancellation/disposal and stale whole-frame refusal.

No runtime mount, UI copy, provider style, CSS pipeline, local account, project
save, production data or outward email is changed by this source increment.
There is consequently no new UI state to present as native-accepted. The
customer-facing drawing intake/review, scoped raw-draft persistence and
recovery, source/plane confirmation, same-project 2D/3D/save/reopen and EN/DE
desktop/phone/physical-touch evidence remain required work on this map. Polygon
topology/fit checks must still use the explicit geometry-review boundary;
coordinate parsing/command validation must not be described as that check.

The full goal additionally retains energy/country capabilities, real equipment
release and complete BOM/report/PDF, site/Genie/Woo/draft/inquiry consumers,
migration, review-site acceptance and production backup/deploy/readback gates.
None is closed by this controller increment.
