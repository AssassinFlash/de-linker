# Batch D — commerce vocabulary: copy rewrites and legal triage (issue #905)

Status: **draft deliverable**. The rewrites below are the strings to publish. This
document is the record; the database writes are main-line's.

Scope: the seven marketing and tool pages the decision names, plus the sentence
triage for the four exempt legal pages. The wordlist, the checker and the
ratchet live in `tools/checks/`.

Rulings applied:

- AGENTS.md §1 — the customer link is product → inquiry (presented as a
  Proforma); everything after it happens offline. Copy must not describe a shop.
- AGENTS.md §2, 2026-10-09 — inquiry promises; Proforma validity; "marketing
  body copy rewrites keep the earlier ruling"; customer-visible copy goes
  through adversarial review, EN first, DE written independently (not
  word-for-word), Sie form, `de_DE_formal`.
- AGENTS.md §2, 2026-10-25 — real legal text, authorised testimonials and quotes
  are protected; only the hit sentence changes, never the paragraph around it.
- `linker-copywriting` Hard Stops 1–9, run against every replacement.

Method: for each page, the live EN and DE page was fetched over HTTPS (public
pages, no SSH, no WP-CLI, no database access), read through the same prose
extractor the checker uses, and every string containing a wordlist term was
recorded. Only those strings are touched. The rest of each page is untouched.

---

## 1. How the drafts were reviewed

Draft → critique → final, per string. The critique was written as the
`linker-copywriting` reviewer, not as the author, and the Hard Stops that
fired are named. Three findings changed the drafts, and they are the reason
several first attempts do not appear below:

1. **"before you order" → "before your inquiry" (first attempt: "before you
   request a quote").** Hard Stop 9 Actor: "request a quote" hands the reader a
   task. The site's own noun for the customer's action is *inquiry* (AGENTS.md
   §3, four inquiry states), so the noun carries the meaning without an
   imperative.
2. **"Orders ship from our warehouse" → "Stock ships from our warehouse"
   (first attempt: "We dispatch from our warehouse").** Hard Stop 1 / Brand
   Rule 5: `We dispatch` as the subject claims a logistics service Linker does
   not sell, and anti-pattern 13 bans fabricated logistics capability. The
   sentence is about where goods come from, so the goods are the subject.
3. **"A complete parts list, ready to order" → "…ready to quote".** The BOM is
   the input to a Proforma, not to a purchase order; "ready to order" promised a
   purchase path the site does not have. This is the same defect the whole batch
   exists to remove, caught inside its own draft.

Rejected on sight during review, kept here so the next writer does not retry
them: `Tell us before you order`, `Place your order with Linker`, `Order
confirmation` (the site issues a Proforma, never an order confirmation),
`No checkout needed`, `We don't run a shop` (Hard Stop 3 — defensive category
negation; naming the accusation plants it).

Not touched, deliberately: legal entity names, product model designations
(`GMK330`, `GW22K-HCA-20`, `DTSU666`), and every sentence where the word carries
the *sequence* sense rather than the commerce sense.

---

## 2. Page 6913 — Startseite / Home

Ten hits in each language. Three separate defects: the pre-inquiry phrasing
(`before you order`), the post-inquiry stage naming (`Quotes · Orders ·
Warranty`, `STAGE 04 · ORDER FULFILLMENT`, `after the order`), and four
logistics lines (`ready for dispatch`, `Versand aus dem Lager`, and — found only
after the wordlist gained `dispatch*` in this batch's sweep — `warehouse
dispatch` twice in the section copy).

| # | EN before | EN after |
|---|---|---|
| 1 | We can help check supported inverter, battery and meter combinations before you order. | We can help check supported inverter, battery and meter combinations before your inquiry. |
| 2 | Quotes · Orders · Warranty | Quotes · Inquiries · Warranty |
| 3 | Check inverter, battery and meter combinations against the compatibility lists before you order | Check inverter, battery and meter combinations against the compatibility lists before your inquiry |
| 4 | Match inverter, battery and accessories on Linker before you order | Match inverter, battery and accessories on Linker before your inquiry |
| 5 | STAGE 04 · ORDER FULFILLMENT | STAGE 04 · INQUIRY TO DELIVERY |
| 6 | Your equipment, ready for dispatch. | Your equipment, prepared and documented. |
| 7 | We prepare your equipment in Germany, with the product documents and grid certificates requested for your order. | We prepare your equipment in Germany, with the product documents and grid certificates requested with your inquiry. |
| 8 | Commercial invoice and order confirmation | Commercial invoice and Proforma confirmation |
| 9 | Datasheets and manuals, plus the unit certificates requested for your order | Datasheets and manuals, plus the unit certificates requested with your inquiry |
| 10 | Confirm the list and order the system through Linker | Confirm the list and send the inquiry for the system through Linker |
| 11 | Linker still answers after the order — documents, questions and warranty coordination | Linker still answers after the inquiry — documents, questions and warranty coordination |
| 12 | Fulfillment · Stock dispatch · Certificates · Invoice | Inquiry handling · Stock in Germany · Certificates · Invoice |
| 13 | 10 kW hybrid package · German warehouse dispatch | 10 kW hybrid package · Warehouse in Germany |
| 14 | We handle project quotes, warehouse dispatch, and warranty coordination directly through our team in Germany. | We handle project quotes, stock in Germany, and warranty coordination through our team in Germany. |
| 15 | We support trade partners at every stage, from sizing in the Solution Configurator to warehouse dispatch and warranty. | We support trade partners at every stage, from sizing in the Solution Configurator to delivery and warranty. |

| # | DE before | DE after |
|---|---|---|
| 1 | Wir unterstützen Sie dabei, passende Kombinationen aus Wechselrichter, Batteriespeicher und Zähler vor der Bestellung abzustimmen. | Wir unterstützen Sie dabei, passende Kombinationen aus Wechselrichter, Batteriespeicher und Zähler vor Ihrer Anfrage abzustimmen. |
| 2 | Angebote · Bestellungen · Garantie | Angebote · Anfragen · Garantie |
| 3 | Prüfen Sie Kombinationen aus Wechselrichter, Batteriespeicher und Zähler vor der Bestellung anhand der Kompatibilitätslisten | Prüfen Sie Kombinationen aus Wechselrichter, Batteriespeicher und Zähler vor Ihrer Anfrage anhand der Kompatibilitätslisten |
| 4 | Stimmen Sie Wechselrichter, Batteriespeicher und Zubehör auf Linker ab, bevor Sie bestellen | Stimmen Sie Wechselrichter, Batteriespeicher und Zubehör auf Linker ab, bevor Sie Ihre Anfrage senden |
| 5 | Ihre Geräte, bereit für den Versand. | Ihre Geräte, vorbereitet und dokumentiert. |
| 6 | Wir bereiten Ihre Geräte in Deutschland vor, mit den Produktunterlagen und den für Ihre Bestellung angeforderten Netzanschlusszertifikaten. | Wir bereiten Ihre Geräte in Deutschland vor, mit den Produktunterlagen und den mit Ihrer Anfrage angeforderten Netzanschlusszertifikaten. |
| 7 | Datenblätter und Handbücher sowie die für Ihre Bestellung angeforderten Einheitenzertifikate | Datenblätter und Handbücher sowie die mit Ihrer Anfrage angeforderten Einheitenzertifikate |
| 8 | Bestätigen Sie die Liste und bestellen Sie das System über Linker | Bestätigen Sie die Liste und senden Sie die Anfrage für das System über Linker |
| 9 | Linker antwortet auch nach der Bestellung — Dokumente, Fragen und Garantiekoordination | Linker antwortet auch nach der Anfrage — Dokumente, Fragen und Garantiekoordination |
| 10 | 10-kW-Hybridpaket · Versand aus dem Lager in Deutschland | 10-kW-Hybridpaket · Lager in Deutschland |
| 11 | PHASE 04 · AUFTRAGSABWICKLUNG | PHASE 04 · VON DER ANFRAGE ZUR LIEFERUNG |
| 12 | Auftragsabwicklung · Lagerversand · Zertifikate · Rechnung | Anfrageabwicklung · Lagerbestand in Deutschland · Zertifikate · Rechnung |
| 13 | Unser Team in Deutschland kümmert sich um Ihre Projektangebote, den Lagerversand und die Koordination von Garantiefällen. | Unser Team in Deutschland kümmert sich um Ihre Projektangebote, den Lagerbestand und die Koordination von Garantiefällen. |
| 14 | Wir unterstützen Handelspartner in jeder Phase, von der Auslegung im Lösungskonfigurator bis zum Lagerversand und zur Garantie. | Wir unterstützen Handelspartner in jeder Phase, von der Auslegung im Lösungskonfigurator bis zur Lieferung und zur Garantie. |

Notes on the choices. #5 EN `ORDER FULFILLMENT` names a warehouse process the
site does not run; `INQUIRY TO DELIVERY` names the range Linker actually covers
(catalogue rule: stating the range is allowed, narrating the buyer's future is
not). #7 EN `Proforma confirmation`: the site issues a Proforma and no order
confirmation, so the second half of the pair was naming a document that does not
exist. #10 DE keeps no `Versand` because the German had invented a shipping
attribute on a package badge.

### Correction to row #5 DE (main-line review)

The first version of this table turned `Ihre Geräte, bereit für den Versand.`
into `Ihre Geräte, abholbereit im Lager.` and justified it as "the same fact as
the English *prepared in Germany*". That justification was wrong twice, and
main-line stopped it:

1. **It cited the wrong twin.** The English twin of this line is not the
   paragraph underneath it; it is the sentence in the same slot:
   **`Your equipment, ready for dispatch.`** The paragraph below ("We prepare
   your equipment in Germany …") is the section's body, not its headline.
2. **It invented a promise.** `abholbereit` asserts *ready for pickup* — a
   collection offer. The English says `ready for dispatch`: goods prepared and
   ready to leave. Collection is a different commercial offer, and under the
   owner's rulings fulfilment is agreed offline per Proforma, with no Incoterms
   stated online. So `abholbereit im Lager` promised a pickup the site does not
   make, replacing one wrong word with a wrong promise. The correction traded a
   vocabulary defect for a factual one — the failure mode the batch exists to
   remove.

Both twins carry the same defect, and it is the same defect: `dispatch` and
`Versand` name the logistics step. Corrected as a pair, in the same slot, each
written natively:

| | before | after |
|---|---|---|
| EN | Your equipment, ready for dispatch. | Your equipment, prepared and documented. |
| DE | Ihre Geräte, bereit für den Versand. | Ihre Geräte, vorbereitet und dokumentiert. |

Both name the fact the section's body then supports — the goods are prepared in
Germany and carry the product documents and certificates. Neither claims a
shipment, a pickup or a date. `dokumentiert` is the word the German body already
uses for the same work, so the headline and the paragraph now say one thing.

The stage title beside it is corrected too, because it had the same defect one
line up:

| | before | after |
|---|---|---|
| EN | STAGE 04 · ORDER FULFILLMENT | STAGE 04 · INQUIRY TO DELIVERY |
| DE | PHASE 04 · AUFTRAGSABWICKLUNG | PHASE 04 · VON DER ANFRAGE ZUR LIEFERUNG |

And the badge line under the package, whose German had added a shipping
attribute the English did not:

| | before | after |
|---|---|---|
| EN | Fulfillment · Stock dispatch · Certificates · Invoice | Inquiry handling · Stock in Germany · Certificates · Invoice |
| DE | Auftragsabwicklung · Lagerversand · Zertifikate · Rechnung | Anfrageabwicklung · Lagerbestand in Deutschland · Zertifikate · Rechnung |

`Lagerversand` was the compound the checker could not see until this batch's
sweep (see §11); the English `Stock dispatch` was invisible to it because
`dispatch` was not in the wordlist. Both were live on the home page.

---

## 3. Page 6921 — Gewerblicher Speicher / Commercial storage

Five German hits and two English. The page's process rail runs
`01 · Load data → 02 · Configuration → 03 · Quotation → 04 · … → 05 · After-sales`,
and stage 04 is the one this batch touches.

| # | EN before | EN after |
|---|---|---|
| 1 | Order · Documents · Warranty | Inquiry · Documents · Warranty |
| 2 | Keep the product conversation connected after the order through Linker | Keep the product conversation connected after the inquiry through Linker |
| 3 | 04 · Dispatch | 04 · Delivery |
| 4 | Shipped from Germany to the site. Delivery date confirmed with the quotation. | Delivered from Germany to the site. The delivery date is confirmed with the quotation. |

| # | DE before | DE after |
|---|---|---|
| 1 | Versand | Lieferung |
| 2 | Bestellung · Dokumente · Garantie | Anfrage · Dokumente · Garantie |
| 3 | 04 · Versand | 04 · Lieferung |
| 4 | Versand aus Deutschland zum Standort. Liefertermin wird mit dem Angebot bestätigt. | Aus Deutschland zum Standort geliefert. Der Liefertermin wird mit dem Angebot bestätigt. |
| 5 | Halten Sie das Produktgespräch nach der Bestellung über Linker aufrecht | Halten Sie das Produktgespräch nach der Anfrage über Linker aufrecht |

`Lieferung` is the word for physical delivery, which is real and is what the
step describes; `Versand` and `dispatch` were the shipping-process words the
wordlist bans. The English twin's sentence changed too: `Shipped from Germany`
was the same defect on the other side, and correcting only the German would
have left the pair saying different things.

### Correction: the parity claim in the first version

The first version of this document said the German page "keeps a stage the
English twin does not show". **That was wrong, and the cause of the error is
worth recording**, because it is the same root cause as the defect above.

Both languages have the same five stages. Read from the live pages:

```text
EN  01 · Load data   02 · Configuration   03 · Quotation   04 · Dispatch      05 · After-sales
DE  01 · Lastdaten   02 · Konfiguration   03 · Angebot     04 · Versand       05 · After-Sales
```

There was never a missing stage. What the first pass compared was the **hit
counts** — five German hits against two English — and inferred an asymmetry in
the content from an asymmetry in the scan. The asymmetry was in the **wordlist**:
it listed `Versand*` and did not list `dispatch`. So the German stage title was
caught and the English one was invisible, and the conclusion drawn from that
difference was that a stage was missing.

Root cause, stated once: *a detection gap was read as a content gap.* The
comparison should have been made against the two pages, not against the two lists
of findings. Two consequences follow, and both are fixed in this batch rather
than noted:

1. **The wordlist gained `dispatch*`** (§11). With it, the English side of every
   twin on this page is caught, and the counts are 4 EN / 5 DE — the remaining
   difference is the German sentence carrying one extra clause.
2. **The German compounds are now matched** (§11). `Lagerversand` on the home
   page had been invisible to the gate from the beginning.

With those two closed, the pair is verified symmetric on this page: same five
stages, same words in each slot, each language written natively. Nothing in this
section needs a production content write — it is page copy, and it is delivered
here for main-line to publish.

---

## 4. Page 6863 — FAQ & Dokumente / FAQ & documents

The largest surface: twelve hits per language. Three kinds, handled differently.

**(a) Interface labels** — rewritten.

| # | EN before | EN after |
|---|---|---|
| 1 | Before you order | Before your inquiry |
| 2 | Shipping & logistics | Delivery & freight |

| # | DE before | DE after |
|---|---|---|
| 1 | Vor der Bestellung | Vor Ihrer Anfrage |
| 2 | Versand & Logistik | Lieferung & Fracht |

**(b) Questions that are the page's own copy** — rewritten.

| # | EN before | EN after |
|---|---|---|
| 3 | What is the minimum order quantity, and where does Linker deliver? | What is the minimum inquiry quantity, and where does Linker deliver? |
| 4 | Which CT version is included in this GMK330 order? | Which CT version is included with this GMK330? |
| 5 | What should be checked before ordering GW22K-HCA-20? | What should be checked before requesting a GW22K-HCA-20? |

| # | DE before | DE after |
|---|---|---|
| 3 | Welche Stromwandlerversion ist in dieser GMK330-Bestellung enthalten? | Welche Stromwandlerversion ist mit dieser GMK330 enthalten? |
| 4 | Was ist vor der Bestellung von GW22K-HCA-20 zu prüfen? | Was ist vor der Anfrage für GW22K-HCA-20 zu prüfen? |

**(c) Vendor answer text and shipment contents** — **not rewritten.** These are
third-party manual text reproduced on the page: `Before ordering, check that the
charging pile model is correct…`, `order an additional DTSU666… from SAJ`,
`Contents are order-dependent`. They quote the manufacturer's document, and the
Preservation List protects quoted text ("Secondhand text is not ours to
rewrite"). They are recorded in the checker's baseline with that reason rather
than edited. The same applies to the German `bestellabhängig` shipment lines,
which are translations of that same vendor text.

One page-level sentence is Linker's own and is fixed:

| # | EN before | EN after |
|---|---|---|
| 6 | (none in EN — the paragraph is German-only) | — |

| # | DE before | DE after |
|---|---|---|
| 6 | Es gibt kein Palettenminimum. Anfragen sind ab einzelnen Einheiten möglich, geliefert in der gesamten EU. Ausrüstung wird gemäß Projektzeitplänen versandt, wobei Handelsangebote die Frachtkosten zum Zielort ausweisen. | Es gibt kein Palettenminimum. Anfragen sind ab einzelnen Einheiten möglich, geliefert in der gesamten EU. Ausrüstung wird gemäß Projektzeitplan geliefert, wobei Handelsangebote die Frachtkosten zum Zielort ausweisen. |

`versandt` → `geliefert` keeps the sentence's claim (goods go out on the
project's schedule) and drops the shipping-process word. Nothing else in the
paragraph moves.

---

## 5. Page 3302 — Solution Configurator / Lösungskonfigurator

**Zero hits in both languages.** The tool page was already clean; nothing to
change. Recorded so the next batch does not re-scan it on the assumption that it
was missed.

---

## 6. Page 874 — Capability / Leistungsfähigkeit

Six English hits, four German. The page describes pre-sale compatibility work
and post-sale document handling.

| # | EN before | EN after |
|---|---|---|
| 1 | We help you match equipment to the site and clarify compatibility, documentation and support questions before you order. | We help you match equipment to the site and clarify compatibility, documentation and support questions before your inquiry. |
| 2 | …We review the available technical data to help narrow the configuration before the order is confirmed. | …We review the available technical data to help narrow the configuration before the Proforma is issued. |
| 3 | Order dispatch and technical support after the order | Delivery and technical support after the inquiry |
| 4 | Our team provides the datasheets and manuals we hold for your model and requests the certificates needed for your order. | Our team provides the datasheets and manuals we hold for your model and requests the certificates needed with your inquiry. |
| 5 | How is the battery sized before ordering? | How is the battery sized before the inquiry? |
| 6 | If a specific document is required for your project, tell us before ordering so we can check its availability for the exact product. | If a specific document is required for your project, we check its availability for the exact product before the inquiry is answered. |

| # | DE before | DE after |
|---|---|---|
| 1 | Auftragsversand und technischer Support nach der Bestellung | Lieferung und technischer Support nach der Anfrage |
| 2 | Unser Team stellt die vorhandenen Datenblätter und Handbücher für Ihr Modell bereit und fordert die für Ihre Bestellung benötigten Zertifikate an. | Unser Team stellt die vorhandenen Datenblätter und Handbücher für Ihr Modell bereit und fordert die mit Ihrer Anfrage benötigten Zertifikate an. |
| 3 | Wie wird der Batteriespeicher vor der Bestellung dimensioniert? | Wie wird der Batteriespeicher vor der Anfrage dimensioniert? |
| 4 | Wenn für Ihr Projekt ein bestimmtes Dokument erforderlich ist, teilen Sie uns dies vor der Bestellung mit, damit wir die Verfügbarkeit für das genaue Produkt prüfen können. | Wenn für Ihr Projekt ein bestimmtes Dokument erforderlich ist, prüfen wir die Verfügbarkeit für das genaue Produkt, bevor die Anfrage beantwortet wird. |

#2 EN `before the order is confirmed` → `before the Proforma is issued` names
the document the site actually produces, so the sentence keeps its timing claim
and loses the shop noun. #6 EN is the one place where the draft removed customer
homework as well as the banned word: the original was `tell us before ordering`,
which is anti-pattern 22 (`Tell us…`). The rewrite makes Linker the actor and
keeps the condition. #4 DE applies the same change, written in German rather
than translated.

---

## 7. Page 2748 — Services & Support / Kundendienst

Nine English hits, eleven German. This page had the most invented commerce
flow: orders shipping, warranty following an order, parts list ready to order.

| # | EN before | EN after |
|---|---|---|
| 1 | We request grid connection certificates and supporting documents for the equipment in your order. | We request grid connection certificates and supporting documents for the equipment in your inquiry. |
| 2 | Orders ship from our warehouse. Where delivery is required, freight is quoted separately for the destination. | Stock ships from our warehouse. Where delivery is required, freight is quoted separately for the destination. |
| 3 | Our team handles after-sales support. Warranty terms follow the order. | Our team handles after-sales support. Warranty terms follow the Proforma. |
| 4 | Grid compliance documents requested for the order through Linker | Grid compliance documents requested with the inquiry through Linker |
| 5 | The Solution Configurator sizes the system from your site data. The available compatibility lists help you choose the right inverter and battery combination before ordering. | The Solution Configurator sizes the system from your site data. The available compatibility lists help you choose the right inverter and battery combination before the inquiry. |
| 6 | A complete parts list, ready to order | A complete parts list, ready to quote |
| 7 | Linker requests the certificates and protection parameter sheets your utility needs for registration and sign-off, for the equipment in your order. | Linker requests the certificates and protection parameter sheets your utility needs for registration and sign-off, for the equipment in your inquiry. |
| 8 | …Check the connection parts before anything is ordered. | …Check the connection parts before the inquiry is sent. |
| 9 | …Check the expansion rules in the product documents before you order the addition. | …Check the expansion rules in the product documents before the inquiry for the addition. |

| # | DE before | DE after |
|---|---|---|
| 1 | Komplette Systempakete, gemeinsam versandt | Komplette Systempakete, gemeinsam geliefert |
| 2 | Wir fordern die Netzanschlusszertifikate und weiteren Unterlagen für die Geräte Ihrer Bestellung an. | Wir fordern die Netzanschlusszertifikate und weiteren Unterlagen für die Geräte Ihrer Anfrage an. |
| 3 | Bestellungen versenden wir ab Lager. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort. | Aus dem Lager liefern wir ab. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort. |
| 4 | Unser Team übernimmt den Kundendienst. Garantiebedingungen richten sich nach der Bestellung. | Unser Team übernimmt den Kundendienst. Garantiebedingungen richten sich nach der Proformarechnung. |
| 5 | Netzanschlussunterlagen, über Linker für die Bestellung angefordert | Netzanschlussunterlagen, über Linker mit der Anfrage angefordert |
| 6 | Der Lösungskonfigurator legt das System anhand Ihrer Standortdaten aus. Die verfügbaren Kompatibilitätslisten unterstützen Sie dabei, vor der Bestellung eine passende Wechselrichter-Batterie-Kombination auszuwählen. | Der Lösungskonfigurator legt das System anhand Ihrer Standortdaten aus. Die verfügbaren Kompatibilitätslisten unterstützen Sie dabei, vor der Anfrage eine passende Wechselrichter-Batterie-Kombination auszuwählen. |
| 7 | Eine vollständige Stückliste, bestellbereit | Eine vollständige Stückliste, fertig für die Anfrage |
| 8 | Verpackt und versandt als eine Lieferung über Linker | Verpackt und geliefert als eine Sendung über Linker |
| 9 | Linker fordert für die Geräte in Ihrer Bestellung die Zertifikate und Schutzparameter an, die Ihr Netzbetreiber für die Registrierung und Abnahme benötigt. | Linker fordert für die Geräte in Ihrer Anfrage die Zertifikate und Schutzparameter an, die Ihr Netzbetreiber für die Registrierung und Abnahme benötigt. |
| 10 | …Prüfen Sie die Anschlussteile, bevor etwas bestellt wird. | …Prüfen Sie die Anschlussteile, bevor die Anfrage gesendet wird. |
| 11 | …Prüfen Sie die Erweiterungsregeln in den Produktunterlagen, bevor Sie die Erweiterung bestellen. | …Prüfen Sie die Erweiterungsregeln in den Produktunterlagen, bevor Sie die Erweiterung anfragen. |

#2 EN `Orders ship` → `Stock ships`: the subject becomes the goods, not a purchase
order (Hard Stop 1; anti-pattern 13). #3 both languages: `follow the order` /
`richten sich nach der Bestellung` pointed at a document that does not exist;
the warranty follows the issued Proforma. #6 `ready to quote` — the BOM feeds a
quotation. #8 DE `Verpackt und geliefert als eine Sendung` keeps the
one-consignment claim and drops `versandt`.

---

## 8. Page 746 — Solution / Lösung

Three English hits, three German.

| # | EN before | EN after |
|---|---|---|
| 1 | Check the pairing against the compatibility lists on file before ordering. Getting equipment from two different manufacturers to communicate properly is often a major headache on site. | Check the pairing against the compatibility lists on file before the inquiry. Getting equipment from two different manufacturers to communicate properly is often a major headache on site. |
| 2 | Linker requests it for the system in your order: the certification package your grid operator asks for. | Linker requests it for the system in your inquiry: the certification package your grid operator asks for. |
| 3 | You don't have to wait. We provide browser-based tools so you can move from a rough customer request to an orderable system package on your own schedule. | You don't have to wait. We provide browser-based tools so you can move from a rough customer request to a system package you can put in front of us, on your own schedule. |

| # | DE before | DE after |
|---|---|---|
| 1 | Prüfen Sie die Kombination vor der Bestellung anhand der hinterlegten Kompatibilitätslisten. Geräte zweier Hersteller zuverlässig miteinander kommunizieren zu lassen, ist auf der Baustelle oft ein großes Problem. | Prüfen Sie die Kombination vor der Anfrage anhand der hinterlegten Kompatibilitätslisten. Geräte zweier Hersteller zuverlässig miteinander kommunizieren zu lassen, ist auf der Baustelle oft ein großes Problem. |
| 2 | Linker fordert für das System in Ihrer Bestellung das Zertifizierungspaket an, das Ihr Netzbetreiber verlangt. | Linker fordert für das System in Ihrer Anfrage das Zertifizierungspaket an, das Ihr Netzbetreiber verlangt. |
| 3 | Sie müssen nicht warten. Wir stellen browserbasierte Linker Werkzeuge bereit, mit denen Sie von einer groben Kundenanfrage bis zu einem bestellbaren Systempaket in Ihrem eigenen Zeitplan kommen. | Sie müssen nicht warten. Wir stellen browserbasierte Linker Werkzeuge bereit, mit denen Sie von einer groben Kundenanfrage bis zu einem anfragefertigen Systempaket in Ihrem eigenen Zeitplan kommen. |

#3 is the one place the review overruled a literal fix. `orderable system
package` and `bestellbares Systempaket` say the output is a purchasable object.
The tool's real output is a package the customer can put into an inquiry, so
both languages were rewritten to name that, and the sentence keeps its "on your
own schedule" promise. `anfragefertig` is the noun the German site already uses
for the inquiry.

---

## 9. Legal pages — sentence triage (exempt from failing, still triaged)

The four pages are exempt from the gate (owner ruling 2026-10-25: real legal text
is protected). Exemption is not a pass: each hit sentence is classified below.
Rule applied — a sentence that describes an **online** checkout or payment flow
that does not exist is a stale fact and needs a surgical fix; a sentence about
the **offline** contract (quote, Proforma, bank transfer, freight, retention of
title) describes a real transaction and stays; a quotation stays verbatim.

Evidence for "the online checkout does not exist": `Shortcodes::checkout()`
(`plugins/linker-commerce/includes/Presentation/Shortcodes.php:314`) renders
`[linker_inquiry_form]` except on the WooCommerce `order-received` endpoint, so
the page reached by the checkout URL is the inquiry form. There is no cart →
address → payment step to declare a VAT rate in.

### 1673 / 6827 — Privacy Policy / Datenschutzerklärung

| Sentence (EN; the DE twin carries the same content) | Kind | Action |
|---|---|---|
| `Order and billing data` | **stale fact** — names a data category the site never creates; the record is an inquiry and a Proforma | Surgical: `Inquiry and billing data` / `Anfrage- und Abrechnungsdaten` |
| `Products, quantities, prices, billing and shipping addresses, order documents (proforma, invoice). Used to fulfil orders and meet statutory bookkeeping duties.` | **mixed** — `order documents`, `shipping addresses`, `fulfil orders` describe the shop flow | Surgical: `…billing and delivery addresses, inquiry documents (proforma, invoice). Used to answer inquiries, issue Proformas and meet statutory bookkeeping duties.` / `…Rechnungs- und Lieferadressen, Anfragedokumente (Proforma, Rechnung). Verwendet zur Beantwortung von Anfragen, zur Ausstellung von Proformarechnungen und zur Erfüllung gesetzlicher Buchführungspflichten.` |
| `If you request the German 0% VAT rate for photovoltaic systems (§ 12 Abs. 3 UStG) at checkout, we record the declaration text version…` | **stale fact** — `at checkout` is the process that does not exist. The 0% rate itself is real and is agreed offline (the registration collects a VAT ID; the Proforma then states the VAT) | Surgical: replace `at checkout` with `before the Proforma is issued` / `vor Ausstellung der Proformarechnung`. Keep the rest of the sentence and the legal basis text unchanged. |
| `Account and order data may be accessed by authorised personnel… where necessary for order processing and account service.` | **mixed** — `order data` and `order processing` | Surgical: `Account and inquiry data … for inquiry processing and account service` / `Konten- und Anfragedaten … für die Bearbeitung von Anfragen und den Kontenservice` |
| `Account data is kept for the life of the account. Order, invoice, and VAT-declaration records are kept for the statutory retention periods…` | **retention fact** — the retention period is a statutory obligation, and a Proforma/invoice record really is kept | Surgical on the noun only: `Inquiry, invoice, and VAT-declaration records` / `Anfrage-, Rechnungs- und Umsatzsteuererklärungsunterlagen`. Retention periods and the 10-year figure stay exactly as written. |

The privacy page is the one legal page where the hits are nearly all **stale
facts**, because the categories were written for a shop. The statutory
retention reasoning is preserved in every case; only the noun for the record
changes.

### 1674 / 6825 — Terms of Sale / Verkaufsbedingungen

| Sentence (EN) | Kind | Action |
|---|---|---|
| `Ordering and contract` (section heading) | **offline contract** — the contract is real and is formed per quotation | **Keep.** The heading names the section that governs contract formation, which happens offline. Recorded in the baseline with this reason. |
| `You can use your Solution draft to send a product inquiry or request a Proforma invoice. Our team prepares your quotation and handles any subsequent order with you. Contract formation is governed by the specific terms in the relevant quotation.` | **offline contract** — narrates the real path and says where the contract forms | **Keep.** This is the sentence that actually describes the site correctly. |
| `Prices are net unit prices in EUR, excluding VAT and shipping.` | **offline contract** — freight is quoted per Proforma; the word names a real cost line | **Keep.** Changing it to `freight` would be cosmetic; the sentence states a price exclusion that exists. |
| `Payment is by bank transfer / prepayment. Bank details are provided with the order documents. Orders are processed and dispatched after receipt of payment…` | **offline contract** — payment really is by transfer, and goods really are dispatched after receipt | **Keep.** This is a payment *term*, not an online payment flow. It is the sentence that proves the transaction is offline. |
| `Shipping and delivery` (heading) | **offline contract** | **Keep.** |
| `Shipping is by freight (pallet) or parcel service. Where a parcel charge can be calculated reliably, it is stated in the quotation or Proforma invoice.` | **offline contract** — real freight mechanism, and the parcel charge is the same one the product page shows | **Keep.** |
| `For pallet, dangerous-goods, multi-item, unknown-weight, and cross-border orders, Linker confirms the freight charge on the Proforma invoice, and nothing is payable until the Proforma total is complete.` | **offline contract** | **Keep.** The sentence is the contractual promise about when money is due. |
| `Delivery dates are communicated per order and are estimates unless expressly confirmed. For B2B sales, risk passes to the buyer when the goods are handed to the carrier.` | **offline contract** — Incoterms-adjacent risk transfer | **Keep.** Protected term. |
| `Delivered goods remain the property of Linker Technology GmbH until full payment of the purchase price.` | **offline contract** — retention of title | **Keep.** Protected term. |

**Result: 0 surgical fixes on the terms of sale, 9 kept with reasons.** The
German twin (`/de/verkaufsbedingungen/`, 6825) carries the same nine sentences
and the same disposition. This is the batch's clearest finding: the terms page
was never the problem, because it describes the offline deal correctly. The
stale-fact problem is the privacy policy's data categories, which were copied
from a shop's privacy notice.

### Quotations

None of the four pages contains a third-party quotation. The vendor-manual text
that the checker baselines as quoted material is on page 6863, not on a legal
page; it is recorded in §4(c) above.

---

## 10. What the checker still reports, and why

After the code fixes in this batch, `just commerce-terms` reports 28 baselined
hits across 9 files: the 24 `order` sequence senses (`Order by rows`, `Reverse
order`, `in either order`, `time order`, `in request order`) plus 4 energy
`dispatch` strings. None is a shop noun or a shipment. Each carries its reason in
`tools/checks/commerce-terms-baseline.json`.

The live database has not been scanned: that is the deploy smoke
(`commerce-terms.py --wp-cli`), and it runs from main-line, not from this
branch. The page strings in this document are the input it will check against.

---

## 11. Proactive sweep: what the gate could not see

Written after the first review round. Each finding is stated with its root
cause, because a finding without one is not a finding: the useful part is which
assumption was wrong, not which string was dirty.

### 11.1 The wordlist was missing the English half of a class it named

**Finding.** `dispatch` was absent from `commerce-terms.txt` while `Versand*`
was present. The live English home page says `warehouse dispatch` twice,
`Stock dispatch` once and `ready for dispatch` once; the live German pages say
the same thing in German. Every English string was invisible to the gate and
every German one was caught.

**Root cause.** The list was transcribed from the two documents that state it —
spec 11:191 names `order/checkout/payment/shipping/Versand/Kasse/Bezahlen/
Warenkorb`, AGENTS §3 names `catalogue/article/basket/cart` — and neither
document names the English dispatch word. The list was faithful to its sources
and still incomplete relative to the ruling those sources implement. AGENTS §1
rules out dispatch (发货) and purchasing (采购) as part of the same chain; the
spec's list stopped one synonym short of that.

**Damage it caused.** The German commercial-storage stage read `04 · Versand`
against an English `04 · Dispatch`. With only the German caught, the first
version of this document concluded the German page had "a stage the English twin
does not show". That conclusion was wrong (§3), and the wrong conclusion came
from reading hit *counts* as if they were page *content*.

**Fixed at the root.** `dispatch*` and `purchase*` are now in the list. The four
`dispatch` strings in the tree are the Planner's energy-dispatch calculation
("an optimal dispatch schedule"), not shipments, so they are baselined with that
reason; a shop use of the word now fails. Regression test:
`test_the_logistics_words_past_the_spec_list_are_named` fails if either term is
removed.

### 11.2 German compounds were invisible: `Versand*` could not see `Lagerversand`

**Finding.** The live German home page says `Lagerversand` **three times**
(alongside `Auftragsabwicklung`, `Lagerversand`, `Zertifikate`, `Rechnung` in a
badge line and twice in section copy). The gate reported nothing. The list has
carried `Versand*` since its first version.

**Root cause.** The matcher anchored every term at a word start
(`(?<![^\W_])Versand`). English compounds are open or hyphenated, so a leading
anchor is correct for English. German closes its compounds and puts the head
last, so `Lager|versand`, `Paket|versand`, `Express|versand` never matched. The
same shape hides `Nachbestellung`, `Kundenbestellung`, `Teilzahlung`,
`Vorauszahlung`, `Ratenzahlung`. This was a defect in the *matcher*, and no
amount of correctness in the wordlist would have fixed it — which is why the
spec's own list never caught these either.

**Fixed at the root.** The four heads that take the compound form
(`Versand*`, `Bestell*`, `Zahlung*`, `Warenkorb*`) now match anywhere inside a
word. It is deliberately not a general rule: loosening `Kasse*` would match
`Kasserolle`, `Kassette` and `Kassierer`. The heads were chosen by trying them
against the shipped copy — every newly matched string is a genuine compound of
its term. The German stage-04 text on page 6921 is now caught by the compound
form, confirming it end to end.

**Recorded, not fixed.** `Kasse*` still matches `Kassette` and `Kasserolle`.
Loosening the term would start missing `Kassenbuch` and `Kassensystem`, and
neither spelling occurs in the tree or on the live pages, so the fix would cost
more detection than it bought. Pinned as a known limit by
`test_kasse_prefix_is_recorded_as_a_latent_false_positive`, so a future writer
sees the trade rather than rediscovering it.

### 11.3 "Refund & Returns" in the site footer, linking to a live page

**Finding.** The footer — on every page, in both languages — carries
`Refund & Returns` → `/refund-returns/` and `Rückgabe & Erstattung` →
`/de/rueckgabe-erstattung/`. Both target pages return HTTP 200.

**Root cause.** The footer was built as part of the shop's site map, before the
single-link ruling. A returns policy is a shop artefact: with no online purchase
there is nothing to return through the site, and the legal position is governed
by the terms of sale, which are offline. The pages themselves are live content,
so deleting the link in the footer template would leave two orphaned pages in
the database.

**Not fixed here, reported with the reason.** This needs two decisions above
this gate's authority: whether a returns page stays at all (the terms of sale
already cover the contractual position), and whether the two pages should be
unpublished or repurposed. Changing the footer alone would hide a page that
still exists. Removed from this batch's scope so it is not half-done; it is not
covered by the wordlist, because `refund*` would also catch nothing else and
`return*` cannot separate "returns a value" (33 strings) from "returns".

### 11.4 `shop` appears where the right word is someone else's vocabulary

**Finding.** Three strings use `shop`: WooCommerce's own settings description
("the store address under General", whose German admin screen says
`Shop-Adresse`) and the linker-i18n plugin header shown in the plugins list
("Polylang companion for de-linker.com: … and the German shop on the English
products").

**Root cause.** The scanner reads every gettext literal and cannot tell wp-admin
copy from customer copy. It has the same limitation for the `order`/`payment`
words it already baselines, which is why the baseline exists. Adding `shop` to
the wordlist would baseline these three and, more importantly, would teach the
next reader that shop vocabulary is tolerated in customer copy — the opposite of
what the gate is for.

**Reported, not wordlisted.** The real gap is surface classification, not
vocabulary: a wp-admin description is not customer copy, and the gate would be
sharper if it knew that. That is a design change to the scanner, not a word to
add, and it is named here rather than hidden behind a baseline entry.

### 11.5 `Auftrag` is WooCommerce's order vocabulary inside wp-admin

**Finding.** `Gemäß den Einstellungen werden für diesen Auftrag keine
Berechnungen aufbewahrt` and five similar strings (saved-order, order manifest,
checksums for source and order).

**Root cause.** These are WooCommerce's own German admin terms for a saved
record, in admin screens this plugin does not own the vocabulary of. Renaming
them would make the plugin disagree with the admin UI around it.

**Reported, not fixed.** Same class as 11.4 and the same root cause: admin
surface, not customer copy. Recorded so the next reader does not re-open it as a
new finding.

### 11.6 The ratchet's own blind spots, checked

Three failure modes were tested rather than assumed, and all hold:

- **A page with no hits is not a stale entry.** Fixed in the first review round
  (`f4d9f20b9`): the two scans now compare only their own entries.
- **A row the smoke cannot read fails instead of counting clean.** Covered by
  `test_an_unreadable_row_fails_instead_of_counting_as_clean`.
- **A reflow is not a new string.** Covered by
  `test_reflow_does_not_read_as_a_new_string`; the baseline key is the
  whitespace-collapsed string.

One gap is now named rather than tested: **the repository scan cannot see a
string that exists only in the database.** That is by design — the live scan
covers it — but it means a page edited in production after the last deploy can
carry a banned word that no repository check will report. The deploy smoke is
the only fence for that, which is why `--wp-cli` exists and why main-line runs it.

### 11.7 What the sweep explicitly did not touch

Other batches' files: the engine, Genie, the Planner and the registry belong to
agents running in parallel. The Planner's own strings were read only to
establish that `dispatch` there means energy dispatch, and the four findings in
11.1 are recorded as baseline reasons, not as edits.
