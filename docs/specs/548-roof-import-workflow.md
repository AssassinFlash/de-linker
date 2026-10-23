# Guided owned roof import

This increment connects the accepted geographic intake to the Journal roof
workspace. The active map still requires map drawing, image calibration,
engineering, full downstream consumers, deployment and production readback.
None of these becomes accepted merely because this import workflow passes.

## Customer operation

1. Import roof geometry opens inside Roof design, for every project type.
   It must not change another workspace, the current geometry or a saved
   revision. An unfinished import blocks leaving the workspace and project.
2. File and roof: choose a UTF-8 GeoJSON original within the existing 4 MiB
   intake policy. Polygon/Feature/FeatureCollection/MultiPolygon choices show
   file feature names and one-based face labels. A single supported choice is
   visibly selected; multiple choices require an explicit selection. Never ask
   the customer to type a zero-based feature/part index. Invalid 3D/CRS/rings are
   not repaired. Original bytes and every opening remain intact.
3. Roof plane: pitch, true-north downslope bearing, relative height at the
   selected outline's first vertex, and their source basis are explicit.
   Numeric input uses the active language's decimal convention. No measured
   pitch, direction, height or source precision is supplied as a default.
   A separate explicit relative-zero checkbox sets a drawing datum; it does
   not claim ground/ellipsoid height. Existing geographic origins stay fixed.
   Selecting this datum bypasses a previously rejected height without erasing
   its raw string; switching back requires correcting that height again.
   A new empty unreferenced project adopts the selected vertex as origin.
   A nonempty unaligned project must align its existing frame first; import
   cannot silently rotate or reposition it. The accepted geographic conversion
   kernel remains authoritative. Plane construction keeps the complete geodetic
   vertical at the selected vertex when assigning relative ENU Up.
4. Source: identify the original and measurement basis, state retain/derive
   permission, independently choose export permission, and optionally record
   source-stated precision. Unknown precision stays null. Permission is an
   explicit user declaration, never an automatically verified licence.
5. Prepare a server preview only after validation and a committed browser
   recovery record. Preview the actual accepted roof, area and openings, then
   explicitly add it to the current design. File storage and project save are
   distinct. Attachment uses the same `attachGeometryImport` domain command,
   exact geometry snapshot and one project history step. Undo/redo must also
   restore the source-to-original selection without losing unrelated inputs.

## Interruption and evidence

- Keep step controls mounted while moving Back, validating or dispatching.
  A typed input refusal returns the same editable raw values and file. Closing
  explicitly cancels unfinished local input; it restores focus only after the
  real entry button is enabled and native admission remains current.
- Persist the exact file/options/project/key before dispatch. If storage is
  unavailable or its existing count/byte policy is exceeded, do not dispatch.
  Never evict another upload to make room. Unknown acknowledgements, including
  unidentified 4xx responses, retain the exact original request for an explicit
  retry. Only identified pre-mutation refusal code/status pairs release it.
  Apply this correction consistently to CSV import and project revision save.
   Shared JSON/shape parser errors never identify a pre-mutation refusal: they
   also arise from unusable response bytes after a server write.
- Native-granted former namespaces may be reviewed without automatically
  uploading, changing project history or granting ownership. A retry uses that
  original namespace/body/key. Disappearance of native admission fences delayed
  local completion and network results. Dismissal aborts the active request
  without deleting its retained intent.
- Preview success alone does not clear recovery. Confirmed project selection
  may clear only the exact associated original. Raw requests survive reload;
  acknowledged asset IDs associate them with confirmed project selections.
- Use actual IndexedDB semantics in storage tests. `fake-indexeddb` is a dev-only
  test dependency, pinned to 6.2.6. Primary README/package sources were acquired
  through Apify run `MfjksZG4mjsSSLurD`, dataset `kY2LwwlOovnHuwER6`;
  package licence Apache-2.0. An isolated IDBFactory is test machinery, not proof
  of native browser persistence. Native EN/DE × 1440/390 evidence must exercise
  file selection, invalid/corrected input, actual preview/attach/save/reopen,
  retained holes, navigation refusal, focus restoration and overflow.
- Deep conversion/source settings are optional details. No test console,
  raw command JSON, fabricated result or unearned engineering release enters
  the customer surface. Copy follows the site EN/DE terminology and independent
  draft/review/final record. All styling belongs to the same WindPress volume.
   The existing accessible file picker supplies the site language independently
   of the operating-system language. Required-field feedback also uses the site
   language, including the source-retention declaration. Source names use a
   documented 256-code-point display/default-name policy, with complete Unicode
   characters and a visible ellipsis when shortened; original identity stays
   unchanged. Preview area uses at most two fractional digits as display policy;
   the calculation original and declared source precision are kept separately.

Primary dependency sources:
[README](https://github.com/dumbmatter/fakeIndexedDB),
[package](https://github.com/dumbmatter/fakeIndexedDB/blob/master/package.json).

## Same-geometry 3D presentation

Native import exposed a fixed-camera composition defect: a north-facing
3–4–5 roof appears almost edge-on. Initial framing and explicit Fit must face
the selected object's roof (the first roof when nothing is selected), retain
all actual scene extents, and fit both horizontal and vertical perspective
limits at the current viewport aspect ratio. Camera composition, lens, padding
and clipping are display policies only; they never edit metric geometry,
calculate shading, create history or claim measurement accuracy. Selecting an
object does not automatically reset an orbit. An explicit Fit moves the current
camera without recreating the renderer. Resizing reframes the current extent
while keeping the viewing direction. Retry/backend changes retain their
existing renderer lifecycle and source/geometry ownership safeguards.
