# Pinned Terra Draw controller contract

2026-10-24 (Asia/Shanghai). Read-only starting HEAD `66324a39fb449425dd1144b46b4d3abc21dc52d0`; parallel implementation may advance it. This narrowly extends [IMPLEMENTATION](IMPLEMENTATION.md) and [MAP-DISPLAY](MAP-DISPLAY.md). **V** below means installed first-party source or executed library fixture; **D** means our controller design, still to implement. No application/test/locale/config/production changes, dependency installation or external acquisition were made. Library fixtures are not native map, GPU, touch-device or UI acceptance.

## 1. Immediate implementation contract

**Use one Terra instance per live map as an interaction buffer; write only explicit domain operations at their gesture/confirmation boundary.** Keep the existing `GeometryCommand { type:'group', before, edits }` writer and original UV points. The present [MapViewport](../../../apps/planner/src/components/design/MapViewport.tsx) and [mapGeometry](../../../apps/planner/src/domain/mapGeometry.ts) display full roofs/holes, obstacle surfaces and module cuboids; that collection must not be passed wholesale to Terra. Terra editable features are separate single-ring handles with an external binding table. Existing [geographicOnRoof](../../../apps/planner/src/domain/geographic.ts) performs the accepted geodetic-vertical/roof intersection; reuse it for changed/inserted points. Do not substitute the older horizontal projection, discard curvature Up or change accepted coordinate mathematics. (D)

Critical verified caveats: **no `setSnapshot`, `finishDrawing`, or `retainValidGeometry` API; add is not upsert; helpers share the store/ID allocator; midpoint drag emits two finishes; native Delete does not emit finish; winding can reverse; pointercancel is unhandled; stop during interrupted drag leaves map interaction toggles disabled.** Exact evidence follows.

## 2. Supported construction and public API (V)

Actual installed app packages: `terra-draw@1.35.0`, `terra-draw-maplibre-gl-adapter@1.4.1`, `maplibre-gl@5.24.0`. Declaration [Terra public API](../../../apps/planner/node_modules/terra-draw/dist/terra-draw.d.ts), [polygon options](../../../apps/planner/node_modules/terra-draw/dist/modes/polygon/polygon.mode.d.ts), [select options](../../../apps/planner/node_modules/terra-draw/dist/modes/select/select.mode.d.ts), [adapter options](../../../apps/planner/node_modules/terra-draw-maplibre-gl-adapter/dist/terra-draw-maplibre-gl-adapter.d.ts).

```ts
// Shape of a valid pinned-library configuration, not the finished controller.
const draw = new TerraDraw({
  adapter: new TerraDrawMapLibreGLAdapter({
    map, prefixId: uniqueControllerPrefix,
    coordinatePrecision: 9, ignoreMismatchedPointerEvents: true,
  }),
  idStrategy: {
    getId: () => crypto.randomUUID(), // also used for library helpers
    isValidId: id => typeof id === 'string' && id.length > 0,
  },
  modes: [
    new TerraDrawPolygonMode({
      editable: false, showCoordinatePoints: false,
      keyEvents: { cancel: 'Escape', finish: 'Enter' },
    }),
    new TerraDrawSelectMode({
      keyEvents: { deselect: 'Escape', delete: null, rotate: null, scale: null },
      flags: { polygon: { feature: {
        draggable: true, rotateable: false, scaleable: false,
        coordinates: {
          draggable: true, deletable: true, midpoints: { draggable: true },
        },
      } } },
    }),
  ],
  // No independent session undo. Existing project history remains authoritative.
});
// Register callbacks before start: adapter's ready callback is synchronous.
draw.on('finish', onFinish);
draw.on('change', onChange);
draw.on('select', onSelect);
draw.on('deselect', onDeselect);
draw.start();                 // after map style can accept sources/layers
draw.setMode('polygon');      // 'select' and built-in 'static' also available
```

The one polygon mode handles roof/hole/obstacle/keepout roles via controller state; flags are keyed by **`feature.properties.mode`**, here `polygon`, not by role or GeoJSON geometry type. Select defaults contain no drag flags, so just adding a SelectMode does not enable vertex editing. `modeName` can name extra modes only at construction; mode options cannot later rename one. (V: P `153–190`; S `219–271`, `948–953`; base.mode `164–168`.)

| Public operation | Pinned behavior and controller consequence |
| --- | --- |
| `new TerraDraw`, `start`, `stop`, `enabled`, `getMode`, `getModeState`, `setMode` | `start`/`stop` are idempotent. `start` synchronously registers adapter sources/layers and emits ready; it does not await map load. Switching away from polygon stops that mode and removes its unfinished drawing. `static` is installed internally. T `159–221`, `915–942`, `1421–1478`, `1528–1535`; P `310–314`. |
| `getSnapshot()`, `getSnapshotFeature(id)` | Copies of the entire store or one feature, including helpers/provisional geometry. Read the explicit completed ID on finish; no snapshot setter exists. T `855–870`. |
| `addFeatures(features)` | Requires an instantiated `properties.mode`; returns per-item validation. Existing ID produces invalid, never replaces it. A mixed batch can partially load, so inspect every result before considering projection synced. T `1357–1414`; Store `96–184`. |
| `updateFeatureGeometry(id, geometry)` | Validates same geometry type and installed mode; throws for missing/invalid/guidance feature. Origin is API; selected helper geometry is refreshed. It does not provide a metric operation. T `1134–1194`. |
| `updateFeatureProperties(id, partial)` | Shallow merge; internal reserved properties cannot be changed through this method. Do not use it to force selected/currentlyDrawing/helper flags. T `1044–1126`. |
| `removeFeatures(ids)`, `clear()` | Remove deselects and removes associated helpers; missing ID throws. Clear delegates to adapter, whose onClear resets mode/store. Both generate API-origin changes while enabled. T `877–880`, `950–1002`, `1470–1476`; A `597–616`. |
| `selectFeature(id, selectMode?)`, `deselectFeature(id)` | Automatically switches to installed select mode; missing select mode throws. Programmatic selection emits the same select/deselect callbacks and creates/deletes helpers. Prevent tree↔map feedback loops. T `738–794`, `1013–1028`; S `380–395`. |
| `on/off`, `undo/redo/canUndo/canRedo/clearUndoRedoHistory` | Off requires original callback reference. Undo/redo are opt-in via mode/session handlers; without configuration `undo()` returns false. Do not create a second project history in Terra. T `159–185`, `1319–1347`, `1545–1573`. |
| `transformFeatureGeometry(id, {...})` | Geographic rotate/scale API exists; it is not a UV/metric command. Retain domain transformations for project rigid motion/rotation. Do not invent `rotateFeature`, `setSnapshot`, `finishDrawing`, or `retainValidGeometry`. Public declarations `216–243`. |

## 3. Events, raw drawing and transaction boundaries

`change(ids, type, context?)` uses create/update/delete/styling; context carries `origin:'api'` and/or `target:'geometry'|'properties'`. **It does not carry gesture IDs, vertex indices, updateType, committed/final status or a durable domain command.** `finish(id,{mode,action})` is the completed library action. Action strings are draw/edit/deleteCoordinate/insertMidpoint/dragCoordinate/dragFeature/dragCoordinateResize. `select/deselect(id)` are temporary selection. Mutation validation callbacks can see updateType, but it is not forwarded as a public change boundary. (V: T `258–318`; common `169–215`; M `428–446`.)

| User/library event | Verified sequence | Domain boundary (D) |
| --- | --- | --- |
| New polygon clicks/mouse preview | First click immediately creates a degenerate raw Polygon, `currentlyDrawing:true`; clicks update committedCoordinateCount, movement includes provisional coordinates. Helpers and property changes also emit change. No finish per vertex. P `791–916`. | Store raw preview, never project revision. Keep source/plane/role and baseGeometry alongside it. |
| Click closure / Enter keyup | Close removes provisional vertex and raw/count properties, sets mode state started, clears polygon local history, then `finish(draw)`. `getSnapshotFeature(id)` now returns a closed final single ring. P `192–259`, `1002–1007`. | One create candidate/group, only after required source/plane fields and normal domain validation. Do not count the repeated closing vertex as a UV vertex. |
| Drag selected vertex/feature | Many change events; pointerup triggers `finish(dragCoordinate)` or `finish(dragFeature)`. The finish runs before adapter exits its pointerup handler. S `1034–1068`. | Pointerdown capture freezes before/binding; defer finalization to a microtask after the whole pointerup dispatch, then one explicit point/move command. |
| Click/drag midpoint | Click gives finish(insertMidpoint). Drag emits that finish in onDragStart **before continued dragging**, then finish(dragCoordinate) at drag-end. S `681–689`, `895–915`. | Coalesce by primary pointer transaction. Intermediate insert finish cannot write history. Click-only insert finalizes once after pointerup. |
| Coordinate deletion | Right-click path removes a coordinate when flags allow, then finish(deleteCoordinate). S `480–583`. | One explicit delete-vertex command with preserved other UV points; keep the controller's ring mapping. |
| Whole feature Delete key | Default keyup emits deselect first, then helper/feature delete changes; **no finish**. S `765–790`. | Disable native delete as above; existing domain delete UI handles expected roof dependents. Do not infer a user delete from every library delete event. |
| Esc/cancel/mode switch | Unfinished raw drawing removed, no completed draw finish. P `1002–1004`, `1258–1287`. | Cancel preview; retain previous authoritative geometry/raw input where needed. No empty-domain command. |

There is no public finish method for a toolbar button. For this pinned version, a controller-owned finish can snapshot the **raw** polygon and its `committedCoordinateCount`, copy the first N committed coordinates, require N≥3, close its own candidate, then `setMode('static')` to clean provisional library state. The probe verified raw counts 1/2/3 and coordinate arrays `[A,A,A,A]`, `[A,B,B,A]`, `[A,B,C,C,A]`. This is an explicit pinned raw-data adapter, not calling private `close()` or synthesizing keyboard input. Preserve candidate/raw data if confirmation/commit fails; successful mouse/Enter completion instead consumes the already-closed finish snapshot. (V + D.)

For last-pointer position, do not assume onDragEnd reapplies its event: SelectMode emits finish using the latest stored geometry. The installed throttle condition is `count % dragEventThrottle === 0 → return`; **setting 1 skips every drag**, while default 5 skips every fifth. Keep default unless tested; if last-event alignment is required, explicitly record final cursor→domain edit rather than accepting stale/quantized whole geometry. S `172`, `955–961`, `1034–1068`.

## 4. IDs, helpers, precision and unchanged UV

Default ID strategy returns UUIDs but validates only string length 36 (Store `48–50`). The same allocator creates raw features and helpers. Use a controller `Map<rawId, {role,objectId,roofId,ringIndex,baseHash,displayToDomainIndex}>`; allocation alone is not a new domain object. Newly drawn raw ID can be bound to a separately allocated stable domain ID at confirmation. Programmatic add/update errors are explicit, not missing drawing success. (D)

Whole snapshots include `selectionPoint`, `midPoint`, `coordinatePoint`, `closingPoint`, `snappingPoint`; raw polygons have `currentlyDrawing`, `committedCoordinateCount`, `provisionalCoordinateCount`. Selected geometry adds `selected`; helper references include selectionPointFeatureId/midPointFeatureId/index. These are library data, not saved project attributes. Prefer explicit binding whitelist plus target ID/type over blacklist-only filtering. T's private isGuidanceFeature does not include every guidance property, so it is not a persistence policy. (V: common `300–328`; T `797–803`; fixture below.)

**Winding correction is real.** M `155–158`, `352–357`, `420–425` and geometry/ensure-right-hand-rule `4–12` reverse an exterior ring when needed on creation/finish. Probe clicked A,B,C and final snapshot returned A,C,B,A. Thus a Terra helper index is not automatically the original `boundary_uv` index. Normalize only the display copy with an explicit permutation; retain per-vertex bindings, and reconcile cyclic/reversed order at finish. Ambiguous/merged display vertices must give a recoverable specific editing error, never an entire geographic-ring replacement. Holes use roof ID + ring index + frozen base; they do not acquire invented permanent IDs. (D)

Polygon validation rejects more than one ring and coordinates beyond adapter precision. Default precision 9 affects raw lng/lat rounding and accepted imports; it is unrelated to survey accuracy or the accepted metric representability budget. Quantize the fresh display handle only. Update one moved point, insert/delete one point, or apply explicit metric delta/pivot to original UV according to the existing operation semantics. All unrelated vertices, holes and objects retain their exact input values. (V: base.adapter `51–54`, `123–125`; polygon.validation `19–75`; D.)

API projection feedback needs both `applyingProjection` guard and `context.origin==='api'` filtering; programmatic selection callbacks lack that origin. Deselect before geometry replacement/clear and restore valid explicit selection after sync. Freeze an active transaction's before document; an intervening 2D/3D edit should reach the existing group-before rejection, preserve raw work and reproject/rebind deliberately. It must not overwrite later input from the last Terra snapshot. (D)

## 5. Pointer, touch, map click and disposal

The real adapter binds **DOM canvas** pointerdown/move/up, contextmenu, keydown/up; it does not bind a browser click. Non-primary pointers are ignored. Pointerup calls mode onClick or onDragEnd, then resets dragState and restores initial-enabled dragPan/dragRotate. Pointermove calls preventDefault; neither that nor contextmenu prevention is a general stopPropagation guarantee. MapLibre independently uses mouse/touch/click handlers. Its MapMouseEvent.preventDefault controls preventable camera handlers and does not replace the controller gate. (V: B `159–425`; A `342–379`; MapLibre `src/ui/handler/map_event.ts:24–92`, `src/ui/handler_manager.ts:200–226`.)

Controller: capture primary pointerdown to freeze edit context before any insertion/change; queue finalization after pointerup so listener registration order is irrelevant. Suppress MapViewport's existing pick path during editing and for the completion click from that same physical gesture; changing Terra to static inside finish does not make that click a new object selection. Reset the token on the next physical pointerdown, rather than consuming a later unrelated keyboard/pointer action. Camera moves/viewport events never submit geometry. (D)

**Cancellation is an actual gap:** B has no pointercancel/lostpointercapture/global pointerup/blur listener or pointer capture, and ignores pointerup whose target is not the canvas. The actual-adapter DOM fixture below reproduced interruption. Controller must handle pointercancel, lost capture, blur, leaving/hiding/unmount and out-of-canvas release: cancel/recover transaction, discard library preview, restore owned camera handler states and reproject authority. Non-primary pointer ignored by Terra is not multi-touch editing support; suspend/cancel active draw before treating two fingers as navigation, then verify on real devices. (D)

Capture original map dragPan/dragRotate/doubleClickZoom enabled state before starting the draw controller; restore **those values**, not unconditional enables. B.unregister does not reset heldKeys or dragState, and A.clear/unregister do not restore the toggles. After interrupted dragging, reconstructing a fresh controller/adapter is safer than restarting an old adapter with stale gesture/key state. Map style/provider replacement likewise destroys the controller before replacing its style/map. (V: B `440–452`; A `362–379`, `421–426`, `597–672`; D.)

Disposal order: mark controller disposed/invalidate queued work → remove controller DOM/window listeners and original `draw.off` callbacks → `draw.stop()` **while map/source/layers still exist** → restore saved camera handlers if retaining map → release map resources with existing MapViewport lifecycle. Prefix must be unique; adapter creates 3 sources and 5 layers, clear cancels RAF and empties data, unregister removes layers before sources **without existence guards**. Stop after map.remove/setStyle can therefore hit missing resources. A `597–672`; B `440–448`. No additional map render/idle listener is installed by this adapter; render uses requestAnimationFrame. (V + D.)

## 6. Executed evidence and minimal reproducible fixture

Executed against app node_modules with no installs/network: callback-adapter fixture proved final draw, helpers, vertex drag, double midpoint finish, native Delete ordering, no setter and default undo false. An additional **actual adapter** fixture used JSDOM DOM pointer events and a fake Map API (no GPU): non-primary ignored; triangle closed; 3 sources/5 layers; during drag pan/rotate false; pointercancel added no finish; stop cleared store/sources/layers/pending RAF but pan/rotate/doubleClickZoom remained false. These prove library boundaries only.

From the worktree root, this executable fixture reproduces the key transaction evidence (fake projection units are deliberately not engineering metres):

```sh
node --input-type=module <<'JS'
import assert from 'node:assert/strict';
import {TerraDraw,TerraDrawPolygonMode,TerraDrawSelectMode}
  from './apps/planner/node_modules/terra-draw/dist/terra-draw.modern.js';
let cb,n=0;const events=[];
const adapter={
  project:(lng,lat)=>({x:lng*1e5,y:-lat*1e5}),
  unproject:(x,y)=>({lng:x/1e5,lat:-y/1e5}),
  getCoordinatePrecision:()=>9,setCursor(){},setDoubleClickToZoom(){},
  getMapEventElement:()=>({}),getLngLatFromEvent:()=>null,
  register(c){cb=c;c.onReady?.()},render(){},
  clear(){cb?.onClear()},unregister(){this.clear();cb=undefined},
};
const d=new TerraDraw({adapter,
  idStrategy:{getId:()=>`raw-${++n}`,isValidId:id=>typeof id==='string'},
  modes:[new TerraDrawPolygonMode(),new TerraDrawSelectMode({
    flags:{polygon:{feature:{draggable:true,coordinates:{
      draggable:true,deletable:true,midpoints:{draggable:true},
    }}}},
  })],
});
for(const type of ['finish','change','deselect'])
  d.on(type,(...args)=>events.push({type,args}));
const e=(x,y)=>({lng:x/1e5,lat:-y/1e5,containerX:x,containerY:y,
  button:'left',heldKeys:[],isContextMenu:false});
d.start();d.setMode('polygon');
for(const [x,y] of [[0,0],[200,0],[200,200],[0,0]]) {
  cb.onMouseMove(e(x,y));cb.onClick(e(x,y));
}
const id=events.find(x=>x.type==='finish').args[0];
assert.deepEqual(d.getSnapshotFeature(id).geometry.coordinates[0],
  [[0,0],[.002,-.002],[.002,0],[0,0]]); // observed winding reversal
d.selectFeature(id);assert(d.getSnapshot().some(f=>f.properties.midPoint));
const start=events.length;
cb.onMouseMove(e(100,0));cb.onDragStart(e(100,0),()=>{});
cb.onDrag(e(100,30),()=>{});cb.onDragEnd(e(100,30),()=>{});
assert.deepEqual(events.slice(start).filter(x=>x.type==='finish')
  .map(x=>x.args[1].action),['insertMidpoint','dragCoordinate']);
const deleted=events.length;
cb.onKeyUp({key:'Delete',heldKeys:[],preventDefault(){}});
assert.equal(d.getSnapshotFeature(id),undefined);
assert.equal(events[deleted].type,'deselect');
assert(!events.slice(deleted).some(x=>x.type==='finish'));
assert.equal(typeof d.setSnapshot,'undefined');assert.equal(d.undo(),false);
d.stop();assert.equal(d.getSnapshot().length,0);
console.log('pinned-library boundary fixture passed; no UI acceptance');
JS
```

## 7. Exact first-party source index

No external fetch was needed: installed published sources are primary evidence. T/P/S/M/B/Store/common in the text refer to original line numbers of `sourcesContent` entries in [Terra's published sourcemap](../../../apps/planner/node_modules/terra-draw/dist/terra-draw.modern.js.map), **not** generated minified JS line numbers: respectively `src/terra-draw.ts`, `modes/polygon/polygon.mode.ts`, `modes/select/select.mode.ts`, `modes/mutate-feature.behavior.ts`, `common/base.adapter.ts`, `store/store.ts`, `common.ts`. A refers to original `src/terra-draw-maplibre-gl-adapter.ts` in [adapter sourcemap](../../../apps/planner/node_modules/terra-draw-maplibre-gl-adapter/dist/terra-draw-maplibre-gl-adapter.modern.js.map). Extract the entry in memory using JSON sources/sourcesContent, then `splitlines`; no repository/source download is necessary.

```text
Terra map SHA256   52684d483063ff148d5b9fdc94d94c2c8657a82ac955372ca8043d0f3237ef25
Adapter map SHA256 398a7f121b2b9b3b65c6735cc9f7b5d6fd9d6ab8241ca70888d400ad06ab467c
T source SHA256    24fae11bc2fe2fbe33694f68fe536a623b14c2abd6db94c7aeb202a83bb5ded4
A source SHA256    972a54ae86a8318480800358e335df47f2259432804726e1c7cdf137cf9f2a50
S source SHA256    3ad142f07b9717b1c59e63b34920cc5c53e09e31719e63262ca1852fe82cbecf
```

Provider/license/Google routes remain governed by the existing dossier; this controller does not reinterpret data rights or make a geographic drawing a survey. The remaining concrete implementation gates are explicit vertex/segment bindings, coalesced pointer transactions, owned cancellation/handler restoration, strict domain commands and native EN/DE desktop/mobile drawing/edit/save/reopen evidence. No missing account/key blocks this installed-library controller work.

## 8. Precision and final-release endpoint supplement

2026-10-24. This supplements the same pinned versions and **supersedes §3's suggestion to retain the default throttle**. Root is implementing [MapDrawingController](../../../apps/planner/src/data/MapDrawingController.ts), [mapDrawingGeometry](../../../apps/planner/src/domain/mapDrawingGeometry.ts) and [mapRingEdit](../../../apps/planner/src/domain/mapRingEdit.ts); this research turn only read those files and appended this section. No application/test edits or native UI acceptance claim.

### Verified zero throttle and release-coordinate gap

Select.updateOptions accepts `isFiniteNonNegativeNumber(options.dragEventThrottle)` (S `248–249`); common/checks `11–14` defines that as a finite number ≥ 0. Thus **`dragEventThrottle: 0` is supported by the installed input contract**. At S `955–961`, `count % 0` is NaN and `NaN === 0` is false, so no move is skipped. This is a checked pinned implementation behavior, not a future-version guarantee. A real-library/real-MapLibre-adapter DOM fixture with fake map/GPU confirmed that its fifth drag move is retained.

That still does not consume the final pointerup position: B `351–354` forwards the release event to Select.onDragEnd, but S `1034–1068` emits finish from the existing geometry and never calls its drag behavior with that event. In the executed fixture (fake screen projection `x=lon*1e5`, `y=-lat*1e5`):

```text
dragEventThrottle = 0
fifth pointermove: screen (50,20) → stored vertex (0.0005,-0.0002)
pointerup:         screen (90,60) → adapter position (0.0009,-0.0006)
stored after up:                    still (0.0005,-0.0002)
```

`adapter.getLngLatFromEvent(event)` is public and reads the actual event position using map unproject (A `342–347`). It does **not** apply coordinatePrecision itself. B `123–125` performs that rounding while constructing normal Terra pointer events; `geometry/limit-decimal-precision.ts:1–4` is exactly `Math.round(value * 10 ** precision) / 10 ** precision`. Final-endpoint correction should use this same display rounding explicitly, then the normal finite/range/unique-ring checks. Do not silently treat the public adapter result as already quantized. Metric UV inputs remain untouched by display quantization.

### Public helper hits: available but not adopted for endpoint identity

T `1505–1521` implements public `getFeaturesAtPointerEvent` through the adapter and `featuresAtLocation`. With `ignoreSelectFeatures:false`, selected single-ring helpers expose:

| Point helper | Actual returned properties | Original source entry/lines |
| --- | --- | --- |
| Vertex | `selectionPoint:true`, `selectionPointFeatureId:<raw feature ID>`, `index:<open-ring index>` | `modes/select/behaviors/selection-point.behavior.ts:8–13,34–50` |
| Midpoint | `midPoint:true`, `midPointFeatureId:<raw feature ID>`, `midPointSegment:<segment start index>`; it has no vertex `index` contract | `modes/select/behaviors/midpoint.behavior.ts:147–172`; insertion is InsertAfter at segment index, `72–98` |

The executed public query returned vertex index 0 and midpoint segment 0 for the explicitly selected `bound-ring`; the default query returned no select helpers because `ignoreSelectFeatures` defaults true (T `559–562`). Results are spatial-search order, not a nearest-target selection. More subtly, query pointerDistance defaults to 30 while Select pointerDistance defaults to 40, and the query's bounding-box prefilter uses **half** its pointerDistance (`geometry/shape/create-bbox.ts:16–30`) before T `635–639` applies the full Euclidean threshold. A point 35 px away was absent with query 40 and present with query 80. If this API is used elsewhere to match a Select radius P, request a covering query such as 2P, then independently filter distance < P and sort/resolve against the bound raw feature; do not assume query 40 equals Select 40.

Even that query is not a public setter for the mode's active vertex. Select decides onDragStart only after the first threshold-crossing pointermove, may use cached dragTarget, and prioritises draggable coordinates before the midpoint branch (S `807–925`). Therefore a pointerdown helper hit alone does not prove which vertex Terra later changed. **Root's adopted endpoint design uses explicit before/after single-point reconciliation instead of helper-index guessing.** No private selection/drag mode method is required.

### Adopted minimal endpoint contract (D)

1. Capture the complete, bound, open display ring at primary pointerdown (`pointerBefore`). Keep the existing immutable document/frame and metric ring binding. Preserve each emitted insert/drag snapshot immediately; do not replace an insertion snapshot with a later mutated store read.
2. At matching window pointerup capture, while adapter/map remain alive, obtain the release lng/lat via public getLngLatFromEvent and apply the same nine-decimal display rounding. Keep it as a pending endpoint; never commit at capture phase, never convert cancelled/out-of-canvas/foreign-pointer releases into edits.
3. After dispatch, require the transaction's supported final action to be dragCoordinate. For a normal drag, compare pointerBefore with its final drag snapshot. For midpoint drag, compare the **already-inserted snapshot** with the final drag snapshot. Use the existing exact cyclic/reversal reconciliation to identify exactly one changed point. Multiple changes, ambiguity or no identifiable change are explicit refusal/recovery, not permission to guess a helper or overwrite a ring. A click-only insert keeps the actual midpoint and does not receive an arbitrary cursor endpoint.
4. Replace only that identified display point with the pending endpoint, and rebuild closure so changing the first open-ring vertex also changes the repeated last coordinate. If there was an insert step, verify that the subsequent drag targets the newly inserted point; a drag of another old point is not the same explicit insert-and-drag intent. Preserve all other display points and all untouched original UV values.
5. Run the final candidate through the current ring/precision/duplicate-point/domain rules. Public updateFeatureGeometry can then refresh the temporary library feature under the API projection guard; it must not create another transaction. Create one domain group-before command through the existing writer. An endpoint equal to the original position may produce no net edit; cancellation/disposal invalidates queued endpoint work.

**Validation boundary:** updateFeatureGeometry calls the polygon mode's basic validator (T `1165–1177`), not Select's drag-coordinate self-intersection path (`modes/select/behaviors/drag-coordinate.behavior.ts:256–265`). Therefore successful API feedback is not proof the corrected endpoint is topologically valid. Apply the intended final-candidate policy explicitly: either retain it as diagnosed unfinished geometry under the existing domain contract, or reject it according to the controller's declared interaction policy. Never claim the previous valid preview proves that a later release endpoint passed those checks. The current unsnapped vertex configuration makes raw release coordinates appropriate; enabling snapping later requires a matching explicit final-endpoint snapping policy, rather than bypassing the snapped preview.

Minimum additional fixtures for root implementation: five moves with the fifth retained at throttle 0; release ≠ last move with only one UV point changed; midpoint insert+drag using its intermediate snapshot; first-vertex closure update; ambiguous/duplicate/out-of-range endpoint refusal; no-difference refusal; cancellation/disposal before queued flush. The fixture in this research verified the library inputs and stale-release behavior, not root's complete implementation or UI.
