# Product content correctness sweep (2026-10-29)

Published catalogue inventory for customer-visible product facts. Evidence is
the local instance `sweepproduct` after loading snapshot
`/Users/chesterjohn/de-linker-data/20261029-1601` (taken 2026-10-29T08:05:06Z,
loaded 2026-10-29T08:10:39Z). WordPress on that instance is 7.1.4. No
production write, and no local content write: the inherited migration was not
applied.

Owner constraint for this pass: change customer-visible copy only where a
hosted source proves the current wording states a false fact. Keep marketing
wording that is not factually wrong. A spec, unit or FAQ change needs that
same source proof.

## Surface read

| Surface | Count | Consumer used |
|---|---|---|
| Published products | 172 (86 EN, 86 DE) | Woo `product` posts |
| Visible EN products | 85 | `catalog_visibility != hidden` |
| Hidden published EN product | 1 | Trina `TSM-460NEG9R.28`, guest URL 404 |
| Draft products | 362 | Not a customer surface |
| `product_brand` terms | 11, seven with count 0 | Archive query rewrites membership to `pa_brand` |
| Engineering feed | 85 products, schema 1, `figure_projection_version` 2 | `GET /wp-json/linker/v1/engineering-feed` |
| Visible products with publication downloads | 85 / 85 | `ProductView::downloads()` |

Customer spec table comes from `_tv_legacy_acf_json` / `_linker_de_acf_json`
(`linker_specs` is empty on every published product). Purchase-panel key
stats come from `Materials::key_stats()`, which reads cited figures or the
material registry. German pages read `_linker_de_acf_json` on the English
source row.

## Verdict

No source-backed factual correction qualifies. The inherited migration (100
label/unit moves on five products, plus deletion of seven empty brand terms)
was not applied. The heuristic file `output/audit_v1.json` (2,166 rows) is
mostly a shape detector, not a defect list.

## What was checked, and what it showed

Published EN and DE spec rows were aligned by SKU and row index. After
treating `91.0` and `91,0` as the same number, the only remaining EN/DE
numeric difference is the enclosure line `max. 4,000 m` versus `max. 4000 m`
on five GoodWe ETR inverters. That is a thousands-separator glyph, not a
different altitude.

Same-group duplicate labels with different values: 0. Cross-group repeats
(cabinet weight versus inverter weight, system energy versus module energy,
on-grid current versus backup current) are different quantities. The
heuristic `SPEC-DUPLABEL` rows are this pattern.

`SelectionFacts` rated power and nominal energy match the spec row for the
same quantity on every visible product, including the datasheet distinction
the page already states: SAJ H2-30K-T3-DE and CHS2-29.9K-T4-X publish
`29999 W`, and the hosted H2 10–30K datasheet column for H2-30K-T3-DE is
`29999`, not `30000`.

Local page readback for GW99.99K-ET-G10:

- EN key stat `Rated AC power | 99.99 kW`; spec row `Nominal power (kW) | 99.99`
- DE key stat `AC-Nennleistung | 99,99 kW`; spec row `Nennleistung (kW) | 99,99`

The unit is visible in both places. Moving `(kW)` out of the label would
change wording without changing the fact.

Brand archives `/brand/trina-solar/`, `/brand/ecoflow/`, `/brand/dehn/` and
`/brand/mbs/` answer 200 with the empty state. The MBS term description is
not rendered. The 2026-10-22 taxonomy acceptance already recorded these
empty archives as valid empty routes, not missing products.

GW208.9-BAT-LCD-G10 shows nominal voltage `665.6 V` and operating range
`700 ~ 1000 V`. Both figures are the GW208.9-BAT-LCD-G10 column of the
hosted V1.0 datasheet
`uploads/2026/07/delinker-goodwe_batc208-datasheet.pdf` (weight on that
column is `≤2105 kg`, which the spec table also states). Later V1.1 and
V2.2 sheets drop that column and keep only LC 208.9 and LCD 261.2. The
page matches the datasheet it cites. It was not rewritten to a sheet that
no longer names the model.

GW9.0-BAT-D-G20 key stats `10.7 A` / `11.8 A` match the GW9.0 column of
`GW_ESA-5-30kW_Datasheet-EN.pdf`.

## Heuristic rows, classified

| Code | Rows | Disposition |
|---|---|---|
| `SPEC-NO-UNIT` | 1,037 | Benign. IP ratings, chemistry, counts, mounting and power-factor text have no measurement unit. |
| `DOC-MODEL-MISMATCH` | 508 | Benign for family datasheets, warranties and declarations. A GW60K-STS sheet named `STS-30-60kW` covers GW60K-STS-G10. |
| `DOC-BRAND-MISMATCH` | 417 | False positive. The flag fires when the file name contains the product's own brand. |
| `SPEC-UNIT-IN-VALUE` | 139 | Benign compound values (`180.5 A / 180.5 A`, `160–1000 V`). Splitting them would change a single stated range. |
| `SPEC-DUPLABEL` | 44 | Benign cross-group repeats. No same-group value conflict. |
| `DOC-NO-DATASHEET` | 19 | Stale against the publication consumer. All 85 visible EN products return download rows. |
| `FAQ-ABSENT` | 2 | The hidden Trina module has no public FAQ. Absence is not a false answer. No FAQ was invented. |

`SPEC-NO-UNIT` also mis-counts the five products whose units sit in the
label. Thirteen visible products have that shape for every measured row,
and twenty-three mix it with a unit column. It is not limited to the five
products named in the inherited migration, and it is not a false fact.

## Not applied

`tools/migrate/sweep-product-facts.php` remains untracked. Its ten pinned
meta edits only move a parenthetical unit from `spec_label` into
`spec_unit` (50 English rows and 50 German rows on posts 1947, 1948, 2003,
2281 and 2394). Values do not change. Rollback would be byte-exact, but the
edit is a label rewrite, so it stays unapplied. The seven `product_brand`
deletions (EcoFlow, DEHN, LAPP, MBS, Mersen, Stäubli, Trina Solar) stay
unapplied for the acceptance reason above.

## Unresolved

- HS2-5K/6K/8K/10K-T2-X purchase-panel weight is `32 kg` and that number is
  not repeated in the spec table. The HS2 PDF opened in this pass is the
  S2 sheet, not the T2-X datasheet the page links. Not changed.
- Engineering feed `ac_power_kw` is `unknown` for GW99.99K-ET-G10,
  GW100K-ET-G10, L260-OMNI, DTSU666 and GM330. The product page still
  states the rated figure. The feed omits a number; it does not publish a
  wrong one. A new cited figure was not added.
- V1.1/V2.2 BAT-C datasheets no longer list GW208.9-BAT-LCD-G10. The
  product still matches its linked V1.0 column. Whether that model should
  follow the later sheet is a source-succession question, not a proven
  false value.
- German `29,999 kW` on the ESA 29.999K description is the German decimal
  form of 29.999 kW. Replacing the comma with a dot would make a German
  reader read 29999 kW. Left as written.
- English document-library descriptions on German pages are the localisation
  sweep's production-data list, not a numeric fact error. Not rewritten here.
- Draft products were not treated as the customer surface.

Untracked exports kept beside this note: `output/audit_v1.json`,
`output/prod_products.json`, `output/prod_products2.json`, and the local
readbacks `output/local_inventory.json` and `output/consumer_en.json`.
