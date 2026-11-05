# Workbench engineering chain, production acceptance 2026-11-05 (C line)

Executor: main session. Criterion: the unified workbench actually works for a
real customer project on production — not a page-200 claim.

**Result: PASS — full project → equipment → engineering-check chain works.**

## Real production run (guest, normal browser)

1. `/solution-configurator/` → New project → `projects/create` 200 → workspace
   with the full section model (overview/site/roof/energy/calculations/
   equipment/installation/Genie), revision 1.
2. Site and project: Country=Germany, address Berlin 10115 → Save →
   `projects/revise` 200 → **revision 2** (persisted in the overview).
3. Equipment: operating mode Grid-connected, three-phase, PV 30 kWp, 30 kWh
   usable, 15 kW continuous AC; product catalog from current Woo data
   (`products/current` 200). Selected **GoodWe GW80K-ET-G10** inverter +
   **GoodWe GW112.6-BAT-AC-G10** battery.
4. Prepare equipment selection → Save (revision 3) → **Check saved equipment
   selection** → `runs/equipment` 200, result polled via `runs/read`.

## Engineering result (real, honest)

- Converter output / Grid phases / Module count / Battery voltage:
  **checked requirements met**.
- Manufacturer pairing / Parallel arrangement / Sales unit / Usable energy:
  **further checks required** (no fabricated approval).
- Country requirements: explicitly not assessed by this calculation.
- Provisional BOM: GoodWe GW80K-ET-G10 (SKU DLK-GOODWE-GW80KETG10).

Evidence: full-page result screenshot `sc-check4.png` (local capture);
project title `SC check4 2026-11-05`.

## Notes

- Section navigation is hash-routed and works (screenshots verified); early
  text-dump confusion was a test-selector artifact, not a product defect.
- The check's "further checks required" verdicts are the intended honest
  engineering boundary (goal C: no assumed/partial release).

## Addendum (same day): energy-calculation input boundary

Continuing the same chain into Energy inputs / Energy calculation: the
scenario calculation **requires real interval inputs by design** — the interval
sources (total site load, available PV output AC, external auxiliary) are
required, and the storage parameters demand a source/assumption note. It
refuses to calculate from an annual figure alone. That is the intended honest
engineering behavior, not a defect. The full energy+report chain has native
coverage in the owned two-hour fixture (synthetic source claims, frozen
execution, per-unit trace, German report); a production customer-path run with
a real imported load profile + PVGIS generation is the remaining acceptance
step. Four test projects from this exploration were deleted through the
engine's own Workspace.delete (0 left, 46 total).

## Addendum 2 (same day): real interval-data import works, including DST validation

The Energy inputs → Import interval data chain was exercised on production with
a real 8,760-row hourly load-profile CSV (203,846 bytes):

- Column preview (`profiles/inspect` 200) and the full mapping form (timestamp/
  value/measurement point/kW/decimal/source type/interval boundaries/timestamp
  role/time zone/duration/source label/storage rights) work.
- A Europe/Berlin-local-time profile was correctly rejected with
  `422 invalid_input · local_time_nonexistent` at the 2026-03-29 02:00 DST gap
  — real timestamp validation, not a rubber stamp.
- The same profile in UTC imported successfully (`profiles/csv` 200), stored as
  a private project source (interval_seconds 3600, gross_load).

The energy scenario calculation and the planning report are the next step,
driven through the same native planner RPC the UI uses (the SPA's custom
controls make repeated browser driving slow; the RPC is the production
interface itself). All 21 exploration test projects were removed through the
engine's own Workspace.delete (0 left, 46 total).

## Addendum 3 (same day): roof/PV/report chain boundary

PV generation (both the roof-shading model and the PVGIS annual AC reference)
requires an editable roof layout: a roof face needs its drawn outline geometry
before the property panel applies, and the PV forms need modules + a
location/north reference from that layout. So the roof-canvas drawing step is a
real prerequisite of the energy/report chain, not optional for it. The
workbench's project/site/equipment-check/interval-import chain is proven on
production (above); the roof-canvas → PV → scenario → report sequence is the
remaining deep acceptance work. Ten exploration test projects were removed
through the engine's own Workspace.delete (0 left, 46 total).

## Addendum 4 (same day): roof GeoJSON import and module catalog work

- The roof layout was created on production **without canvas drawing**, through
  the native GeoJSON import: a WGS84 roof rectangle (20×10 m) → the import
  wizard (file/plane/source steps with pitch, true-north bearing, height,
  provenance and permission declarations) → `geometry/import` 200 → the roof
  outline rendered in the plan view, 1 roof face in the saved project.
- The module catalog (`products/current` → `pv_modules`) includes the Trina
  Solar TSM-460NEG9R.28 reference module from the Woo engineering overlay
  (feed overlay = 3 entries: the Trina module + 2 Nexans cables); the module
  selector populates once the catalog finishes loading. The reference product
  (Woo 8349) is published, bound to its datasheet, and `ready.engineering=true`.

So the roof and module inputs are available through the native import/catalog
paths; the module-placement → PV → scenario → report tail remains the deepest
acceptance work. Nineteen exploration test projects were removed through the
engine's own Workspace.delete (0 left, 46 total).

## Addendum 5 (same day): array-placement automation boundary

The array-creation form (name, module spec, anchor U/V, rows, columns,
rotation, tilt, gaps, height) validates every field as required at apply time;
driving it field-by-field proved fragile in automation (custom number fields
and label associations), and the Columns field repeatedly failed to retain a
value through the native/label paths tried. This is a test-tooling limitation
to solve with a proper component-level driver or a real-browser pass — not
itself a proven product defect. The workbench is verified on production through
project/site/equipment-check/interval-import/roof-import/module-catalog; the
array-placement → PV → scenario → report tail is the remaining acceptance work.
Fifteen exploration test projects were removed through the engine's own
Workspace.delete (0 left, 46 total).

## Addendum 6 (same day): array placed on the roof; weather step pending

The array creation works on production once every field is filled (the array
form reads its fields by name; the mounting-note textarea is required too):
4×6 = 24 Trina modules placed on the imported roof, 11.04 kWp declared DC
nameplate, 1 roof face, all saved in the project revision. Earlier failures
were test-side field omissions, not product defects.

The weather step (PVGIS typical-year source) is the next link; its request
button stays disabled until the location/year/database settings are prepared
and saved, and this run did not complete that gate. The remaining
weather → PV → scenario → report sequence is the deepest acceptance tail.

Production note: a Hostinger load-average spike (~788 → ~61 within minutes)
was observed during this session and decayed without action; current CPU is
mostly idle. No persistent resource incident.
