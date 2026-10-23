# Geographic source intake boundary

This increment connects an owned original, a declared coordinate/plane operation
and a prepared domain candidate. It implements the first seams identified in
the map-workbench-integration dossier. It does not complete the map/drawing,
image calibration, import UI/recovery, engineering or full A–D acceptance. These
remain required work in the active unified workbench goal.

## Coordinate contract

- The server uses installed, pinned pyproj/PROJ with explicit WGS84 geodetic
  degrees → cart → topocentric metres. Its reference includes longitude,
  latitude, ellipsoid height, method/version and height basis. Every conversion
  exposes the exact operation and library versions; this operation needs no
  datum grids. A CRS is never inferred from numbers, country or interface locale.
- A known WGS84 ellipsoid height and the zero-height horizontal convention are
  separate declarations. The latter requires h0=0 and accepts only zero input
  ellipsoid height. Curvature Up is not a measured building/roof height. The
  complete ENU inverse takes all three coordinates; substituting roof relative
  Up or discarding curvature Up changes the operation and is not allowed.
- Browser ECEF/ENU formulas are a narrow display boundary checked against frozen
  independent PROJ positions. Ellipsoid constants come from the installed EPSG
  WGS84 definition. No Mercator world unit, camera scale or empirical latitude
  factor owns engineering lengths. Numerical parity is distinct from source
  accuracy; an unknown source precision remains null.
- Horizontal E/N points intersect the explicitly declared roof plane before UV
  projection. The 3-4-5 fixture must retain 5m slope for 4m horizontal length.
  Non-invertible planes and unsupported numerical results fail explicitly.
  Existing metric UV/pose mathematics is reused unchanged; its helper accepts
  a read-only plane frame so no fictitious roof is needed during intake.

## Owned source and prepared candidate

- `geometry/import` is a private, owner-checked mutation creating an immutable
  source asset/manifest, not a project revision. It accepts raw base64 original
  bytes plus explicit format/feature/polygon, source declaration, reference and
  roof plane. It cannot fetch a URL or choose provider rights. The first format
  is `geojson_wgs84_horizontal_v1`, with longitude/latitude pairs and explicit
  horizontal-only convention. Known-height 3D geometry, another CRS, image
  calibration and provider acquisition need their respective actual operations;
  they cannot masquerade as this format.
- RFC7946 Polygon, Feature and FeatureCollection selections are supported;
  MultiPolygon requires an explicit part index. Every selected outer/interior
  ring is retained, removing only its required repeated closing coordinate.
  The original remains byte-for-byte. No bbox substitution, fill/repair, plane
  guessing, hole removal, implicit third-coordinate discard or unannounced
  multi-building merge is permitted.
- File JSON/coordinates/IDs, finite interoperable values, unit/orthogonal upward
  plane and polygon topology must validate before publishing bytes. Ambiguous
  duplicate JSON members, invalid Unicode IDs, unsupported CRS/positions, bad
  closures and invalid topology fail without an asset. Ownership precedes file
  decoding, projection and blob work. Errors do not echo private file content.
- The source is a user-owned original declaration, not proof of a licence or
  measurement. Retain/derive are explicitly attested; export is independent.
  Standard map/provider content cannot be relabelled by an automated adapter.
  This permanent intake does not implement an expiring Solar/provider store.
- The manifest preserves original content hash, exact selection/declared plane,
  input/axis/units/method, source precision/basis, projection/runtime, candidate
  geometry/hash and area in the roof plane. Source.reference_sha256 unambiguously
  references the raw original; asset metadata has its separate immutable hash.
  Engineering status stays not_evaluated.
- Existing permanent Assets/receipts own idempotency. The same key/bytes/options
  returns the original manifest without rerunning a changed projection runtime;
  changed command under that key conflicts. Stable domain IDs depend on the
  project and declared conversion, never list order in a renderer. Native quota
  treats this as an upload and checks the same private receipt before charging
  retry. A read-only asset/replay never grants another project's source.

## Project attachment and verification

- `inputs.geometry_imports` associates a named geometry source with its owned
  asset ID. Project create cannot borrow assets. Revision validation checks
  same-project ownership, source/manifest association, purpose and actual
  original-byte availability. Imported source metadata remains frozen even
  when a later project revision edits its measured geometry or source notes.
- The client validates authoritative generated options/command/selection schemas
  without coercion or defaults. Prepared output has the correct project, source,
  original/hash, plane, one roof and all holes. Its geometry and attachment enter
  one immutable history step. Undo/redo preserve unrelated brief/profile inputs.
- An empty unreferenced frame can explicitly adopt the prepared ENU reference.
  Existing geometry needs a matching anchor and declared true-north basis;
  attaching an anchor never silently rotates/repositions old geometry. Missing
  alignment is a specific refusal. A complete before-document guards against
  a changed frame before the candidate is applied; no partially attached source
  or overwritten geometry is allowed.
- Initial 4MiB original-file and existing geometry vertex limits are deployment
  resource policy, not physical roof capacity or accepted engineering accuracy.
  Browser and server policy/schema fixtures must agree. A retained source is
  distinct from a saved/confirmed project and from an engineering release.

Acceptance for this seam requires actual PROJ/analytic fixtures, real owned
Assets/HTTP/receipt/foreign-source tests, emitted/source build checks, native
WordPress gateway import→original readback→explicit revision→reopen, and both
independent review axes. UI, map/provider, EN/DE/viewport/touch and complete
workbench acceptance cannot be inferred from these kernel/API tests.
