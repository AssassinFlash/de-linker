# PV parameters and shared saved-project start

Reviewed source: `310bf2f4b6cd9d5a7c8bfcf35965c38905ef08be`.
Accepted base: `c7232e3d91e80d87887ca3d1d398f92852dec021`.

The common energy workspace now exposes module, array-model and grouped
conversion parameters, prepares their draft against the current active roof
layout, and starts PV through the existing saved-revision/durable-request/history
workflow. Explicit layout alignment retains matching parameters, creates empty
entries and does not invent physical coefficients or converter assignments.
Each active array must belong to exactly one conversion group. Model stages,
units, source notes and the unshaded-reference scope are visible. The governing
contract is [solar settings](../../../../specs/548-solar-settings.md).

The actual TypeScript compiler, private ASGI service and registered real Worker
were exercised together with a synthetic roof and retained original weather:
Save returned 200; the minimal saved-revision PV command produced all 8,760
intervals; exact retry retained its original run; injected command inputs were
rejected. The owned weather source and prior history remained intact. This is
an executable integration fixture, not a survey, shading calculation, hardware
release, country approval or field-accuracy validation.

Independent Spec review found a user-visible numerical defect: entering 57%
or 56% could display binary floating-point residue. Decimal exponent scaling
now preserves the declared number without an arbitrary rounding cutoff, and
NumberField preserves a locally typed partial value across parent echoes. Both
PV and existing storage efficiency controls use the same unit boundary. The
actual German control reproducer now displays exactly `57` and `56`, stores
`0.57` and `0.56`, and retains signed zero, trailing separators and declared
additional precision. Independent final Spec findings: zero. The independent
Standards P3 concerning module-parameter source comments was also corrected;
final documented breaches: zero. See [independent reviews](REVIEWS.md).

Verification:

- Full application: 137 domain/data and 178 DOM tests passed, zero failures,
  skips or TODOs. Formatting, production build and source/manifest binding pass.
- Related backend: 135 tests passed. After the decimal correction, both actual
  TS-to-ASGI/Worker contracts passed again. Normal strict typing passes for
  159 source/changed-test/export files; Ruff checks pass.
- The earlier whole-engine type run still has 199 errors in 16 other test
  files. Every affected file's current hash was checked against that run and
  remains unchanged. This is retained as an unresolved whole-goal obligation,
  not described as green CI or waived: `engine-whole-type-scope.json`.
- All 73 customer messages have draft/opposition/final records and independent
  formal German wording. Source/script coverage, eight catalog validity checks,
  German-copy checks and actual installed WordPress i18n evaluation all pass.
- Computer Use covers EN/DE at requested 1440 and 390 widths: three parameter
  groups, empty parameters, invalid/partial input, prepare-before-save gating,
  saved-revision start and common history. Nineteen captures are retained.
  Browser warning/error count is zero; measured client/scroll widths agree.
  A hard-broken German mobile step label was shortened and photographed again.

The visual fixture uses real application components and current catalogs with
synthetic roof/model values, retained original weather and simulated transport.
Earlier EN captures remain applicable because production JavaScript/styles are
byte-identical between the decimal-fix pin and final pin; final DE step views
were recaptured. See `visual-scope-audit.json` and `visual-readback.json`.
This does not prove an installed native HTTP/worker pair or provider acquisition.

Read-only native preservation checks confirm schema 2, all 165 projects and
228 revisions, protected project revision 14, and the unchanged canonical
all-table-row hash
`b74d9b5e657e3180fc0182233bd1138e7a90f98fee47b3d62e1e9af4e5176295`.
The WordPress plugin remains linked to this owned worktree's built frontend;
the new paired services/schema are not installed in this increment. No Actor,
production deployment, mail, new instance/worktree or full backup was created.
The temporary Vite service and created browser tab were reclaimed, the viewport
override reset, and the user's original tab retained. Ten redundant successful
logs were removed after their final replacements passed; unique initial failure
and independent reproduction evidence remain.

Next native integration requires private provider credential wiring, a verified
recovery point and paired immutable HTTP/worker/schema installation, then actual
weather → selection/save → PV → selection/save → energy replay. Novice source
and model discovery, near shading/electrical design, equipment/manufacturer and
European-country coverage, complete BOM/report/PDF, site entries and all
Genie/commerce/inquiry/account consumers, migration, review environment and
production readback remain within the same full delivery goal. The map remains
open; this evidence does not reduce its scope.
