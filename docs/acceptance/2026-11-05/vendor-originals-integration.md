# Vendor-originals integration 2026-11-05: BAT-C manual association gap closed

Companion to `docs/research/2026-11-04-vendor-originals.md` (target 2) and the
publication rules in `docs/specs/609-product-publication.md`.

## State of the four original-document targets

| Target | State (verified) |
| --- | --- |
| SGS Annex `250008RECO14-CER` (164 pp) | Not publicly available anywhere (two exhaustive research rounds; GoodWe publishes only the 1-page cover, as for the whole certificate family). Engineering does not claim its contents. |
| ET 75–100 kW quantitative envelope | Only in that unpublished Annex; the hosted datasheet/solution/user manuals are byte-identical to the current official versions. No quantitative envelope is claimed. |
| BAT-C 60–112.6 kWh quantitative data | Official 87-page User Manual V1.0 (2026-10-10) obtained and hosted; no plotted SOC×temperature derating curve is publicly published. |
| SAJ HS3/CB2 terminal maps | The hosted HS3 V4 / CB2 manuals are byte-identical to the current official files and already carry the complete public terminal/pin definitions. |

## Gap found and closed this round

The hosted BAT-C User Manual (Woo attachment 8508, sha256
`c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7` — exactly
the officially retrieved file) was associated only with product 1954
(GW61.4-BAT-AC-G10), although the manual covers the whole BAT-AC series
including GW112.6-BAT-AC-G10 (product 1955).

- Fix: appended the manual's document row to product 1955's
  `_linker_documents` (same row as 1954's). Production backup first
  (`cutover-20261105-0633`).
- Read-back: product 1955 has the row (11 document rows); the publication
  manifest's manual entry now carries `product_ids: [1954, 1955]`.
- GW92.1/GW102.4 are not in the Woo catalogue (no such products); GW261.2 is a
  different series (BAT-LCD) and correctly not associated.
- German twins carry no separate document rows; associations derive from the
  EN products, so no second write was needed.
- The Woo source revision changed; the ordinary publication worker's next poll
  builds the knowledge generation that includes the manual for GW112.6.
