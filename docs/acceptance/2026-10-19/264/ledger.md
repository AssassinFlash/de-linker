# #264 · German visual changes (ruled ledger)

Owner ruling 2026-10-17: a German page is German-only, and German corrections
are ruled changes against the pixel gate (ticket comment: "德语修正豁免像素门——
一律作为裁定变更记入变更台账"). English pages are not changed by this ticket:
the diff touches no English template, and the English pixel gate run below is
the proof.

Instance: `c264`, snapshot `20261019-0155` (2026-10-18 18:03 UTC), URL
`http://127.0.0.1:9150`. Live reference for "before": `https://de-linker.com`
(state at snapshot time; the German address migration of #254 changes the local
addresses, so before/after is compared by page type and content, not by URL).
Screenshots: `screens/` (1440 and 390, German; captured with the same
Chromium build, animations off, fonts and images settled; stored as JPEG for
repository size, the captures themselves were lossless):
`produkte`, `kategorie-heimspeicher`, `kategorie-wechselrichter`, `blog-index`,
`blog-artikel`, `faq-dokumente`, `vergleich`, `produkt-esa`,
`loesungsentwurf`, `proforma-anfrage`, `mein-konto`, `impressum`,
`fuer-installateur`, `gewerbespeicher`, `loesung`, `danke`, `datenschutz` —
each at `-1440` and `-390`.

## Ruled changes

| Page type | Before (live German) | After (local German) | Why |
|---|---|---|---|
| Shop `/de/produkte/` (H4) | `<title>Browse Inverters, Batteries and Systems | Linker</title>`; English description | German title "Wechselrichter, Speicher und Systeme | Linker"; German description and `og:description` | 2026-10-17 ruling: everything German-only; audit H4 |
| Category archives (H5) | Crumb `STARTSEITE / PRODUKTE / INVERTERS`, home links to `/` | `STARTSEITE / PRODUKTE / WECHSELRICHTER`, home links to `/de/`, German category names | Audit H5; the old `STARTSEITE` pointed at the English home |
| Blog index/search/archive | English date `May 29, 2026` (old deployed template) | German date `29.05.2026` (the #254 German templates already carry `d.m.Y`; verified, no further change) | Audit M1 |
| Blog single share row | `title="Share on Facebook"` etc. | `title/aria-label="Auf Facebook teilen"` etc. | Audit M1; LiveCanvas ships no German pack |
| Blog related cards | "Artikel lesen" | "Beitrag lesen" | AGENTS §3: no Artikel (article) |
| FAQ library `/de/faq-dokumente/` | "…zu den Geräten im Bestand.", "448 im Bestand", "Chint DTSU666 Katalog (EN)" | "…zu den Geräten in unserer Dokumentation.", "404 Einträge hinterlegt", "Chint DTSU666 Produktübersicht (EN)" | Audit M10/M3: "im Bestand" means in stock; no Katalog |
| Compare page `/de/produkte-vergleichen/` | "Weiter einkaufen" | "Weiter zu den Produkten" | AGENTS §3: no shopping vocabulary |
| Product page `/de/produkt/…` | "Artikelnr.:", series "ESA Series", "ET SERIES", document "… Katalog (EN)" | "Produktnr.:", "ESA-Serie", "ET-Serie", "… Produktübersicht (EN)" | Owner comment 2026-10-17 (Produktnummer); AGENTS §2 (Produkt/Modell/Serie); audit M3/M4 |
| Product and blog data | "Dieser Artikel …", "P3-S2-Artikeln", "Technische Artikel", "genaue Artikelnummer", "über den Katalog hinaus", "Dieser Shop verwendet" | "Dieses Produkt …", "P3-S2-Produkten", "Technische Beiträge", "genaue Produktnummer", "über das Sortiment hinaus", "Diese Website verwendet" | AGENTS §3; audit M3. Legal citation "Artikel 10, 12 und 14" stays (documented exception) |
| Metas (5 pages + 2 marketing pages) | English or truncated body text | Reviewed German descriptions (copy review) | Audit H4/M6 and the #253 follow-up comment |

## Unchanged

- English templates, English data, English copy: no file in `content/livecanvas/`
  without `/de/` was changed; no English product or page data was written.
- The only visual difference on German pages beyond copy is none: the share row
  keeps LiveCanvas's classes and icons, so the reader workspace's stylesheet
  draws it as before.

## English pixel gate

`tests/visual/pixel-parity.mjs` over `/`, `/products/`,
`/product-category/inverters/`, `/product/goodwe-gw80k-et-g10/`, `/blog/`,
`/hybrid-inverter-vs-ac-coupled-storage/`, `/compare-products/`,
`/faq-download/`, `/for-installer/` at 1440 and 390 (18 cases). Result:
**0 differing pixels outside the ruled dynamic regions**; the raw counts are in
`pixel-en-final2/results.json`.

Two dynamic media regions are ruled, both recorded here for the owner (AGENTS
§5 permits only real dynamic areas, each reported):

- `/for-installer/` at 1440: the two autoplaying product videos
  (`linker-bess-layout-for-planning-en.mp4`, `linker-bess-sizing-for-the-site-en.mp4`)
  show different playback frames in the two captures; the two lazy
  `.installer-pkg-photo` images differed by a 9-pixel loading band at their
  edges. Everything else on the page — including all text and the rest of the
  screenshots — is identical.
- `/hybrid-inverter-vs-ac-coupled-storage/` at 390: the site footer
  (`.tv-footer-root`, an animated entrance block) was still animating when the
  two captures were taken; the article above it is identical pixel for pixel.

The first run without these rulings is kept as
`pixel-en-first-run/results.json`: 15 of 18 cases were already 0; the three
non-zero cases are exactly the dynamic media above. No English template and no
English data file is changed by this ticket (`git diff` touches only
`content/livecanvas/de/` and German data), so the gate guards against
accidental English drift rather than proving a rewrite.

The other 16 cases, at both widths: `unmasked_different_pixels: 0`.
