# Interactive metric design increment

This implements the first real editor on top of the accepted geometry service,
within the full workbench contract. It does not complete path B, the map or the
end-to-end goal. The accepted prototype remains the visual baseline.

## Required behaviour for this increment

- The native project editor exposes optional roof design for every project type.
  Its inputs.geometry is the same authoritative document used by numeric forms,
  a roof-plane SVG view, a lazy Three/R3F view, object selection, quantities and
  the owned geometry/review API. No separate render counter or scene JSON owns it.
- Manual rectangle intake asks for actual surface dimensions, pitch, down-slope
  bearing, relative origin and source/retention basis. It has no invented roof or
  module size. The first relative origin is defined as zero, not surveyed ground
  height. Source spatial precision and calibration start explicitly unrecorded.
- Existing roof boundaries/openings are editable U/V rings. Arrays retain actual
  module dimensions, STC nameplate power, mount tilt, row reset, clear projected
  gaps, lower-edge height and excluded slots. Obstacles and keep-outs have source
  references; source precision, north/anchor and declared clearances are editable.
- Property forms stage raw text until Apply; locale-specific decimals and required
  ranges are checked. Cancel explicitly abandons this property edit. Staged forms
  block project save/leave/undo so raw values cannot disappear in a global action.
  Apply is a guarded immutable command; stale before-values and changed roof
  dependents are rejected without overwriting current work. A group is atomic and
  produces one history step. Deleting a roof discloses dependent object removal.
- SVG array drag previews commit one command at pointer-up, support cancellation
  and coexist with numeric editing. Pan/zoom are view state. Stable module IDs and
  an independently usable paginated slot table support selection/exclusion.
- 3D uses explicit ENU -> (E,U,-N), rebase-before-add, full cuboid poses and instance
  IDs. Roof holes and extruded objects use real geometry. Local-plane handles
  move the array, with camera controls paused during manipulation; final movement
  enters the same command path. Camera/lighting/backend never become engineering
  inputs. The backend is read back after actual initialisation. Failure/retry
  preserves numeric/plan editing. Resources and controls clean up on unmount.
- Checks capture their input/scope, retain old output as previous after any edit,
  and cannot select current objects from stale diagnostics. Missing inputs,
  incomplete numerical/resource checks and conflicts remain explicit. Method,
  library/runtime/input hashes and numerical limits are visible. This operation
  remains a plan projection review, not engineering or shading release.
- Styling stays in the existing WindPress volume and consumes site tokens. 3D
  loads on demand; site React and other pages are not upgraded. EN/DE, 1440/390,
  keyboard/touch and saved-project readback remain required acceptance gates.

## Implementation evidence and release gates

The manual model and coordinates follow the existing geometry spec and official
library dossier; no industry setback or roof size is invented. The first direct
Drei import exposed four unrelated three-stdlib declaration conflicts under strict
TS6/exact optional properties (VR controller, line material, SVG/TGA loaders).
Instead of disabling library checks or changing global compiler flags, the editor
uses narrow lifecycle adapters around the already researched version-locked
Three OrbitControls and TransformControls. React, R3F and Three remain isolated;
Drei's installed package is not claimed as an active renderer dependency.

At this draft: strict TS and native production bundle build pass; 39 domain and
45 existing DOM checks pass, plus four new editor DOM checks. Those new checks
caught a StrictMode effect-cleanup validity race, which was corrected. They cover
locale/source intake, invalid raw-text preservation, shared exclusion quantities
and late-check staleness. The native checker4 API passed independently. Actual
GPU/drag/save/reopen/EN-DE viewport acceptance is still being performed.

Customer wording in design-copy-draft.json is an English draft pending adversarial
copy review and independent German wording. This source checkpoint is not a
release. Known whole-goal work includes map/provider lifecycle, free drawing and
advanced geometry editing, import/calibration, scenario/task/dependency integration,
engineering calculation/equipment/country qualification, files/reports and all site
consumers. These are obligations in the active goal, not post-delivery follow-ups.

### Refinements from the first fixed review

The editable roof basis requires0<=pitch<90degrees; the field and errors use
that exact domain. A renderer-only module centres roof/obstacle rings before
Float32 conversion and batches instances into128m local cells. Local-coordinate
rounding may not exceed1e-5m; distinct vertices that collapse after conversion
and dimensions that become0 are explicitly refused. These are internal display
policies, separate from the1e-9m binary64 plan-check support budget and from
source/measurement precision. Full obstacle tops and keep-outs enter framing.
The outer lazy boundary preserves staged input if the module itself cannot load.
Pointercancel, lost capture, Escape and blur abort a transform and restore orbit;
no cancellation writes a command. The renderer factory owns both attempted
backends until handoff and uses the locked runtime's public cleanup methods.
JSON signed-zero equivalence is required when acknowledging a saved document.

The next independent review exposed cancellation when handles alone unmount,
and a changed roof/reference frame during finish. Controller teardown must abort
first. A gesture uses an atomic whole-document precondition, not only an array
before-value; all geometry changes cancel its preview. Numeric edit and camera
operations continue to use their own existing paths. This conservative gesture
precondition also covers module/north/frame changes ahead of a child re-render.

Native WordPress loading exposed a separate module-identity failure: a queried
entry and an unqueried lazy back-import created two React/root identities.
The current pinned Rolldown initial-module tag emits all static dependencies in
a hashed core; the versioned WP entry owns the mount only. Generated chunks may
never import the entry. Build checking executes that actual versioned ESM graph
once before accepting assets. This does not upgrade or expose site-global React.

### Native module recovery and current boundary

An explicit 3D retry must make a new request after a failed module URL; replacing
React.lazy alone does not invalidate the browser's failed ESM module cache. The
native mount therefore publishes the scene file from its reviewed Vite manifest.
The client accepts only a query-free, credential-free SceneViewport-hash.js in
the actual entry module's own origin and directory. This configuration never
comes from a project, uploaded file, map source or user-entered URL.

The first request remains a literal lazy import so the production bundler owns
its graph. A failed request is evicted from the loader, and a subsequent explicit
retry adds a monotonic request query to that exact native scene URL. In-flight
and successful modules are reused across view changes. Missing metadata keeps
the plan and property editor available but cannot invent an executable URL.
This recovers a transient failed scene request; it is not a claim that missing
old-release assets, arbitrary dependency errors or device loss are all repaired.

Constraint footprints draw after module projections in the plan, so overlapping
modules cannot hide obstacle/keep-out selection. This changes view ordering,
not coordinates, quantities or the geometry check.

Independent b0080ec1 Spec and Standards reviews both passed the fixed manual
increment. Subsequent native fault injection exposed the failed-URL retry defect
above, separately from those source-review results. Native evidence now includes
real WebGPU and WebGL2, plane and 3D mouse moves, undo/redo, save/reopen through
the owned gateway, cancellation and EN/DE at both required viewport widths.
The browser tool cannot dispatch native touch events, so touch acceptance is
still open. Actual device loss and maximum-capacity mobile performance are also
unproven. See the acceptance record and design-native evidence; the entire
map/drawing/import/task/engineering/report/site goal remains active.
