# Customer energy scenario, execution and frozen results

Continuation of the complete workbench goal, base `71b54073` (2026-10-24).
This implements the missing customer workflow over the existing owned profiles,
parameter assets, project revisions, managed EnergyKernel and durable jobs.
It adopts the observed/source-backed simulation controls and project/results
separation in `2026-10-23-modern-workbench/CAPABILITY-MAP.md` W08–W11/W14–W15;
it adds no numerical model, equipment release or default manufacturer facts.

## One project and an explicit scenario

- A calculation workspace is another section of the same application/project,
  available for residential, commercial and industrial use. Existing roof,
  site, energy intake, undo, server save and scoped draft recovery remain.
- Editable scenario settings are versioned project input, including unfinished
  numeric fields, operating periods and source notes. Blank is not zero. A
  prepared `energy_replay` references the owned battery parameter asset and the
  selected gross-load, available-PV, separate auxiliary and optional critical
  profiles. Net import and post-curtailment PV do not substitute for these.
- Storage parameters are explicitly declared scenario values with usable kWh,
  AC charge/discharge kW, separate efficiencies, internal auxiliary demand and
  exponential standing-loss coefficient. Their source note is retained. No
  nominal product capacity, hidden efficiency, loss or country value is inserted.
- Initial PV/grid/unknown-origin inventory and terminal condition are explicit.
  Operating periods name real ISO timestamps with UTC/offset, connected/outage,
  reserve, import/export cap policy, PV availability and grid-charge permission.
  One named self-consumption-with-reserve controller is explained; no unbuilt
  tariff optimiser or equipment capability is advertised. Outage simulation
  needs critical-load input and is not backup-device approval.
- All settings, meanings, units, missing inputs, model limits and expected
  outputs are available before calculation. The backend exported EnergyInputs
  and BatteryParameters schemas govern prepared values without coercion/defaults.
  The server remains authoritative for asset ownership, data/time coverage,
  physical consistency, runtime policy and calculation validity.

## Submission, recovery and tasks

- Preparing the battery asset uses one exact durable intent before dispatch;
  uncertain acknowledgements retain the original body/key/scope. Its result
  cannot overwrite settings edited in the meantime. Changes to prepared settings
  or selected profile identity require explicit re-preparation; the stale replay
  is not offered as the effective current scenario.
- Calculation uses a confirmed server revision and a durable original intent.
  Unsaved/conflicting/recovery-pending edits must be resolved first. Retry uses
  that same request, not the latest edited revision. Scope transitions check
  native grants and do not automatically submit an old guest mutation as a user.
- Query reads and polls actual durable states, with no invented progress or
  automatic mutation retry. Leaving the workspace/browser does not cancel a
  worker. Cancel is an explicit server command followed by acknowledged state;
  pause is not exposed without a durable implementation.
- Saved runs can be reopened after reload, in stable paginated history. A
  pending/unknown request remains recoverable, even if the server created a run
  before the browser received its response. Recovery-storage failure is visible
  and must not dispatch an unprotected new calculation.
- A new evaluation against an older server head returns the specific
  `evaluation_revision_changed` refusal before run/job/receipt publication.
  That refusal can retire its browser intent. A generic idempotency conflict
  cannot establish that fact and retains the exact original request. Existing
  successful receipts still replay across later input revisions.

## Result truth and presentation

- Result identity is checked against run/project/revision/input/manifest hashes,
  named model and source assets before rendering. The UI distinguishes a run
  completing from its scenario constraints and equipment/country assessment.
- The summary uses frozen gross/requested-load scope, solar supplied energy,
  grid import and defined ratios with units. Undefined values keep their reasons.
  No estimated annual figure is substituted for an interval simulation, and no
  payback, SKU approval, country release or new peak resolution is inferred.
- Historical revision and unsaved/newer-input status remain visible. Sources,
  model assumptions, definitions and pinned identities can be inspected. Old
  results remain readable and never acquire the current inputs' label.
- The follow-through to detailed windows/charts, scenario comparison, product
  qualification, full BOM and report/PDF remains in the same active full goal;
  this workflow may not mark those unimplemented consumers complete.

## Required evidence

Shared schema positive/negative fixtures; incomplete settings and explicit zero;
source/mode/coverage refusals; exact request/recovery scope and lost acknowledgement;
duplicate clicks, unmount and account transition; actual native setup → save →
enqueue → managed calculation → result/history/reload plus cancellation/failure;
all relevant input hashes and historical status; independent copy and Spec /
Standards reviews; EN/DE × 1440/390 native visual/keyboard checks. Preserve the
existing p548 project v14; use a separately owned synthetic scenario for new input.


## Saved interval exploration

The energy result exposes a lazy ECharts SVG view beside an accessible table.
The existing authenticated trace RPC keeps its original full-byte download;
paired optional offset/page_size fields request a bounded exact window under
the advertised deployment page limit. Ownership precedes trace access. The
window is bound to the run, manifest and retained trace hash and never invokes
an evaluation, aggregation, interpolation or newer source lookup.

Power curves use stored interval means, with their actual UTC start/end;
storage uses the sum of retained origin buckets at interval end. Zooming only
changes display. Previous/next and a 1-based jump select exact intervals. CSV
exports those same rows and unit-labelled columns without display rounding.
A chart loading failure leaves the table and CSV usable. Session loss hides
cached values and prevents an obsolete callback exporting another scope.
The chart inherits site font/colour tokens and sizes through WindPress.
