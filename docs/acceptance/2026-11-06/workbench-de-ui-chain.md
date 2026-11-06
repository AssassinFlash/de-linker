# Workbench German (DE) UI chain, production acceptance 2026-11-06

Executor: main session, built-in browser at 1440x900 against `de-linker.com`.
Criterion: the same workbench chain a German customer runs actually completes,
including the German report file a customer downloads.

**Result: PASS — German locale, PV generation, energy scenario and the German
planning report all complete on production, and the German PDF/CSV read back.**

Evidence: `/Users/chesterjohn/de-linker-data/planner-de-chain-20261106/`
(`linker-planning-97f546…-r7-de.pdf`, 54 433 B, 4 pages;
`…-r7-de.csv`).

## What the customer did (German UI, project `97f54605…`)

1. `/de/solution-configurator/` redirects to `/de/loesungskonfigurator/`
   (`Lösungskonfigurator | Linker`). Interface is German throughout — chrome,
   project navigation (`Projektübersicht`, `Standort und Projekt`,
   `Dachplanung`, `Energiedaten`, `Energieberechnung`, `Geräte`,
   `Leitungswege der Installation`), energy tabs (`Wetterquelle`,
   `PV-Erzeugung`, `Sichtbarkeit der Direktstrahlung`,
   `Szenarioeinstellungen`, `Berechnungen vergleichen`, `Planungsbericht`,
   `Gespeicherte Berechnungen`), report form (`Nicht aufnehmen`,
   `Prüfung der Geräteauswahl`, `Ihr Logo im PDF (optional)`,
   `Planungsbericht erstellen`), and the footer incl. legal links
   (`Impressum`, `Datenschutzerklärung`, `Cookie-Einstellungen`,
   `Verkaufsbedingungen`, `Rückgabe & Erstattung`,
   `© OpenStreetMap-Mitwirkende`).
2. `Neues Projekt` → `Projektname` → `Projekt anlegen` → `Gespeichert · Version 1`.
3. `PV-Erzeugung` → `PV-Modell vorbereiten` → `PV-Modell in diesem Entwurf
   vorbereitet` → `PV für gespeicherte Eingaben berechnen` →
   **`Modellierte PV-Erzeugung 12.216,115 kWh`**,
   `Beginn 01.01.2026`, `Ende 01.01.2027` — numbers and dates correctly
   localised (thousands `.`, decimal `,`, `TT.MM.JJJJ`).
4. `Dieses PV-Profil verwenden` → `Projekt speichern` (`Version 5`).
5. `Szenarioeinstellungen` → `Szenario vorbereiten` → storage parameters
   (20 kWh / 10 kW, efficiencies, aux, standing loss) with the German source
   note → `Gespeichertes Szenario berechnen` → run `succeeded` (revision 7).
6. `Planungsbericht` → select `Eingabeversion 7` (energy) and
   `Eingabeversion 4 · PV-Erzeugungsprofil` → `Planungsbericht erstellen` →
   **`Projektplanungsbericht`** rendered → **`PDF herunterladen`** and
   **`Stückliste herunterladen (CSV)`** downloaded.

## Files read back (not a page-200 claim)

- PDF: `PDF document, version 1.4, 4 pages`, title `Projektplanungsbericht`,
  subject `Gespeicherte Projekteingaben und ausgewählte Berechnungsergebnisse`,
  author Linker Technology GmbH.
- CSV header fully German: `Projektreferenz, Eingabeversion, Menge, Produkt,
  Referenz, Lieferumfang, Mengengrundlage und Quellen, SHA-256 des
  Materialstands, Planungsstand, Einheit`; row `…,7,24,Trina Solar
  TSM-460NEG9R.28,…,PV-Referenzmodul · Projektangebot,…,Installationsmaterialien
  müssen projektspezifisch ausgelegt werden,St.` with the datasheet SHA-256 and
  the Woo product revision.

## Product defects found and fixed while running this path

1. **A direct `energy_view=pv` link silently landed on the scenario form**
   (PR #970, merged and deployed). `EnergyWorkspace` read the requested view once
   at mount and never followed later URL changes, so `PvSetup` received
   `active=false`, `products/current` was never requested, and PV preparation sat
   at `PV-Modelleinstellungen noch nicht vorbereitet` with no reason shown.
   The workspace now syncs its view on `PLANNER_NAVIGATION` and `popstate`.
   Production read-back: a full reload of the same URL now issues
   `POST /planning/products/current 200` and renders `PV-Ertragsmodell`.
2. **`just cutover deploy` failed on a slow SSH banner exchange.** The deploy
   opened its master session with a hard-coded `ConnectTimeout=10` and gave up
   after ten seconds of its own; Hostinger's shared endpoint routinely needs
   more. The ceiling now comes from `LINKER_CUTOVER_SSH_TIMEOUT` with a 30 s
   default (305 cutover tests pass). This is what finally let the UI fix reach
   production.

## Report rule the customer must satisfy (recorded, not a bug)

`report_sources` additionally requires the PV and energy results to share the
same generation profile ("report PV and energy results use different generation
profiles"). Changing the adopted PV profile therefore invalidates an earlier
energy result. The German UI states the consequence
(`Ein ausgewähltes Ergebnis passt nicht zu den gespeicherten Projekteingaben`)
but offers no one-click recompute; the customer re-runs the affected
calculation. Worth a product decision, not silently patched.

## Cleanup

The German test project was deleted through the engine's own `Workspace.delete`;
staging archives and the stale deploy checkpoint were removed, with recovery
copies kept only where the retention rules require them.
