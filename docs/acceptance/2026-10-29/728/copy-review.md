# #728 trade-standard copy review

Date: 2026-10-29

## Surfaces

- EN page 2748: `/services-support/`
- DE page 6700: `/de/kundendienst/`

The existing Services & Support pair carries all four requested subjects. The
footer already links to this pair, so this batch adds one compact row without
duplicating the statements in legal or other marketing pages. Existing page copy
is retained byte for byte except for the inserted row and its scoped styles.

## Final EN

- Delivery: `Orders ship from our warehouse. Where delivery is required, freight is quoted separately for the destination.`
- Training: `We provide product training for installers.`
- After-sales: `Our team handles after-sales support. Warranty terms follow the order.`
- Resellers: `We work with distributors and resellers.`

## Final DE

- Lieferung: `Bestellungen versenden wir ab Lager. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort.`
- Produktschulung: `Für Installateure bieten wir Produktschulungen an.`
- Kundendienst: `Unser Team übernimmt den Kundendienst. Garantiebedingungen richten sich nach der Bestellung.`
- Wiederverkäufer: `Wir arbeiten mit Distributoren und Wiederverkäufern zusammen.`

## Adversarial review

Result: PASS.

An independent DeepSeek Flash review checked the EN/DE pair against issue #728,
`linker-copywriting`, and `humanizer`. It found no factual, constraint,
meaning-changing grammatical, or cross-language mismatch. No line invents a
delivery time, warranty duration, Incoterm, free-shipping threshold, stock
quantity, online ticket, account-opening promise, or other service commitment.
No rewrite was requested.

Per the owner's 2026-10-29 correction, the review did not propose tone, style,
rhythm, or vocabulary changes; existing wording is preserved unless a factual
error is proven.

## Consumer evidence

- Real WordPress reviewed-pair write and exact readback.
- Second plan reports both pages unchanged.
- Before/after screenshots:
  - `en-1440-before.png` and `en-1440-after.png`
  - `de-390-before.png` and `de-390-after.png`
- EN 1440 and DE 390 both render four readable cells with no horizontal overflow.
