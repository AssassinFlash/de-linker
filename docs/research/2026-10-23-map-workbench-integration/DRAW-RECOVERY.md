# Unfinished map drawing: recover committed points, then continue

2026-10-24. Starting HEAD `43297ecf5673fa5f29c82f90fbe583666a5e3e15`, with parallel application work. Research only; this file is the sole change. Installed versions remain Terra Draw 1.35.0 / MapLibre 5.24.0 / adapter 1.4.1. **V** means installed first-party source or executed library probe; **D** means proposed application behavior. No dependency install, external acquisition, private mode/store calls, historical click replay, native/UI or production acceptance.

## Decision

**Implement an application-owned open-prefix collector for recovering unfinished drawings. Persist the committed vertices, render them as Point/LineString, append genuine new user input, and explicitly stage a closed candidate once the user has at least three points. Reuse the reviewed Terra Select controller for that candidate.** Stock Terra PolygonMode cannot publicly resume its half-drawn state. Displaying its old raw Polygon is insufficient. This needs a small new collector and its UI/fixtures; the already reviewed controller does not acquire a resume capability merely because the journal restores its bytes. (D)

The collector accepts an empty or restored prefix and does not require changing the domain geometry model. Fresh Terra drawing may continue to emit its existing raw format: its committed prefix is normalized into the same journal record. Recovery uses the explicit collector path, with no fabricated events. Keep the existing project owner/revision/source/plane journal work and single `GeometryCommand` writer.

## Why no stock resume API exists (V)

| Candidate mechanism | Actual pinned source/API | Conclusion |
| --- | --- | --- |
| Polygon constructor/update options | `TerraDrawPolygonModeOptions`: snapping, pointerDistance, keyEvents, pointerEvents, cursors, editable, showCoordinatePoints, plus BaseModeOptions. No initial vertices, seed, resume, current feature or drawing-state import option. | `editable:true` enables editing behavior; it does not adopt an unfinished polygon. |
| State API | Polygon's `currentCoordinate`, `currentId`, last mouse event and local undo buffer are private. Base `state` has a getter; its setter throws "Please use the modes lifecycle methods". `getModeState` only reads lifecycle state. | A persisted `currentlyDrawing` property is not the mode's internal current feature. Do not set private fields or invoke internal `start/onClick/close` to reconstruct it. |
| `addFeatures` / `updateFeatureGeometry` | `afterFeatureAdded` only creates optional coordinate-point display. `afterFeatureUpdated` explicitly resets `currentCoordinate/currentId`, local undo and closing helpers when the current drawing was updated; original source even explains that recovering that state is not supported. | Adding raw bytes can display them. It cannot continue their existing drawing state. Updating the current raw feature is not a resume technique. |
| `setMode('polygon')` | Stops the previous mode and starts Polygon in `started`; a genuine new first click sees `currentCoordinate === 0`, creates a new raw feature and only then enters drawing. | Setting the mode does not choose an imported raw polygon as current. |
| Mode/session undo-redo | Mode handler registers current in-memory undo/redo callbacks and reads sizes; session handler owns private history/undo/redo stacks. Neither declares history/state import. | Persisting GeoJSON or a history size does not restore the drawing cursor or undo stack. Keep raw-prefix undo in the application journal. |
| `TerraDrawExtend` | Public exports include BaseDrawMode/BaseSelectMode/BaseAdapter and custom-mode hooks. A new custom mode could own its own seeded state and implement lifecycle/style/validation/input. | This is a real extension route, but a new drawing implementation, not a hidden stock-Polygon resume API. The smaller collector below avoids a custom Terra mode and private stock state. |

Precise evidence: published [polygon declaration](../../../apps/planner/node_modules/terra-draw/dist/modes/polygon/polygon.mode.d.ts); [base declaration](../../../apps/planner/node_modules/terra-draw/dist/modes/base.mode.d.ts); [extend declaration](../../../apps/planner/node_modules/terra-draw/dist/extend.d.ts); [mode history](../../../apps/planner/node_modules/terra-draw/dist/undo-redo/mode-undo-redo.d.ts), [session history](../../../apps/planner/node_modules/terra-draw/dist/undo-redo/session-undo-redo.d.ts). Original source entries in the installed [Terra sourcemap](../../../apps/planner/node_modules/terra-draw/dist/terra-draw.modern.js.map): polygon.mode `105–151,303–314,804–834,1437–1488`; base.mode `83–90,187–226`; terra-draw `915–942`. Line numbering and fixed sourcemap hash are explained in [DRAW-CONTROLLER §7](DRAW-CONTROLLER.md#7-exact-first-party-source-index).

### Executed public-API probe

Created fresh instances, loaded representative persisted 1/2/3-point raw Polygons with their original `currentlyDrawing/committedCoordinateCount`, then called public `setMode`, `getModeState`, `canUndo`, and `updateModeOptions(editable:true)`. No old click was replayed or new fake input dispatched.

| Restored committed points | `addFeatures` | State after `setMode('polygon')`, including editable:true | Mode undo |
| --- | --- | --- | --- |
| 1 | valid; stored count stays 1 | started | false |
| 2 | valid; stored count stays 2 | started | false |
| 3 | valid; stored count stays 3 | started | false |

Separately stripped raw flags from a three-point prefix, explicitly closed it, then used `addFeatures` + `selectFeature`: valid, mode `select`, state `selecting`, three selection helpers. These are library-level results using a fake adapter/projection, not a real map or recovery UI acceptance. A raw degenerate polygon passing the library's basic validation is not proof it is an engineering candidate.

## Recommended recovery contract (D)

| Restored record | Show immediately | Actual continuation |
| --- | --- | --- |
| 1 committed point | A point and its existing metadata; no invented edge or area | Collector starts with that exact point. The next accepted genuine click/button adds point 2. |
| 2 committed points | Both points and an open LineString | Continue appending point 3, 4, etc. Do not require the user to replace/retrace points 1–2. |
| 3+ points, unfinished | All points and the open line in original order; optional closing preview is derived display only | User can continue appending or explicitly choose Finish/Review shape. Reload alone never closes or applies it. |
| Explicitly staged/complete candidate | Closed candidate with source/plane state and an Apply decision | Load sanitized single-ring Polygon into the existing Terra Select entry; edits remain staged until the caller's normal confirmation/writer boundary. |

### Prefix and phase, not synthetic polygon state

For the existing `RawMapDrawing`, when incomplete and `committed_coordinate_count=N`, take exactly `geometry.coordinates[0].slice(0,N)` after strict type/count/range/resource checks. Existing Terra raw shapes contain provisional/duplicate/closing positions: 1 point may be `[A,A,A,A]`, 2 `[A,B,B,A]`, 3 `[A,B,C,C,A]`. Do not persist a hover position as a committed point or infer N from ring length. Missing/corrupt counts remain an explicitly invalid recovery record; preserve original evidence, never guess vertices or silently discard the record. Existing complete candidates use the normal closed-ring parser.

The journal's semantic geometry payload should be a versioned `collecting` prefix or `staged` closed candidate, plus the already planned shape kind, source/rights, roof/plane inputs and baseline identity. Library helpers, selected flags, private mode fields and pointer coordinates are not persistence state. A raw point's nine-decimal display position is not survey precision. Preserve source/coordinate/calibration facts independently. Restoring the journal must not introduce a default flat roof, height, north or source permission.

### Controlled collector using public MapLibre primitives

Use these already installed first-party primitives, not a replacement map/drawing package:

- `map.on('click', listener)` supplies `MapMouseEvent.lngLat`, `point` and `originalEvent`. Append from that event once through an application function; do not dispatch clicks to Terra. The installed handler suppresses mouse clicks after movement ≥clickTolerance (default 3 px), but this alone does not establish correct multi-touch behavior.
- `map.on('mousemove', listener)` may draw a transient next segment. It never changes the committed prefix or its journal. Point features for all committed vertices and a LineString only when N≥2 are sufficient for static restoration; no Polygon is required for N<3. Use `addSource(type:'geojson')`, normal circle/line layers and `GeoJSONSource.setData` on fresh derived copies.
- On a real click, require active collection phase, valid current identity, primary completed gesture and a usable map. Reuse the existing pick gate so the same gesture cannot also select a project object. Exclude cancelled/dragged/multiple-pointer gestures; consume one accepted gesture only once. Ignore second-click detail/double-click duplication and disable double-click zoom while collecting; use an explicit Finish button rather than making a double-click both append and close. Do not separately append from both touchend and click.
- All input paths call one application `appendVertex(lngLat)` with the same finite/range, display quantization, duplicate/budget checks and immutable raw-journal update. Keep a refused input's error visible without removing previous points. Raw-prefix undo/remove-last edits this buffer; global project undo remains a different operation with explicit focus/phase handling.
- For keyboard use, keep the existing MapLibre arrow-key panning and show a centre reticle. A real **Add vertex at map centre** button calls the same append function with `map.getCenter()`. Standard button Enter/Space behavior, Finish, remove-last and pause controls make the entire collection possible without synthetic pointer/keyboard events. Canvas Escape pauses and retains the draft; discarding is a separate explicit action. Avoid overriding native arrow handlers or assuming Enter already inserts a map point.
- Before provider/route/account changes, remove original listeners via `map.off`, clear collector DOM listeners and overlays using their owned prefix, and retain its committed journal. Mode interruption does not erase the prefix. While collecting, do not mount stock PolygonMode concurrently on the same canvas.

This is a proposed controller over established map events and GeoJSON display; it is not a claim that MapLibre itself supplies a resumable polygon tool. Source/policy evidence: `MapMouseEvent` properties/construction in [events.ts:498](../../../apps/planner/node_modules/maplibre-gl/src/ui/events.ts); click suppression in [map_event.ts:43](../../../apps/planner/node_modules/maplibre-gl/src/ui/handler/map_event.ts); public on/off/addSource/addLayer in [map.ts](../../../apps/planner/node_modules/maplibre-gl/src/ui/map.ts); updates in [geojson_source.ts:249](../../../apps/planner/node_modules/maplibre-gl/src/source/geojson_source.ts); keyboard panning in [keyboard.ts:13](../../../apps/planner/node_modules/maplibre-gl/src/ui/handler/keyboard.ts); public centre in [camera.ts:369](../../../apps/planner/node_modules/maplibre-gl/src/ui/camera.ts). The 3 px default is interaction policy, never metric/source precision.

### Collector → staged candidate → reviewed Select

On explicit Finish with N≥3, copy the prefix, add exactly one repeated first point, and run `readMapPolygon`/normal candidate checks. Keep the journal as collecting if this fails; do not clear it. On success, durably mark a staged candidate, detach the collector and its event ownership, then instantiate the existing `MapDrawingController` with `{kind:'edit', ring}`. Its public add/select path is supported; no private `close()` or replay is needed. Its transaction callback updates the staged candidate, not an unrelated confirmed project. Normal Apply uses the stored source/plane/baseline and existing newMapShapeCommand/group-before writer once.

If three saved points should be reviewed immediately, offer an explicit **Review saved shape** action; the same staging transition applies. If the user chooses to continue adding points, keep the open collector even though N≥3. On a stale baseline or changed source/plane, preserve the original prefix/candidate and require explicit revalidation; do not silently apply it to a different roof/project or turn it into a new user mutation after account change. Root's session/project-scoped journal owns those checks.

## Required implementation and focused proof

New code is needed for the seeded committed-prefix collector, Point/LineString overlay lifecycle, append/remove/keyboard controls, raw-format adapter and staged handoff. Reuse existing MapLibre, source contracts, quantizeMapPosition, candidate parser, reviewed Select controller and domain writer. No library upgrade, paid provider, Google key or custom Terra mode is required. Data derivation/retention/export claims stay with their original source; recording raw vertices does not create new provider rights. The provider/source rules in [IMPLEMENTATION](IMPLEMENTATION.md) and [MAP-DISPLAY](MAP-DISPLAY.md) remain in force.

Minimum fixtures: restore 1→append 2→append 3 without changing earlier coordinates; restore 2→append; restore 3+→continue versus explicitly stage; hover excluded; remove-last/reload; duplicate/corrupt count refused without data loss; pause/cancel/reload; select-edit staged ring without helper leakage; changed baseline/identity refused; source/plane retained; one final group-before application. Native EN/DE × desktop/mobile must additionally prove real taps versus pan/pinch, keyboard/button collection, visible recovery state, save/reopen and actual continued drawing. None of those UI gates was run in this research.
