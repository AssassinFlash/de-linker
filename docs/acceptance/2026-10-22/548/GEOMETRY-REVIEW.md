# Shared geometry and authoritative plan-review increment

2026-10-23. Implements the first service increment of
[the geometry contract](../../../specs/548-design-geometry.md). Full editing,
renderers and the whole A–D goal remain active.

The new Pydantic model publishes the exact browser JSON Schema. Source records,
separate rights claims, null precision, reference integrity, local ENU, upward
roof bases, stable slots and whole panel cuboids precede any rendering. New
owned saves validate this after permanent receipt recovery; conflict sketches
with safe wire data remain saveable. Existing revisions/results are untouched.
The service explicitly returns projection conflicts, unspecified inputs,
bounded-completeness state, geometry hash and checker/library identities.

Apify verified five official Shapely pages in a successful run. The implementation
uses roof-local XY; it does not mistake GEOS's Z-ignoring operations for 3D
collision. Concave extrusions are exact base/top/edge sweeps, not convex hulls.
No hidden setback, shape repair, coordinate snapping or shadow-based loss is
introduced. Source permissions remain claims rather than provider/country release.

Implementer verification: planning361 cases passed16.55s before the final added
pose-reference test; that final test and the29 existing geometry cases pass
separately. Node31/DOM45 passed before the additional browser parity case;
that added geometry case, strict TS and rebuilt source manifest are verified
separately. PHP Gateway WPCS/PHPStan and planning mypy70 modules/ruff pass.
Independent analytic dimensions and brute-force rectangles supplement the
frozen server/browser placement vectors; the latter alone are not independent
physics proof. The five-thousand-module synthetic local preview completed in
0.337s with complete review; this is one local call, not production throughput.

Actual native HTTP accepted source/reference validation, review without saving,
foreign-owner refusal, save/replay/reopen and unchanged geometry hash:1 case,
23 deselected,3.05s. The first native test wrongly tried a corrected body under
its refused intent key; native admission correctly returned409. Giving that
corrected input a new intent passes. This was a fixture expectation correction,
not an exception to immutable request semantics. No customer account, production
write, real mail, formal route cutover or browser visual claim was made here.

Fixed-source Standards and Spec review follow before this increment is accepted.

## Rejected fixed source bc528c67

Both axes FAIL. Standards independently showed that converting local corners
to absolute ENU and back erased1cm overlap at a legal1e15 origin, and that an
accepted large rotation differed between Python/JS by17.5mm. Spec reproduced
the overlap, ordinary30-degree roof-basis zero-edge false refusal, missing
periodicity (MAX_SAFE_INTEGER degrees vs31 degrees), and browser-only acceptance
of invalid acquisition dates and duplicate excluded slots. Existing30 Python,
2 ASGI and8 Node all passed despite these counterexamples. Spec's five extra
ASGI, full5000-slot budget, concave/thickness/obstacle probes otherwise passed.
Original independent probes/results are retained in `geometry-probes/`.

The correction retains a roof-local UVN pose, directly projects its full cuboid
for layout, and projects obstacle extrusion deltas without adding/subtracting
large origins. Analysis also translates large UV charts near zero, preserving
the original input/source/hash. Renderer placement now has an explicit helper
that rebases before adding local offsets; the absolute display point is not
an engineering roundtrip. Rotation uses signed remainder before the same pi
operations in both languages, with exact quadrant values. No acceptance epsilon
or arbitrary physical-angle restriction was added. Browser UTC calendar checks
and duplicate-slot refusal now match the strict server contract.

All16 rotated-roof/origin zero-edge cases and both original1cm-overlap cases
pass. The unchanged Standards angle probes now return the same Python/JS pose.
The original ordinary-scale pose reference was kept, with a numerical comparison
for its original vector fields rather than regenerating expected values to hide
the change. New local-frame/rebased tests and large-angle periodic cases are
separate. Current geometry+private HTTP140 pass2.44s;10 Node geometry cases,
strict TS, build and planning mypy70 modules pass. Final fixed-source axes and
native current-checker readback still follow; this remains a service increment.

## Rejected fixed source aead2014

Both axes confirmed the previous fixes, but FAIL remains. Unconditional UV
translation by the first roof vertex could itself turn small component UVs
into huge coordinates and erase overlap. Spec independently showed the same
polygon's cyclic start changed the answer. Spec also showed a large-UV helper
had already lost half-module detail before ENU rebasing, including59.67mm error
for a normal1.134×2.278m module.140 Python/10 Node plus independent ASGI and
budget probes passed while those new counterexamples remained.

The next correction removes automatic UV translation entirely. Binary64 UV
granularity is reported with an explicit1e-9m internal computational support
budget. Above it the original safe document remains saveable, review returns
`incomplete` plus `numerical_limit`, and the render helper raises a typed
precision refusal. This budget is not an installation/survey tolerance or
an epsilon used to accept a near miss. Large ENU origins with ordinary local
UV retain successful direct-UV review and rebased rendering. This avoids
concealing unsupported precision behind a heuristically chosen frame.
