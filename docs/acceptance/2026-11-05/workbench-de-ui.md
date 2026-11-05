# Workbench German (DE) UI pass, production 2026-11-05

Executor: main session, built-in browser at 1440x900 against `de-linker.com`.
Scope: verify the same workbench chain a German customer sees, and record
exactly how far it runs today.

**Result: partial. The German UI, the PV calculation and German number
formatting all work; assembling a German report did not complete because the
report refuses results whose input revision is older than the current project
revision, and the PV preparation step kept returning to "not prepared" while
the draft already equalled the saved revision.**

## What was verified (real UI, German locale)

- `/de/solution-configurator/` redirects to `/de/loesungskonfigurator/`, title
  `Lösungskonfigurator | Linker`. The interface is German throughout with no
  English leakage in the chrome, the project navigation, the energy tabs or the
  report form: `Ihre Projekte`, `Neues Projekt`, `Projektname`,
  `Projekt anlegen`, `Projektarbeitsbereich`, `Projektübersicht`,
  `Standort und Projekt`, `Dachplanung`, `Energiedaten`,
  `Energieberechnung`, `Geräte`, `Leitungswege der Installation`,
  `Wetterquelle`, `PV-Erzeugung`, `Sichtbarkeit der Direktstrahlung`,
  `Szenarioeinstellungen`, `Berechnungen vergleichen`, `Planungsbericht`,
  `Gespeicherte Berechnungen`, `Nicht aufnehmen`,
  `Prüfung der Geräteauswahl`, `Ihr Logo im PDF (optional)`,
  `Planungsbericht erstellen`.
- Footer/legal German: `Datenschutzhinweise von OpenFreeMap`,
  `© OpenStreetMap-Mitwirkende`, `Fußzeilen-Navigation`,
  `Lösungen / Dienstleistungen / Planen mit Linker / Konto / Linker kontaktieren`,
  `Heimspeicher / Gewerbespeicher / Großspeicher`.
- Project create in German: `Projekt anlegen` → `Gespeichert · Version 1`.
- PV generation completed through the German UI:
  `PV-Modell in diesem Entwurf vorbereitet` →
  `PV für gespeicherte Eingaben berechnen` →
  **`Modellierte PV-Erzeugung 12.216,115 kWh`**,
  `Beginn 01.01.2026, 00:00 UTC`, `Ende 01.01.2027, 00:00 UTC`,
  profile page `PV-Erzeugungsprofil · Quelle bereit`.
  Numbers and dates are correctly localised (thousands `.`, decimal `,`,
  `TT.MM.JJJJ`), which is the part most likely to break in a translated UI.
- Energy scenario run reached `succeeded` on the engine for this project
  (`d28e6cbe…`, input revision 3), and the run list rendered in German as
  `Eingabevorsion 3 · 05.11.26, 23:58`.

## What did not complete

Generating the German report stopped on a product rule, not on translation:
`Ein ausgewähltes Ergebnis passt nicht zu den gespeicherten Projekteingaben.`
`report_sources.require_analysis` compares the run's pinned inputs against the
**current** project inputs per field, so any earlier revision is refused. After
rebinding the project's own PV profile asset the project moved to revision 4,
which made both the PV result (revision 2) and the energy result (revision 3)
stale for reporting.

Re-preparing PV in the German UI at revision 4 repeatedly returned to
`PV-Modelleinstellungen noch nicht vorbereitet` even though
`Die PV-Berechnung verwendet den gespeicherten Eingabestand 4` was shown and
`projects/revise` answered 200 (revision 4 persisted). So either the prepare
step does not produce a draft state the panel accepts, or it does and the panel
re-derives "prepared" from a field that the saved document does not carry.
**This needs a proper root-cause fix (panel state vs. saved input), not another
UI retry** — recorded here rather than papered over.

Product question this raises (for the report rule, not the UI): a customer who
changes anything after calculating cannot include those earlier results, and
the German wording says that plainly, but there is no affordance that recomputes
the affected analyses for the current revision. In English the same rule
applies; the earlier EN run only succeeded because every binding was created
before any result was produced.

## Cleanup

The German test project was left at revision 4 with two succeeded runs while
this is investigated; it is a guest project invisible to customers. Its title
starts with `SC ` so the next cleanup sweep removes it with the same
`Workspace.delete` path as before.
