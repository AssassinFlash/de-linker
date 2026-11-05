# Workbench PV→scenario→report tail chain, production acceptance 2026-11-05

Executor: main session. Criterion: the deepest workbench chain
(PV generation → energy scenario → planning report) completes on production
through the same RPC surface the browser client uses — not a claim from
component tests.

**Result: PASS — project → roof → array → weather → PV → energy → report PDF,
all on production, run states `succeeded`, artifacts read back.**

Evidence: `/Users/chesterjohn/de-linker-data/planner-pv-chain-20261105/`
(full run log `sc-full.log`, report `sc-report.pdf`, PV payload
`pv-generation-payload.json`).

## Real production run (guest session, Chrome, de-linker.com)

Project `6eb4419e…` (cleaned up after acceptance):

1. UI: New project → site (DE, Berlin) → roof GeoJSON import (20×10 m,
   pitch 15°) → Trina TSM-460NEG9R.28 module → 4×6 array, 11.04 kWp.
2. RPC `projects/revise` (weather_acquisition from the geometry anchor) →
   `runs/weather` **succeeded** (PVGIS 5.3 TMY 2014–2023, SARAH3/ERA5).
3. RPC `products/current` → `pv_modules[0].parameters` **verbatim** with only
   `module_spec_id` swapped → `projects/revise` (pv_generation + pv_preparation)
   **200, revision 7** → `runs/pv` **succeeded**:
   **12 216.115 kWh/a** (≈1106 kWh/kWp·a, plausible for Berlin), 8760 hourly
   intervals, `pv_available_ac`, unshaded reference scenario.
4. `profiles/csv` ×2 (8760-row gross_load fixture, synthetic zero aux_ac) →
   `battery/scenario` (20 kWh / 10 kW explicit AC scenario) → revise
   (`profile_selections` + `energy_replay`, revision 8) → `runs/energy`
   **succeeded**: gross load 66 709 kWh, grid import 54 520 kWh,
   charge/discharge conversion losses 12.25/11.48 kWh, aux unserved 0,
   metric definitions pinned in the run result.
5. `runs/report` (locale en, energy_run + pv_run) **succeeded** →
   `assets/content` → **PDF 1.4, 4 pages, 53 197 bytes** read back.

## Root causes found while unblocking this chain (all three test-side, fixed)

1. **revise 422 `invalid_input` with no fields**: domain check
   `ProductSources.check_pv_inputs` requires `pv_generation.modules[i]` to
   equal the Woo-maintained reference template **field-by-field** (note,
   datasheet sha, `woo` binding, gamma). Hand-typed parameters are rejected
   by design — this is the "Woo is the only product source of truth" rule
   enforced at the domain layer. Correct construction (same as the UI's
   `compilePv`): spread `products/current.pv_modules[0].parameters`, replace
   only `module_spec_id`.
2. **runs/pv worker `invalid_input`**: pvlib SAPM cell thermal constants must
   be the documented open-rack values (a=−3.47, b=−0.0594, ΔT=3); positive
   a/b explodes cell temperature and the DC series goes negative
   (`PvModelDomainExceeded`). Canonical values mirrored from the engine's own
   recorded scenario fixture.
3. **runs/pv worker `invalid_input` (layout gate)**: `generation_arrays`
   requires a complete, conflict-free geometry review. The GeoJSON import
   maps the roof outline into the **negative u/v quadrant**; an array at the
   default origin (0,0) lays every panel outside the roof polygon
   (`panel_outside_roof` ×24). Array origins must be placed inside the
   imported roof's u/v extent (here −7,−8).

The exact worker-side exception is reproducible off-production with the
release venv against the workspace blobs (`generate_pv` trace) — used to
pin causes 2 and 3 instead of guessing from stripped error codes.

## Cleanup

All 8 `SC %` test projects deleted via the engine's own `Workspace.delete`
(guest actor per project); workspace back to the 46-project baseline,
0 test projects. VPS `/tmp` artifacts removed; disk 5.1/48 G used,
load ≈0.02.
