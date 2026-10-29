# #728 trade-standard copy review

Date: 2026-10-29

## Surfaces

- EN page 2748: `/services-support/`
- DE page 6700: `/de/kundendienst/`

The existing Services & Support pair carries all four requested subjects. The
footer already links to this pair, so this batch adds one compact row without
duplicating the statements in legal or other marketing pages. Existing page copy
is retained byte for byte except for the inserted row; its scoped rules live in
the existing WindPress `service-intro.css` source.

## Source and consistency

The retained source message and its reviewable extraction are linked in
[source-email-evidence.md](source-email-evidence.md). The original `.eml` has
SHA-256
`858c2fca18dacbcef2b3814e5f8e802c9468237db55c39d68f03071422d20631`;
the excerpts used here are E1, E3, E8 and E12.

| Item | Existing commitment | Authority |
| --- | --- | --- |
| Delivery | E8: Linker normally quotes EXW from its warehouse; DAP transport cost is added after the destination is supplied. The site deliberately avoids Incoterms under the owner's 2026-10-02 ruling. | Source e-mail E8; `competitor-standard-checklist.md` row 15. |
| Training | Linker offers product training to installers. | Owner's 2026-10-28 average-standard ruling; competitor rows PVS14/EWS18/SEN15/MEM17/AKS19. No source e-mail wording is claimed. |
| After-sales | E1 includes after-sales service; the existing site says Linker handles a claim from reporting to replacement. | Source e-mail E1 and E3; existing site S-118; `competitor-standard-checklist.md` row 19. |
| Resellers | E3 supports the reseller buyer's main-equipment supply; E12 proposes long-term cooperation. | Source e-mail E3/E12 and the buyer's stated resale model; `competitor-standard-checklist.md` row 20. |

The page does not invent an Incoterm, delivery time, warranty duration, free
shipping threshold, online ticket, account-opening promise, or stock quantity.
The English and German versions state the same four facts.

## Initial EN draft

- Delivery: `Orders ship from our warehouse. Where delivery is required, freight is quoted separately for the destination.`
- Training: `We provide product training for installers.`
- After-sales: `Our team handles after-sales support. Warranty terms follow the order.`
- Resellers: `We work with distributors and resellers.`

## Initial DE draft

- Lieferung: `Bestellungen versenden wir ab Lager. Bei Lieferungen berechnen wir die Fracht gesondert nach Zielort.`
- Produktschulung: `Für Installateure bieten wir Produktschulungen an.`
- Kundendienst: `Unser Team übernimmt den Kundendienst. Garantiebedingungen richten sich nach der Bestellung.`
- Wiederverkäufer: `Wir arbeiten mit Distributoren und Wiederverkäufern zusammen.`

## Review comments and resolutions

This section is the review chain from initial drafts to the final wording.
A previous binary "PASS" is not treated as evidence for findings raised later.

1. Initial adversarial review: DeepSeek Flash returned PASS with no requested
   rewrite of the four body statements.
2. Retained evidence review: Helmholtz found that the file did not link the
   source e-mail, did not preserve an auditable draft-to-review-to-final chain,
   left the false online warranty workflow unexamined, and guarded only the new
   row rather than existing page copy. Those findings superseded the binary
   PASS and are resolved below.
3. Source linkage: [source-email-evidence.md](source-email-evidence.md) now links
   the retained `.eml`, records its SHA-256, links the extraction, and quotes the
   four source statements used by this ticket.
4. Standards review: the German accessible name
   `Geschäftsbedingungen` wrongly means legal terms of business. It was changed
   to `Leistungen für Fachpartner`. The equivalent English accessible name
   `Services for trade customers` describes the row without changing its body.
5. Visual styling previously sat in the page's inline style block. It was moved
   to the existing WindPress source `service-intro.css`; the page migration now
   changes markup only.
6. Owner correction: the 2026-10-29 instruction prohibits style, tone, rhythm,
   and vocabulary changes. No body statement in the four-cell row was rewritten
   during these fixes.
7. Guard review: the migration now scans customer-visible text across the whole
   existing EN/DE page before inserting anything. It rejects named trade terms,
   free shipping, fixed delivery or warranty periods, online warranty workflows,
   online account workflows, and stock quantities. Tests cover English and
   German examples, the exact obsolete warranty workflow, and false-positive
   controls for legitimate warranty/delivery copy.

## Adjacent factual correction in the trade library

The existing `/faq-download/` and `/de/faq-dokumente/` warranty answer claimed
an online `Open Warranty & Replacements` workflow and a signed-in order form.
That contradicts the owner's 2026-10-28 ruling that the company has no online
ticket and handles the transaction and after-sales offline. This is a factual
correction explicitly allowed by the owner's 2026-10-29 instruction; it is not a
style rewrite.

Only that false workflow claim was replaced. The diagnostic role performed by
Linker remains. The new EN/DE answers ask the customer to contact the team with
the order, serial number, model, and fault description; the link now says to
contact the team instead of implying an online form.

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

## Consumer evidence

- Dedicated snapshot instance `s728` (`http://127.0.0.1:8916`, production snapshot
  `20261029-1605`). Its only purpose is this batch's content and visual
  acceptance. Recycle immediately after merge/deploy; do not retain as a
  general-purpose review instance.
- Real WordPress reviewed-pair write and exact readback succeeded. A second
  plan reports both pages unchanged.
- EN and DE were captured at 1440 and 390 through the repository's lossless
  `tests/visual/pixel-parity.mjs`. The four rendered pages have no horizontal
  overflow (`scrollWidth` equals 1440 or 390).
- The row is the ruled change. Exact comparison above the inserted row's margin
  box reports **0 differing pixels** in all four cases. The row has a fractional
  CSS height, so the evidence does not claim downstream integer-crop pixel
  equality; it separately records equal downstream DOM translation and unchanged
  heights in `pixel/layout-result.json`. Raw full-page PNGs, geometry and the
  limited pixel result remain under `pixel/`.
- The four rendered row crops were visually inspected: four readable cells at
  desktop and four stacked facts at 390, in both languages.
- The real trade library readback through the same WordPress instance returns
  200 for `/faq-download/` and `/de/faq-dokumente/`. Both render the corrected
  contact workflow; the old “Open Warranty & Replacements”, signed-in account,
  and German signed-in-account phrases are absent.
