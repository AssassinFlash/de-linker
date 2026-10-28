# GoodWe HCA G2 GW11K-HCA-20 (11 kW three-phase EV charger, 7.5 m cable)

- id: 3557
- slug: `goodwe-hca-g2-gw11k-hca-20-11-kw-three-phase-ev-charger`
- sku: `DLK-GOODWE-GW11KHCA20`
- model: GW11K-HCA-20

## 2026-10-28 evidence and review

- The currently hosted English user manual and local snapshot have the same SHA-256 `6a8d11d5afde6aa1840c6c8591a5c4dc379efc1c0953ef144a90d65f5a36e6a9`. Its delivery illustration is on PDF page 33 (printed page 32); the GW11K-HCA-20 table is on PDF page 93 (printed page 92). The illustration was visually checked: 2 RFID cards, 5 AC cable pin terminals, 4 RS485 cable pin terminals, 1 RJ45 terminal, and one screwdriver of each pictured type. Optional items on the following page are not added to the listed delivery.
- The hosted English datasheet matches the local snapshot at SHA-256 `0fdeaf90548f35e00a605e8ae538c24f89f745be5195e85dbf466c2a7d2d9178`; PDF page 2 requires an external Type A RCD. The manual's PDF page 72 describes the grid-dispatch setting for a single device, its activation, the 4.2 kW value and adjustment to actual requirements. The answer describes the manual, without claiming legal compliance.
- Preliminary self-review checked the cited facts, English/German agreement and the original question angles. An existing local instance rendered the revised answers in both languages through the publication binding; the product metadata was restored afterwards. This is not an independent copy review or production readback.
- Independent Terra xhigh copy and primary-source review passed on 2026-10-28. The review confirmed both screwdrivers are included, the listed component counts, the external Type A RCD, and the §14a answer’s enabled, single-device and actual-settings qualifiers. The prior review of earlier text remains in Git history.
- Production product-page and FAQ/document-library readback remain outstanding. The current importer selects only `status: pass` rows; an unrelated all-pending product could still be written as an empty list, so the general import-chain issue remains open.

## 1. Does the 11 kW charger still need an external Type A RCD?

**Status:** pass
**Review:** pass — Independent Terra xhigh copy and source review, 2026-10-28.

**EN Q:** Does the 11 kW charger still need an external Type A RCD?

Yes. The datasheet lists under Protection: "External Type A RCD is needed". The technical data table for GW11K-HCA-20 states: "An external Type A residual current device (RCD) is required."

**DE Q:** Braucht das 11-kW-Ladegerät noch einen externen FI Typ A?

Ja. Laut Datenblatt ist ein externer FI-Schutzschalter vom Typ A erforderlich. Auch die technischen Daten für GW11K-HCA-20 nennen diese Anforderung.

**Citation:** GoodWe HCA G2 Datasheet (EMEA, EN) · p.2 · https://de-linker.com/wp-content/uploads/2026/10/GW_HCA-G2_Datasheet_EMEA-EN_V1.1.pdf

## 2. What comes with the charger?

**Status:** pass
**Review:** pass — Independent Terra xhigh copy and source review, 2026-10-28.

**EN Q:** What comes with the charger?

The scope of delivery includes: Charger x 1, AC connector x 1, dummy socket x 1, dummy socket fastening screws x 4, expansion bolts x 4, RS485 communication connector x 1, LAN communication connector x 1, Phillips screwdriver x 1, flat-head screwdriver x 1, AC cable pin terminals x 5, RS485 cable pin terminals x 4, RFID cards x 2, RJ45 terminal x 1, waterproof rubber plugs x 2 and documents x 1.

**DE Q:** Was gehört zum Lieferumfang?

Zum Lieferumfang gehören: eine Ladestation, ein AC-Steckverbinder, eine Blindbuchse, vier Befestigungsschrauben für die Blindbuchse, vier Spreizbolzen, je ein RS485- und LAN-Kommunikationssteckverbinder, je ein Kreuzschlitz- und Schlitzschraubendreher, fünf AC-Aderendhülsen, vier RS485-Aderendhülsen, zwei RFID-Karten, ein RJ45-Stecker, zwei wasserdichte Gummistopfen und ein Satz Dokumente.

**Citation:** GoodWe HCA G2 User Manual (EN) · p.33 · https://de-linker.com/wp-content/uploads/2026/09/GW_HCA-G2_User-Manual-EN.pdf

## 3. Is GW11K-HCA-20 prepared for §14a EnWG?

**Status:** pass
**Review:** pass — Independent Terra xhigh copy and source review, 2026-10-28.

**EN Q:** Is GW11K-HCA-20 prepared for §14a EnWG?

The manual describes an EnWG §14a grid-dispatch setting. It says that, when enabled, the function is intended to limit the power drawn from the grid by a single device to 4.2 kW, and that the grid-import limit should be set according to the actual requirements.

**DE Q:** Ist GW11K-HCA-20 für §14a EnWG vorbereitet?

Das Handbuch beschreibt eine Einstellung für die Netzsteuerung nach § 14a EnWG. Demnach soll die Funktion im aktivierten Zustand die aus dem Netz bezogene Leistung eines einzelnen Geräts auf 4,2 kW begrenzen; der Netzbezugsgrenzwert ist entsprechend den tatsächlichen Anforderungen einzustellen.

**Citation:** GoodWe HCA G2 User Manual (EN) · p.72 · https://de-linker.com/wp-content/uploads/2026/09/GW_HCA-G2_User-Manual-EN.pdf
