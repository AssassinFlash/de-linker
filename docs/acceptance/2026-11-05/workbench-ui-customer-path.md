# Workbench UI customer path end to end, production acceptance 2026-11-05

Executor: main session, driving the built-in browser (`mcp__desktop_browser__run`)
inside Kimi Code Desktop at 1440x900 against `de-linker.com`. Criterion: the
deepest workbench chain works when a real customer clicks it — not when a
script replays the same RPCs.

**Result: PASS — PV generation, energy scenario and planning report all
complete through the real UI, and the downloads read back as real files.**

Evidence: `/Users/chesterjohn/de-linker-data/planner-ui-chain-20261105/`
(`linker-planning-4e32a62dea1d429c9a668526b29f7d73-r11-en.pdf`, 53 188 B,
4 pages; `…-r11-en.csv`).

## What the customer did (browser clicks, project `4e32a62d…`)

1. `New project` → name → `Create project`; site `Country=Germany`,
   `Address Berlin 10115` → `Save project` (`Saved · revision 2`).
2. `Energy calculation` → `PV generation` → `Update parameters for current roof
   layout` → module parameters materialise from Woo
   (`Trina Solar TSM-460NEG9R.28`, `−0.29 %/°C`, `Source document · Page 2`) →
   `Overall PV model assumptions` filled → `Prepare PV model`
   (`PV model prepared in this draft`) → `Save project` (`revision 7`) →
   `Calculate PV for saved inputs`.
3. Result page: `PV generation profile · Source ready`,
   **`Modelled PV generation 12,216.115 kWh`**, `2026-01-01 → 2027-01-01`,
   8 760 intervals → `Use this PV profile` → `Save project` (`revision 9`).
4. `Scenario settings`: three interval sources `Selected in this draft`,
   storage parameters + source note legible →
   `Calculate saved scenario` → `Calculation complete · Input revision 11`:
   **solar supplied to load 12,189.22 kWh**, **grid import 54,520.27 kWh**,
   solar share 18.3 %, PV used or stored on site 100 %.
5. `Planning report` → select `Input revision 11` (energy) and
   `Input revision 8 · PV generation profile` → `Generate planning report` →
   `Report ready` → **`Download PDF`** and
   **`Download bill of materials (CSV)`**, both read back locally.

## Report content read back (not a page-200 claim)

The rendered report carried project reference, input revision, a provisional
BOM (24 pc Trina Solar TSM-460NEG9R.28, datasheet SHA-256, page 2, Woo product
revision and reference id), the PV scenario (12,216.115 kWh, 8 760 intervals,
PVGIS-SARAH3 / ERA5, 2014–2023, terrain horizon included, synthetic year 2026,
the original JRC request URL and response timestamp), the per-array model
(24 modules, 11 040 W, 15° tilt, 180° azimuth, SAPM a/b/ΔT, ASHRAE b0, retained
fractions) and the energy scenario (66,709.489 kWh load, 54,520.268 kWh import,
0 kWh export and curtailment, 18.272 % solar share, 100 % on-site use) with
frozen asset SHA-256 values.

The CSV row 1 confirmed the same provenance: `project reference`,
`Input revision 11`, `Quantity 24`, `Trina Solar TSM-460NEG9R.28`, the datasheet
SHA-256 and Woo product revision, and the honest
`Planning status = Installation materials require project-specific design`
(this is not presented as a complete balance-of-system take-off).

## Product defects found and fixed while running the real path

1. **`projects/read` 503 for a customer project.** Writing workspace blobs as
   `root` (an operator-side import) left files the service user cannot read, so
   the whole project page refused to open. Ownership restored with
   `chown -R linker-planner:linker-planner`; the read now succeeds.
2. **`products/current` 503 on a transient edge TLS abort.**
   `Publication.read()` performed a single unguarded `requests.get` against
   `https://de-linker.com/wp-json/linker/v1/publication/manifest`; the Hostinger
   edge intermittently answers a fresh handshake with
   `[SSL: TLSV1_ALERT_INTERNAL_ERROR]`, which closed product/module selection
   for the customer. It now retries connection/SSL/timeout faults (3 attempts,
   short backoff) and still fails closed on a persistent fault or an invalid
   manifest. Regression tests:
   `tests/test_publication.py::test_transient_tls_alert_recovers_without_closing_the_action`
   and `::test_persistent_transport_failure_stays_closed`.

## Cleanup

The browser project was deleted through the engine's own `Workspace.delete`
(workspace back to the 46-project baseline, 0 `SC %` projects). No test process,
browser tab or temporary copy of this run was left behind.
