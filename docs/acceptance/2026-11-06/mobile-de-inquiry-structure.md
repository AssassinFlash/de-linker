# Mobile DE inquiry page, structural walkthrough 2026-11-06

Executor: main session, built-in browser device emulation (Pixel 7 portrait,
412×915 CSS px, touch) against `https://de-linker.com/de/proforma-anfrage/`.

**Result: PASS at DOM/copy level. Pixel-level visual acceptance remains
open** — the current agent session cannot view images, so per the standing
visual rule (Computer Use acceptance required) this record covers structure,
copy and completeness only and the pixel pass must be re-run in a
vision-capable session before the mobile matrix can be called complete.

## What was checked (three scroll segments, full page)

Top: `Anfrage senden` heading, intro (`Teilen Sie uns Ihr Anliegen mit. Die
Produkte aus Ihrem Lösungsentwurf werden mitgesendet.`), `Nachricht
(optional)` textarea, `Name`, `E-Mail für die Antwort`, `Unternehmen
(optional)` — all formal German, correct labels, single-column layout.

Middle: consent sentence with `Datenschutz` link, `Anfrage senden ↗`
submit, reassurance (`Kein Konto erforderlich.`, `Wir antworten innerhalb
eines Arbeitstags.`), partner-account login prompt with `Konto erstellen`,
`Lösungsentwurf` panel (`Sie können uns auch ohne Produkte eine Nachricht
senden.`), language switcher (`Sprache Englisch/Deutsch`).

Bottom: brand line, footer accordion (`Lösungen`, `Dienstleistungen`,
`Planen mit Linker`, `Konto`, `Linker kontaktieren`), solutions list
(`Heimspeicher`, `Gewerbespeicher`, `Großspeicher`), legal row
(`Impressum`, `Datenschutzerklärung`, `Cookie-Einstellungen`,
`Verkaufsbedingungen`, `Rückgabe & Erstattung`), `© 2026 Linker. Alle
Rechte vorbehalten.`, tagline (`Produkteignung · Wechselrichter-Kompatibilität ·
Projektunterstützung`).

No missing sections, no English leftovers, no clipped/absent form fields at
this viewport. No submission was attempted here (the built-in browser is
automation-flagged by Cloudflare; mobile guest submission is covered by the
same protection client as desktop, both desktop paths proven the same day
in `inquiry-regression-check.md`).
