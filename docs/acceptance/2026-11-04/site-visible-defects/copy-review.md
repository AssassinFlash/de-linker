# Site-visible defects batch — ordering/Bestellung to inquiry workflow copy review

Date: 2026-11-04

## Surfaces

- LiveCanvas header partials:
  - `plugins/linker-commerce/content/livecanvas/partials/header.html` (lines 164, 266)
  - `plugins/linker-commerce/content/livecanvas/partials/de/header.html` (lines 164, 266)
- Trade FAQ data source:
  - `plugins/linker-commerce/data/faq-trade.json`
- Paired WordPress pages (`tools/migrate/marketing-controls.py`):
  - Residential Storage: EN `749` (`/solution/residential-storage/`) and DE `6923` (`/de/loesung/heimspeicher/`)
  - For Installers: EN `826` (`/for-installer/`) and DE `6869` (`/de/fuer-installateur/`)
  - FAQ & Documents: EN `932` (`/faq-download/`) and DE `6863` (`/de/faq-dokumente/`)

## Business and copy ruling alignment

Per `AGENTS.md` §1, §2 (2026-10-07, 2026-10-09, 2026-10-17) and §3:

1. **Single customer workflow**: Product categories and products → Solution draft (`Lösungsentwurf`) → Inquiry presented as a Proforma (`Anfrage` / `Proformarechnung`) → offline completion. Self-service online ordering (`ordering` / `Bestellung`), checkout, and online warranty forms (`Open Warranty & Replacements from your order`) do not exist on the site.
2. **Preserve marketing pull and technical credibility**: Keep the original section structure, contractor-facing benefits, compatibility-list verification guidance, and German warehouse dispatch facts while replacing self-service `ordering`/`Bestellung` claims with the actual inquiry and proforma workflow.
3. **Independent German authoring (`de_DE_formal`)**: All German strings use natural `Sie`-form B2B trade terminology (`Projektanfragen`, `Anfrage`, `Proformarechnung`, `Projektunterlagen`) without banned words (`plugins/linker-i18n/data/banned-de.json`) or artificial contrast structures.

---

## 1. Header Partials (`header.html` & `de/header.html` lines 164, 266)

### Initial draft

- EN: `Product selection, technical support and project inquiries`
- DE: `Produktauswahl, technischer Support und Projektanfragen`

### Adversarial review & resolution

- **Hard Stops 1–9 check**: Plain 1-second B2B navigation sublabel under `For Installers` / `Für Installateure`, parallel to the adjacent `For EPCs` / `Für EPCs` sublabel (`Project quoting, delivery and after-sales coordination` / `Projektangebote, Lieferung und After-Sales-Koordination`). No jargon, no homework imperative, no defensive negation.
- **Verdict**: PASS.

### Final copy

- EN: `Product selection, technical support and project inquiries`
- DE: `Produktauswahl, technischer Support und Projektanfragen`

---

## 2. Residential Storage (`749` EN / `6923` DE)

### Initial draft

| Location | Original EN / DE | Initial draft EN / DE |
| --- | --- | --- |
| Capability card 4 | `Support after the Order` / `Support nach der Bestellung` | `Support after Delivery` / `Support nach der Lieferung` |
| Registration documents | `Datasheets for the exact models in the order, and the unit certificates requested for registration with the local grid operator.` / `Datenblätter für die genauen Modelle in der Bestellung und die für die Registrierung beim örtlichen Netzbetreiber angeforderten Einheitenzertifikate.` | `Datasheets for the exact models in your inquiry, and the unit certificates requested for registration with the local grid operator.` / `Datenblätter für die genauen Modelle Ihrer Anfrage und die für die Registrierung beim örtlichen Netzbetreiber angeforderten Einheitenzertifikate.` |
| Section eyebrow | `HOW ORDERING WORKS` / `SO FUNKTIONIERT DIE BESTELLUNG` | `FROM INQUIRY TO DELIVERY` / `VON DER ANFRAGE BIS ZUR LIEFERUNG` |
| Stage 03 tab & heading | `Order confirmation` / `Auftragsbestätigung` | `Proforma & availability` / `Proforma & Verfügbarkeit` |
| Stage 03 body & image alt | `Check the home inverter, battery and meter on Linker before you order` · `Your order is checked against stock in Germany, and you get a shipping date you can plan around.` / `Prüfen Sie den Heim-Wechselrichter, den Batteriespeicher und den Zähler auf Linker, bevor Sie bestellen` · `Ihre Bestellung wird gegen den Lagerbestand in Deutschland geprüft, und Sie erhalten ein Versanddatum, mit dem Sie planen können.` | `Check the home inverter, battery and meter on Linker before sending your inquiry` · `Your inquiry is checked against stock in Germany, and you receive a proforma invoice with a shipping date you can plan around.` / `Prüfen Sie den Heim-Wechselrichter, den Batteriespeicher und den Zähler auf Linker vor Ihrer Anfrage` · `Ihre Anfrage wird gegen den Lagerbestand in Deutschland geprüft, und Sie erhalten eine Proformarechnung mit einem Versanddatum, mit dem Sie planen können.` |
| FAQ 1 (mixed brands) | `Combinations are sold as listed packages with the compatibility lists on file; check the pairing before ordering.` / `Kombinationen werden als gelistete Pakete mit den hinterlegten Kompatibilitätslisten verkauft; prüfen Sie die Kombination vor der Bestellung.` | `Combinations are supplied as matched packages with the compatibility lists on file; check the pairing before sending your inquiry.` / `Kombinationen werden als abgestimmte Pakete mit den hinterlegten Kompatibilitätslisten geliefert; prüfen Sie die Kombination vor Ihrer Anfrage.` |
| FAQ 3 (sizing) | `Once saved to your Partner Account, you can send the Project to Linker for a quote. Check the pairing against the compatibility lists on file before placing the trade order.` / `Nach dem Speichern in Ihrem Partnerkonto können Sie das Projekt für ein Angebot an Linker senden. Prüfen Sie die Kombination vor der Handelsbestellung anhand der hinterlegten Kompatibilitätslisten.` | `Once saved to your Partner Account, you can send the project to Linker for a quote. Check the pairing against the compatibility lists on file before sending your inquiry.` / `Nach dem Speichern in Ihrem Partnerkonto können Sie das Projekt für ein Angebot an Linker senden. Prüfen Sie die Kombination vor Ihrer Anfrage anhand der hinterlegten Kompatibilitätslisten.` |
| FAQ 5 (grid documents) | `Linker requests the certification package for low-voltage grid connection with the German Verteilnetzbetreiber (DSO) for your order:` / `Für Ihre Bestellung fordert Linker das Zertifizierungspaket für den Niederspannungsanschluss an das Netz des zuständigen deutschen Verteilnetzbetreibers (VNB) an:` | `Linker requests the certification package for low-voltage grid connection with the German Verteilnetzbetreiber (DSO) for your inquiry:` / `Für Ihre Anfrage fordert Linker das Zertifizierungspaket für den Niederspannungsanschluss an das Netz des zuständigen deutschen Verteilnetzbetreibers (VNB) an:` |
| FAQ 6 summary | `How do trade partners access net pricing and ordering?` / `Wie erhalten Handelspartner Zugang zu Nettopreisen und Bestellungen?` | `How do trade partners access net pricing and project quotes?` / `Wie erhalten Handelspartner Zugang zu Nettopreisen und Projektangeboten?` |

### Adversarial review & resolution

- **Review check**: FAQ 6's answer body already stated `You can add equipment to your Solution draft and send an inquiry with or without an account. Our team prepares the quote and agrees the next steps with you.` Updating the summary from `net pricing and ordering` to `net pricing and project quotes` (`Nettopreisen und Projektangeboten`) aligns the question with its existing answer.
- **Stage 03 check**: Replacing `Order confirmation` / `Auftragsbestätigung` with `Proforma & availability` / `Proforma & Verfügbarkeit` accurately reflects the proforma response step between `02 · Quote` and `04 · Dispatch`.
- **Verdict**: PASS. Final copy matches initial draft.

---

## 3. For Installers (`826` EN / `6869` DE)

### Initial draft & final copy

| Location | Original EN / DE | Final EN / DE |
| --- | --- | --- |
| Trust strip label | `Warehouse stock in Germany, confirmed dispatch dates, and project documentation with the order.` / `Lagerbestand in Deutschland, bestätigte Versandtermine und Projektdokumentation mit der Bestellung.` | `Warehouse stock in Germany, confirmed dispatch dates, and project documentation with your inquiry.` / `Lagerbestand in Deutschland, bestätigte Versandtermine und Projektdokumentation zu Ihrer Anfrage.` |
| Tool / stage grid compliance | `...requested for your order.` / `...für Ihre Bestellung angefordert.` | `...requested for your inquiry.` / `...für Ihre Anfrage angefordert.` |
| Warranty stage | `...using your original project and order records.` (`Backed by original project order records.`) / `...anhand Ihrer ursprünglichen Projekt- und Bestelldatensätze.` | `...using your original project records.` (`Backed by original project records.`) / `...anhand Ihrer ursprünglichen Projektunterlagen.` |
| Timeline Stage 02 | `...with the compatibility lists and wiring references on file to check before ordering.` / `...die hinterlegten Kompatibilitätslisten und Verdrahtungsunterlagen prüfen Sie vor der Bestellung.` | `...with the compatibility lists and wiring references on file to check before sending your inquiry.` / `...die hinterlegten Kompatibilitätslisten und Verdrahtungsunterlagen prüfen Sie vor Ihrer Anfrage.` |
| Timeline Stage 04 tab & panel | `Order & Delivery` · `STAGE 04 · ORDER & DELIVERY` · `Orders are checked against stock in Germany and dispatched with a confirmed delivery date.` / `Auftrag & Lieferung` · `PHASE 04 · BESTELLUNG & LIEFERUNG` · `Bestellungen werden gegen den Lagerbestand in Deutschland geprüft und mit einem bestätigten Lieferdatum versandt.` | `Proforma & Delivery` · `STAGE 04 · PROFORMA & DELIVERY` · `Inquiries are checked against stock in Germany and confirmed with a proforma invoice and delivery date.` / `Proforma & Lieferung` · `PHASE 04 · PROFORMA & LIEFERUNG` · `Anfragen werden gegen den Lagerbestand in Deutschland geprüft und mit Proformarechnung sowie Lieferdatum bestätigt.` |
| Timeline Stage 05 tag | `STAGE 05 · AFTER THE ORDER` / `PHASE 05 · NACH DER BESTELLUNG` | `STAGE 05 · AFTER DELIVERY` / `PHASE 05 · NACH DER LIEFERUNG` |
| FAQ H2 | `Five questions installers ask before ordering.` / `Fünf Fragen, die Installateure vor der Bestellung stellen.` | `Five questions installers ask before sending an inquiry.` / `Fünf Fragen, die Installateure vor einer Anfrage stellen.` |
| FAQ 1, 2, 4, 5 | `...check the pairing before ordering.` · `...for your storage order.` · `Once the order is confirmed...` · `Open Warranty & Replacements from your order with the serial number, model and fault description, and our team in Germany opens the case.` / `...prüfen Sie die Kombination vor der Bestellung.` · `Für Ihre Speicherbestellung...` · `Sobald die Bestellung bestätigt ist...` · `Öffnen Sie „Garantie & Ersatz“ aus Ihrer Bestellung mit Seriennummer, Modell und Fehlerbeschreibung; unser Team in Deutschland eröffnet den Fall.` | `...check the pairing before sending your inquiry.` · `...for your storage inquiry.` · `Once the proforma invoice is confirmed...` · `Contact us with your invoice or proforma reference, serial number, model and fault description, and our team in Germany opens the case.` / `...prüfen Sie die Kombination vor Ihrer Anfrage.` · `Für Ihre Speicheranfrage...` · `Sobald die Proformarechnung bestätigt ist...` · `Kontaktieren Sie uns mit Ihrer Rechnungs- oder Proforma-Referenz, Seriennummer, Modell und Fehlerbeschreibung; unser Team in Deutschland eröffnet den Fall.` |

### Adversarial review & resolution

- **Factual correction in FAQ 5**: In addition to removing `Bestellung`, FAQ 5 on `826`/`6869` previously instructed the customer to `Open Warranty & Replacements from your order` (`Öffnen Sie „Garantie & Ersatz“ aus Ihrer Bestellung`), an unimplemented online order-portal action already prohibited by `#728` (`industry-standards.py`). Replacing it with contacting the team with the invoice or proforma reference resolves both defects simultaneously.
- **Verdict**: PASS.

---

## 4. FAQ & Documents (`data/faq-trade.json` & `932` EN / `6863` DE)

### Initial draft & final copy

| Location | Original EN / DE | Final EN / DE |
| --- | --- | --- |
| Category 0 title & quick link | `Ordering` · `Ordering & delivery` / `Bestellung` · `Vor Ihrer Bestellung` · `Bestellung & Lieferung` | `Inquiries` · `Inquiries & delivery` / `Anfragen` · `Vor Ihrer Anfrage` · `Anfrage & Lieferung` |
| Q1 (minimum quantity) | `Orders start from individual units, delivered across the EU.` / `Bestellungen starten ab einzelnen Einheiten, geliefert in der gesamten EU.` | `Inquiries start from individual units, delivered across the EU.` / `Anfragen sind ab einzelnen Einheiten möglich, geliefert in der gesamten EU.` |
| Q2 (combining brands) | `Can different brands be combined in one project order?` · `...combined in one order. They ship together under a unified invoice; check each pairing against the compatibility lists on file before ordering.` / `Können verschiedene Marken in einer Projektbestellung kombiniert werden?` · `...in einer Bestellung kombiniert werden. Sie werden zusammen mit einer einheitlichen Rechnung geliefert; prüfen Sie jede Kombination vor der Bestellung anhand der hinterlegten Kompatibilitätslisten.` | `Can different brands be combined in one project inquiry?` · `...combined in one project inquiry. They ship together under a unified invoice; check each pairing against the compatibility lists on file before sending your inquiry.` / `Können verschiedene Marken in einer Projektanfrage kombiniert werden?` · `...in einer Projektanfrage kombiniert werden. Sie werden zusammen mit einer einheitlichen Rechnung geliefert; prüfen Sie jede Kombination vor Ihrer Anfrage anhand der hinterlegten Kompatibilitätslisten.` |
| Q3 (packages vs components) | `Both. Installers can order packaged systems...` / `Beides. Installateure können paketierte Systeme ... bestellen...` | `Both. Installers can request packaged systems...` / `Beides. Installateure können paketierte Systeme ... anfragen...` |
| Warranty Q1, Q2, Q3 | `...from your order.` · `...with your order, serial number...` · `What technical support is included with an order?` (`...before the order...`) / `...ausgehend von Ihrer Bestellung.` · `...mit Ihrer Bestellung, Seriennummer...` · `Welcher technische Support ist bei einer Bestellung enthalten?` (`...vor der Bestellung...`) | `...based on your project records.` · `...with your invoice or proforma reference, serial number...` · `What technical support is included with a project?` (`...during planning...`) / `...ausgehend von Ihren Projektunterlagen.` · `...mit Ihrer Rechnungs- oder Proforma-Referenz, Seriennummer...` · `Welcher technische Support ist bei einem Projekt enthalten?` (`...bei der Planung...`) |
| Compliance Q1, Q3 | `...for the models in your order.` · `Are Declarations of Conformity provided with orders?` / `...für die Modelle in Ihrer Bestellung an.` · `Werden Konformitätserklärungen mit Bestellungen bereitgestellt?` | `...for the models in your inquiry.` · `Are Declarations of Conformity provided on request?` / `...für die Modelle Ihrer Anfrage an.` · `Werden Konformitätserklärungen auf Anfrage bereitgestellt?` |

### Adversarial review & resolution

- **Hard Stops & German gate check**: Zero occurrences of `ordering`, `Bestellung`, `Bestellungen`, or banned German words (`Warenkorb`, `Katalog`, `Artikel`, `du`/`ihr`). Preserves Q1's English/German question heading (`What is the minimum order quantity, and where does Linker deliver?` / `Was ist die Mindestbestellmenge, und wohin liefert Linker?`) as the standard B2B trade term for MOQ while stating the inquiry workflow in the answer.
- **Verdict**: PASS.
