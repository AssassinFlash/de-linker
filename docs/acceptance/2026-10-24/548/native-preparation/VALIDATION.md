# Shared solar-task consumer checkpoint

Final source `ee667df1eaacf7d7b8f9972b0d05e8789dc565b3`, from accepted base
`83f06cafd6dbec886dd1b7ac60a0de5a799da023`. This is source and isolated component
acceptance inside the still-active complete unified-workbench goal. It does not
accept or install the unfinished native acquisition workflow.

## Verified behavior

Weather acquisition, roof-derived PV preparation and energy replay use one
durable browser intent/history path and preserve the previous database/store
identifiers. Task-specific model identity is checked before an acknowledgement
can clear its original intent. The native gateway exposes the declared starts
and owned status only, under the existing shared admission/replay policy.

Live dispatch atomically scans native-authorised recovery namespaces and writes
its original intent in one IndexedDB readwrite transaction. A second already-open
consumer with a stale empty cache cannot dispatch a replacement task; it
discovers the retained original instead. Exact retries remain possible. The
lower-level envelope writer also retains its restoration mode; the live hook
always supplies the authoritative discovery scopes.

Result readers require task-specific frozen source roles, runtime/plan/weather
bindings, ownership and published-asset consistency. Consistently changing a
role in several maps, or deleting the required weather plan from every map,
does not make it a valid result. Explicit selection rechecks the current draft
and identity, preserves unrelated edits, rejects changed roof/weather/model
inputs and invalidates prepared energy when its PV role changes. It leaves
server persistence to native Save project.

The visible source basis reads the actual owned weather asset used by the frozen
task, including JRC PVGIS, actual SARAH3/ERA5 databases, requested source-year
bounds and the synthetic calculation calendar. It explains stitched typical
months and reconstructed PV interval averages. Original source/interpretation,
saved PV settings and checksums remain expandable. Source completion does not
grant shading analysis, equipment release or country approval.

Weather progress separates provider completion, validated original retention,
published readiness, uncertain starts and stop confirmation. Browser requests
read the local journal; they do not start or poll provider work.

The app-wide Solution Configurator / by Linker and Lösungskonfigurator / von
Linker identity is retained. Linker's project workflow and editing contribution
precedes component credits. No map provider is presented as owning the system.

## Checks and their limits

- Final app source: **127 domain/data + 171 DOM tests**, all passed, zero skips
  or TODOs. `final-app-tests.txt` and `final-source-checks.json` retain results.
  Production TypeScript/build, source/build manifest, lazy-module test and
  formatting passed. No fixture page is a production build entry.
- Engine runtime source: **818 tests passed** in this turn. The later change to
  the new history test only narrowed types/assertions; its four focused history/
  native-HTTP cases passed afterward. Runtime engine source did not change in
  subsequent browser fixes. Strict source plus the two new files passed mypy
  (**159 files**); changed Python lint passed.
- PHP 8.3: **291 tests / 2,382 assertions** passed. The final route test passed
  again (**1 / 17**), changed WPCS passed and PHPStan passed.
- Catalog extraction/source coverage, all eight catalog validity checks and
  German-copy checks passed. All **67 reviewed strings** agree with the actual
  planner JSON, PO and MO. Copy draft/opposition/finals and independent German
  integration reviews are retained.
- A broader `mypy .` diagnostic remains **failed: 202 errors in 18 unchanged
  test files**. `engine-type-baseline.json` verifies each file against the base.
  This is not a green whole-repository type gate or complete-goal acceptance.

Initial failing diagnostics are retained with their verdicts: two formatting
files were fixed before final format; the PHP test docblock/parameter naming
was corrected before final WPCS. The first full DOM run's assertion expected
the superseded draft phrase; the final assertion checks the approved explicit
validation-and-preparation condition. Independent review failures were corrected
in the same goal; see `REVIEWS.md` and the original reports.

## Actual browser observation

Computer Use rendered both weather and PV consumers in EN/DE at **1440/390**.
All eight cases have document width equal to viewport width. Expanded source/
interpretation and product credits wrap within the phone viewport; explicit
selection becomes the disabled current-draft state. The German unknown-start
contact action reads **Linker kontaktieren**, with the correct mailto target;
no mail was sent.

`visual-readback.json`, AX observations and PNGs retain these cases. Rendered
source/copy/style at visual pin `68a69ab3` is byte identical to final source;
`visual-scope-audit.json` records this. The last change adds invalid-role
refusals and their regression, without changing visible output.

These are isolated React consumer fixtures: actual worker-published result
views, retained real TMY, explicitly synthetic roof/model and simulated provider
responses. They prove component rendering/interaction, not WordPress identity,
live source acquisition, installed schema support or real-site accuracy.

## Preservation and same-goal work

No new runtime/schema was installed. Read-only comparison confirms every live
table row unchanged at SHA-256
`b74d9b5e657e3180fc0182233bd1138e7a90f98fee47b3d62e1e9af4e5176295`:
schema 2, 165 projects, 228 revisions; the protected roof remains saved v14 with
input SHA-256 `8a6394917a9a9e6b91db4bfc73c0299dcedd2c51619144a5beffa1664f010288`.
The original carrier worker PID 71736 remains live with its original runtime,
execution and storage binding. No new instance, worktree or full backup was
created. Both temporary Vite listeners and their created browser tabs were
reclaimed; viewport override was reset. No physical storage saving is claimed.
The existing bounded carrier remains referenced and retains its recorded review
deadline; it is not a superseded duplicate.

The source/model entry forms, native start controls, private credential
injection and paired HTTP/worker/schema install remain required in this same
goal. Full engineering and country coverage, actual equipment compatibility,
complete parts lists/report/PDF, site/Genie/Woo/Solution draft/inquiry consumers,
migration, review environment and production readback remain required. The
broad existing type-check failure is also not waived. No new follow-up issue,
reduced product scope or completion claim replaces that work.
