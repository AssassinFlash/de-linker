# Roof-facing 3D framing correction

Native import exposed a presentation defect beyond the guided upload form.
The actual north-facing 3–4–5 synthetic roof has render-space normal
`[0, 0.8, -0.6]`. The prior fixed camera offset `[0.6, 0.65, 0.7]` has a normalized
dot product of about 0.089 with that normal, so it sees the surface nearly
edge-on. This is a view-composition error, not an incorrect roof dimension.
The fixed-eff native image is retained in import-native/eff8341d.

The initial camera and explicit Fit now face the selected object's roof, with
the first roof as the unselected default. Composition offsets, the existing
75-degree lens and 10% fit margin are explicitly display policy. Framing keeps
the enclosing sphere of all actual scene points, including obstacle tops, and
uses the narrower horizontal/vertical field of view for the current aspect.
Clipping scales with that sphere. A narrow phone view therefore has its width
included in the fit. Arbitrary in-plane chart rotations are covered as well as
the usual horizontal U axis.

Fit moves the current camera without recreating its GPU renderer. A resize
refits the extent while retaining viewing direction; ordinary selection or
project edits do not reset the user's orbit. Camera state never enters project
inputs or undo history. Renderer retry and explicit backend selection keep their
existing disposal/ownership path.

Technical backend names have left the primary customer controls. View options
contains the existing explicit fallback as Compatibility mode. Three EN/DE
pairs have independent draft/opposition/final records in camera-copy-*.json.
The actual renderer name remains a DOM diagnostic for native verification;
neither that name nor a grey lit roof proves shading or engineering accuracy.

Owner checks: strict TypeScript, seven camera/buffer/lifetime cases and the real
emitted-module/source-manifest check pass. The independent import correction
at eff8341d is being recorded separately; it does not accept this camera change.
New fixed-source review and EN/DE × 1440/390 native results are still required.
The full unified-workbench goal remains active.
