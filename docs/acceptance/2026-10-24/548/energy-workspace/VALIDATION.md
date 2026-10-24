# Energy workspace: local customer-flow acceptance

This increment connects a saved project scenario to the managed energy worker,
calculation history and an immutable result. It is **local acceptance of this
increment**, not completion of goal 548, an annual-yield validation, a product
release, a country approval or production acceptance.

The final application source is
`ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a`; the initial implementation pin is
`1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb`. Later commits repair defects found
through native use. Evidence-only commits do not change that application source.
The governing increment contract is
[`548-energy-workspace.md`](../../../../specs/548-energy-workspace.md).

## Environment and ownership

- Reused the one owned worktree, `codex/unified-planner-548`, and the existing
  snapshot-based p548 instance: WordPress 9347, engine 9348, Genie 9349. No new
  instance, worktree, dependency, account, production write or test email was
  required.
- Native actions used the existing customer, WP user 66. One explicitly named
  synthetic France/commercial project was added:
  `334e269920d540fe8573a66a1031e0be`. It is not a surveyed site, an actual client
  design or a manufacturer-backed battery configuration.
- Read-only reconciliation checks every one of the 164 pre-existing projects
  against its initial title hash, saved revision and input hash. All remain
  unchanged. The protected roof project
  `82a84c56e50c4efb8497d1bfbe106bd1` remains at revision 14 with input hash
  `8a6394917a9a9e6b91db4bfc73c0299dcedd2c51619144a5beffa1664f010288`.
- The live worker reports runtime hash
  `9b66656acb26b65b88b09a44b8508a42094059af64b49e7038eedef0d92a10a1`.
  The readback compares HTTP version, ready record, execution key, storage
  binding, live process, exact CAS bytes and real jobs. A recorded ready file
  alone is not accepted as execution proof.
- Runtime policy is unchanged. Genie and PHP process identities are unchanged;
  the engine/managed worker were intentionally restarted earlier to load the
  new backend conflict semantics. See `runtime-before.json`,
  `runtime-after.json` and `runtime-final-readback.json`.

## Actual native calculation

The customer imported `native-inputs/gross-load.csv`, `pv-available.csv` and
`aux-ac.csv` using the application's file chooser. Each contains two one-hour
intervals, beginning `2024-03-30T23:00:00Z` and `2024-03-31T00:00:00Z`, with
explicit UTC offsets. The entered project timezone is Europe/Paris; interface
language does not change it. Source descriptions explicitly identify synthetic
test data and record the declared rights. `critical-load.csv` is retained as an
unused fixture; it was not imported for this connected-grid run.

The battery's seven values were entered explicitly: usable capacity 5 kWh,
charge and discharge AC power 5 kW each, charge and discharge efficiency 0.9
each, zero internal auxiliary power, and zero standing loss. Its source note
says that this is an analytic test model, not a manufacturer or SKU release.
Initial PV/grid/unknown stored energy is zero, with an explicit basis. The
connected-grid schedule has zero reserve, unrestricted import/export, PV
charging enabled, grid charging disabled, and no terminal-energy constraint.
The native UI prepares the scenario, explicitly saves the project and submits
the confirmed saved revision. It does not fill missing values with nominal
product facts.

| Interval | Gross load | Available PV | PV direct to load | PV into battery | Battery to load | Grid to load |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First hour | 2 kWh | 4 kWh | 2 kWh | 2 kWh AC → 1.8 kWh stored | 0 | 0 |
| Second hour | 2 kWh | 0 | 0 | 0 | 1.8 × 0.9 = 1.62 kWh | 0.38 kWh |

The independent hand calculation gives 4 kWh gross load, 3.62 kWh solar supply
to load, 0.38 kWh grid import and 90.5% solar autarky. All available PV is used
directly or put into storage, so the model's PV input self-use ratio is 100%.
Charge loss is 0.2 kWh and discharge loss is 0.18 kWh. The worker's frozen
metrics and trace agree, within the reader's stated `1e-12` numeric tolerance.
No annual projection is derived from these two hours.

| Actual run | Saved revision | State | Evidence |
| --- | ---: | --- | --- |
| `2c360c4679fe41cf8bd8f874036e58c4` | 3 | Succeeded | `customer-success.json` |
| `43310088cfe74ba19bdb155fb3ce1598` | 4 | Failed, invalid input | `customer-failure.json` |
| `a0f51822d8ee4e0e98ff4112145ed767` | 5 | Cancelled | `customer-cancelled.json` |
| `14dacb74cda2451a95d00df374532af8` | 5 | Succeeded after worker resumed | `customer-success-after-resume.json` |

The successful jobs each have attempt 1 and worker `local-p548`. The first result
hash is `ea9b0e81630d6f3d52d10488f66e14ddd4a473bb473c4da1b8ae71fd7c37423f`;
the final result hash is
`3f1e5d7bd5bb67d71e321bb2ec3f1d6244d04c64810c081594364f02b13c61e1`.
The read-only reader verifies each result, manifest and trace against the
content-addressed bytes and stored job output. Both results explicitly report
equipment release and country assessment as `not_assessed`.
Its `source_pin` is the checkout used for that readback, not a claim that the
historical run was created by a later browser bundle. Actual native captures
record their loaded asset versions; worker identity and runtime hashes are
verified separately.

For the failure, the customer extended the requested period one hour beyond
the imported sources, prepared and saved revision 4, and submitted it. The
actual managed job failed with invalid input and has no result. History still
contains the earlier successful run. The end was then restored, prepared and
saved as revision 5; this is a new saved revision, not a rewrite of revision 3.

For cancellation, an owned-local operator fixture briefly held only the
verified worker process so the very short two-hour run could be cancelled
reliably through the customer interface while queued. `cancel_worker_window.py`
checks process start identity, runtime, execution key, storage binding and
generation, has a 45-second failsafe, and resumes in `finally` after checking
identity again. The recorded hold lasted about 26.3 seconds; the native cancel
received the server's real cancelled state. No job state was injected, no
customer pause capability was introduced and no execution policy was changed.
The worker is now resumed, execution is not draining, and the final ordinary
successful run proves recovery. See `worker-cancel-control.json`.

## Browser evidence and repairs

All browser interaction and captures used the native Computer Use browser.
Screenshots are rendered evidence; React/JSDOM tests are not substituted for
geometry or customer-path proof. Each complete capture has an image, AX text and
metadata with its actual URL, viewport, focus and loaded script hash. The
matrix retains the actual asset version of every capture; early captures are
not relabelled as the final source.

Native screenshot bytes are JPEG. `media-readback.json` records the extension
correction from `.png` to `.jpg` without editing or recompression. The local
`.gitattributes` preserves raw AX/stdout bytes, including text-node trailing
spaces and terminal lines; it does not relax checks for source or written docs.

| State | English 1440 | English 390 | German 1440 | German 390 |
| --- | --- | --- | --- | --- |
| Current successful result, revision 5 | `en-1440-current-result` | `en-390-current-result` | `de-1440-current-result` | `de-390-current-result` |
| Actual failed run | `en-1440-failure-final` | `en-390-failure` | `de-1440-failure` | `de-390-failure` |
| Actual cancelled run | `en-1440-cancelled` | `en-390-cancelled` | `de-1440-cancelled` | `de-390-cancelled` |

The final success matrix loads planner script version
`52fb733a2fc7884b846623f07279ab9ca6d9cb6d788c73163c09cd088c1d197b`.
Every matrix capture has page width equal to viewport width. Desktop captures
use 1440 × 1000; phone captures use 390 × 844. The complete selected-run heading,
status and saved-revision context are visible below the sticky site/project
bars. In the final successful-result matrix, focus is on the semantic result H3.
The pointer-activated cancellation capture proves the actual server state and
visible context; it is not used as a keyboard-focus assertion. The final desktop H3 begins near y=208; its complete heading context
begins near y=178, below the measured bar bottom near y=162.

Additional native evidence covers the three scenario steps and retained form
values, explicit zeroes, invalid raw `5e` text without coercion, missing-source
validation, switching views, Undo, frozen results for earlier inputs, source
records, expanding detailed records, initial history selection, reload and
language changes. In particular:

- `en-1440-error-fixed.jpg` and its AX text, `en-390-error`,
  `de-1440-error` and `de-390-error` establish the repaired error reveal. These
  were captured at their actual earlier source versions; the English desktop
  repair capture has an image and AX text only.
- `en-390-undo-validation-pass` proves Undo removes obsolete local validation
  and restores the clean saved scenario. Transport/recovery errors retain their
  separate lifetime and protected request identity.
- `en-390-earlier-result-confirmed` shows that a changed draft does not rewrite
  a successful run's frozen revision, metrics or source records.
- `de-1440-first-history-selection` and `de-1440-first-history-reload` show the
  first fully verified history choice retained as the actual run URL across
  reload and language context. A summary row alone is not treated as a receipt.
- `en-390-table-keyboard.json` records a 358-pixel table viewport and 480-pixel
  content width, `tabIndex=0`, and actual keyboard scrolling from 0 to 40 pixels.
  `en-390-sources-loaded` supplies the visible source-table screenshot. The
  German phone source capture establishes data/width but is not claimed to show
  the complete table above the fold.
- `de-1440-whole-system-identity-readback` shows the system-level
  “Lösungskonfigurator · von Linker” identity and Linker's project/editing/save
  responsibilities, with software/data credits separately expanded below it.
  Provider credits remain specific to their contribution. This does not claim
  that every capability in the destination has already shipped.
- `de-handoff-original-roof` returns the browser to the protected original roof
  project, plan view, saved revision 14, with no browser console errors. The
  existing project was not edited or saved during this read-only smoke check.
  `de-1440-original-roof-map` proves the lazy map workspace loaded; street-map
  tiles were not requested during that check and are not claimed as loaded.

Native use found actual defects, which were fixed before the final captures:
errors outside the viewport after a long form; selected-result heading and
revision context hidden by asynchronously measured sticky bars; stale local
validation after Undo; and an implicit first history choice lost on refresh.
The shared reveal helper measures the live bars, reveals the complete heading
context and performs one guarded late correction while the same target retains
focus and native project admission remains current. Polling does not keep
moving focus. Parameter labels, units and fraction/percent presentation now
share one module between scenario entry and frozen input display.

**Failed intermediate evidence remains failed.** The following captures are
retained to explain the diagnosis, not counted as passing acceptance:

| Capture | Disposition |
| --- | --- |
| `en-1440-incomplete.jpg` | Original missing validation message below the viewport |
| `en-1440-result-initial` | Initial selected result outside visible clearance |
| `en-1440-result` / `en-1440-result-fixed` | Heading context at about y=105, occluded by bars |
| `en-1440-result-reload-pass` | H3 visible, but complete revision/eyebrow context still clipped |
| `en-1440-result-final` | Late bar timing still occluded complete heading context |
| `en-1440-failure` | Immediate resize capture was occluded; superseded by fresh `en-1440-failure-final` |
| `en-390-earlier-inputs` | History still loading; superseded by `en-390-earlier-result-confirmed` |

`en-1440-result-19be` is the first complete-heading clearance pass. The final
four language/viewport success combinations above supersede it for current-result
acceptance. File names containing “pass”, “fixed” or “final” are historical
names; this disposition, their actual contents and later evidence govern.

## Verification and review boundaries

- Final planner checks: **115 domain/data tests plus 157 React/JSDOM tests,
  272 passed**, zero failed. Build/type check, exact source manifest and actual
  emitted lazy-module graph check passed. Raw final logs are
  `node-tests-final.log` and `build-final.log`.
- Engine suite at the initial implementation pin: **615 passed**. No backend
  source changed in the subsequent UI repairs. `engine-tests.log` records it.
  These are the existing model/contract tests, not certification of arbitrary
  products or every country's engineering rules.
- Independent Spec and Standards review covered the original full change and
  all subsequent source repairs, ending at the exact final pin with zero open
  findings. See `REVIEWS.md`. They do not independently certify the native
  viewport matrix or accept the entire goal.
- English copy was drafted and challenged against the actual model. Formal
  German was authored and independently challenged; all six German corrections
  were applied. Final 187 new German entries match PO/MO/native JSON; the
  existing German prefix remains unchanged. See `COPY-FINAL.md` and both copy
  reviews.
- Styles were installed and generated through the existing WindPress volume
  and native Generate action. `native/windpress-readback.json` verifies the
  847,448-byte generated cache and exact planner volume/source hash. No second
  CSS pipeline or PHP layout was introduced. The admin screenshot was moved
  outside the repository; it is not part of the evidence to push.
- The acceptance reader and bounded local worker fixture pass Ruff checks.
  The reader is read-only and keeps the service credential only in process
  memory; it neither prints nor stores it. The fixture's already recorded
  execution is retained and was not rerun merely to check syntax.
  Its analytic comparisons now set `rel_tol=0.0` explicitly with
  `abs_tol=1e-12`; both successes were re-read and passed this absolute bound.
  See `reader-final.log`.

Storage closure removed the 46,360-byte planner backup only after proving it
was an exact duplicate of the committed base and the active volume matched
current source. The private admin screenshot was moved, not copied. Consumed
one-use login URL files are absent. One worktree and one active p548 instance
remain needed for the complete goal. See `storage-readback.json`; its observed
free-space delta is not attributed to this deletion because other sessions
share the volume.

## Remaining destination work

The full goal remains active. The complete roof/location/module-to-PV-series
chain still needs validated generation, shading and source-accuracy treatment.
Detailed time-series analysis and comparison, complete equipment/manufacturer
and country-rule release, truthful product selection, complete BOM/report/PDF,
all affected site/Genie/Woo/Solution draft/
inquiry consumers, old-data and URL migration, review-site validation and
production deployment/readback still require their own finished implementation
and evidence. A two-hour synthetic France/C&I run does not close these gates,
and an explicit `not_assessed` result is not evidence that those required
capabilities may be omitted.
