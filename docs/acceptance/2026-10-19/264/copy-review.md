# #264 · German copy review

Basis: AGENTS.md §3 (Produkt / Modell / Serie; no Artikel as article, no Katalog,
no Warenkorb/Einkaufswagen, no Shop/einkaufen; Sie form, de_DE_formal; no
"nicht …, sondern", no three-part rhetorical lists), the 2026-10-17 ruling that a
German page is German-only, and the live German wording in the 2026-10-19
snapshot (instance `c264`, snapshot `20261019-0155`).

Method: EN source fixed first; every German sentence written independently, not
translated word for word. An adversarial reviewer checked the drafts against the
rules, the live German terms and the #254/#176 copy precedents; every finding
below is answered with a disposition and the final string. The rendered German
pages were then read back on `c264` (`curl` + WP-CLI) to confirm each final
string is the one the visitor sees.

## Dispositions

| # | Item | Draft | Review | Final (DE) |
|---|---|---|---|---|
| 1 | Shop meta description (H4) | "…nach Marke – oder finden Sie ein Produkt über Produktnummer…" | CHANGE: "per Produktnummer" is the idiomatic minimal fix; the inserted dash was not in the live sentence. | "Filtern Sie Wechselrichter, LFP-Batterien, Komplettsysteme, Zähler und Steuerungen nach Marke oder finden Sie ein Produkt per Produktnummer oder Typenschildfoto. Nettopreise für Partner." |
| 2 | Cart (Lösungsentwurf) meta description | "Prüfen Sie die Positionen … und prüfen Sie die Summen." | CHANGE: "Prüfen … prüfen" repeats the verb; "Überprüfen … prüfen" is the live rhythm. | "Überprüfen Sie die Positionen in Ihrem Lösungsentwurf, passen Sie die Mengen an und prüfen Sie die Summen. Freigegebene Partnerkonten sehen Nettopreise, Steuern und Lieferbedingungen vor der Proforma-Anfrage." |
| 3 | Proforma request meta description | "…und die Zahlungsart, und senden Sie dann Ihre Anfrage. Die Unterlagen dazu folgen…" | CHANGE: double "und"; "follow to" was rendered literally. | "Bestätigen Sie Ihr Konto, Ihre Rechnungs- und Lieferadresse, Ihre Umsatzsteuerangaben und die Zahlungsart; senden Sie dann Ihre Anfrage. Die Unterlagen stellen wir in Ihrem Partnerkonto bereit." |
| 4 | My account meta description | "Melden Sie sich an für Kontopreise, …" | CHANGE: "sich anmelden für" is unidiomatic; "Kontopreise" is not the site term. | "Melden Sie sich an, um Preise für Ihr Konto, Ihre Anfragen, Adressen und Unterlagen zu sehen, oder registrieren Sie Ihr Unternehmen. Nur für Gewerbekunden; jede Registrierung wird geprüft." |
| 5 | For installer meta description | "…mit je Bestellung angeforderten Netzanschlussunterlagen…" | CHANGE: "Bestellung" is the order vocabulary the site does not use; "Netzanschlussdokumenten" is the live term. | "Komplette Speicherpakete, im Lösungskonfigurator ausgelegt, mit den für Ihre Anfrage angeforderten Netzanschlussdokumenten, Lagerware in Deutschland und bestätigten Versandterminen." |
| 6 | Commercial storage meta description | "…Netzanschlussunterlagen auf Anfrage." | CHANGE: "auf Anfrage" weakens "requested" to "available on request". The reviewer proposed "fordern wir an"; the passive keeps the actor unstated (the source does), so the final uses the passive. | "C&I-Systeme von GoodWe, SAJ und Pylontech für Lastspitzenkappung, Eigenverbrauch und Notstrom, im Lösungskonfigurator anhand Ihres Lastprofils ausgelegt. Netzanschlussdokumente werden je Anfrage angefordert." |
| 7 | Blog share labels | "Auf %s teilen" | PASS. | "Auf %s teilen" (Facebook, WhatsApp, Telegram, Twitter) |
| 8 | Blog related-card link | "Beitrag lesen" | PASS. | "Beitrag lesen" |
| 9 | FAQ library subtitle | "…zu den hinterlegten Geräten." | CHANGE: "hinterlegte Geräte" is ambiguous; "in unserer Dokumentation" states the "on file" meaning. | "Datenblätter, Handbücher und Handelsregeln zu den Geräten in unserer Dokumentation." |
| 10 | FAQ counter | "%d hinterlegt" | CHANGE: a bare participle with no counted noun. | "%d Einträge hinterlegt" |
| 11 | Compare page button | "Weiter zu den Produkten" | PASS. | "Weiter zu den Produkten" |
| 12 | SKU labels | "Produktnr." / "Produktnummer" | PASS. | "Produktnr." (PDP, picker), "Produktnummer" (item-number label, search placeholder) |
| 13 | Shipping sentence | "Paketpreis für ein lieferfähiges Produkt … bei Absenden." | CHANGE: "lieferfähig" implies availability/stock, which is a separate ruled concept; "bei Absenden" lacks its object. | "Paketpreis für ein versandfähiges Produkt innerhalb Deutschlands: %s bei Absenden der Anfrage. Fracht für mehrere Produkte wird gesondert bestätigt." |
| 14 | Series labels | "ET-Serie", "ESA-Serie", "STS-Serie", "(dreiphasig)", "(einphasig)" | PASS. | As drafted. |
| 15 | Document title | "Produktübersicht" | PASS; "Produktprogramm" would name the manufacturer's lineup, not the document. | "Produktübersicht" (e.g. "Chint DTSU666 Produktübersicht (EN)") |
| 16 | Blog article link | "Beitrag lesen" (was "Artikel lesen") | PASS. | "Beitrag lesen" |
| 17 | Home page / thank-you page item terms | "genaue Produktnummer"; "Technische Beiträge" | PASS; these are the §3 words for the old "Artikelnummer" and "Technische Artikel". | "genaue Produktnummer"; "Technische Beiträge" |
| 18 | Product data item terms | "Dieses Produkt ist ein Schrank"; "ein eigenes Produkt"; "P3-S2-Produkten"; "Produktnummer (Serie)"; "Katalog" → "Produktübersicht"/"Sortiment" | PASS. The legal citation "Artikel 10, 12 und 14" stays (banned-de.json's documented exception). | As drafted; rendered pages carry no other "Artikel" or "Katalog". |

## Rejected or deferred

- Reviewer's active "Netzanschlussdokumente fordern wir an." — rejected for #6:
  the English sentence does not name the actor, and the passive keeps the claim
  true without adding one.
- Reviewer's length note: the German descriptions run 170–204 characters, like
  the corresponding English ones (153–169). The ticket asks for German
  descriptions where there were none or where the German was truncated body
  text; shortening the English-aligned facts would change the message. Kept.
- Share labels: #254's reader toolbar hides the link text and draws icons; the
  German template still needs a German accessible name, so the server writes
  "Auf … teilen" into `title`/`aria-label` and the template script no longer
  overwrites it.

## Rendered evidence (instance c264, snapshot 20261019-0155)

- `/de/produkte/` — title "Wechselrichter, Speicher und Systeme | Linker";
  description = item 1 (standard and `og:description`).
- `/de/loesungsentwurf/`, `/de/proforma-anfrage/`, `/de/mein-konto/` — descriptions 2–4.
- `/de/fuer-installateur/`, `/de/loesung/gewerbespeicher/` — descriptions 5–6
  (previously truncated body text).
- `/de/batteriegroesse-heimspeicher-notstrom/` — "Auf Facebook teilen",
  "Auf WhatsApp teilen", "Auf Telegram teilen", "Auf Twitter teilen",
  "Beitrag lesen", date `29.05.2026`.
- `/de/faq-dokumente/` — subtitle 9, counter "404 Einträge hinterlegt",
  "Chint DTSU666 Produktübersicht (EN)".
- `/de/produkte-vergleichen/` — "Weiter zu den Produkten".
- `/de/produkt/goodwe-esa-gw10k-eha-g20-10-kw-einphasiges-leistungsmodul/` —
  "Produktnr.:".
- `/de/produkt-kategorie/heimspeicher/` and `/de/produkt-kategorie/wechselrichter/`
  — "ESA-Serie" / "ET-Serie" in the family cards.
- German sitemap scan (151 URLs): zero occurrences of `Katalog`, `Warenkorb`,
  `Weiter einkaufen`, `Dieser Shop`, `Share on`, `Artikelnummer`; the only
  `Artikel` left is the legal citation `Verordnung (EU) 2023/1542 Artikel 10, 12
  und 14`.
