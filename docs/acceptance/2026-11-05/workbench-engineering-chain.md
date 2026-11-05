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
