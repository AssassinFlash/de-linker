# GoodWe EHA/ETA German family-card title — read-only diagnosis

The reported screenshot discrepancy is **not reproduced in the current native product data or rendered HTML**. No product/title/translation/template or instance data was changed. The parent's CUA frame `cua-final-20261022T0508/final-de-1440-page2-language.jpg` remains its own browser evidence; this child made no browser inspection or modification.

Native Polylang, post and Woo reads returned:

| EN ID ↔ DE ID | Native product/model | EN title suffix | DE title suffix | Selection fact |
| --- | --- | --- | --- | --- |
| 6526 ↔ 6569 | GW6K-EHA-G20; SKU DLK-GOODWE-GW6KEHAG20 | 6 kW single-phase power module | 6 kW einphasiges Leistungsmodul | phase 1 |
| 6513 ↔ 6582 | GW6K-ETA-G20; SKU DLK-GOODWE-GW6KETAG20 | 6 kW three-phase power module | 6 kW dreiphasiges Leistungsmodul | phase 3 |

`post_title`, native `WC_Product::get_name()` and `ProductView::fields()['title']` all distinguish EHA and ETA correctly. Both German native bodies likewise use their respective model and phase words. English `_tv_legacy_acf_json` distinguishes the two model descriptions and says `ESA Series`; the German rows have no such raw JSON. The view's localized ACF source is `Materials::acf()` (German `_linker_de_acf_json` on the paired source), not a free-standing family-name field. The raw English-context CLI series result is not treated as a German-page rendering claim.

One additional authorized local GET of `/de/produkte/?sort=name&product-page=2` independently parsed the actual first two `<article data-linker-family-card>` elements and their title anchors:

- ID 6569: `data-phase=1`, title **GoodWe ESA GW6K-EHA-G20 (6 kW einphasiges Leistungsmodul)**, URL identifies EHA.
- ID 6582: `data-phase=3`, title **GoodWe ESA GW6K-ETA-G20 (6 kW dreiphasiges Leistungsmodul)**, URL identifies ETA.

Both anchors have an empty `data-card-series-title`; these are their own product titles, not a shared series label substituted from EHA. `ProductShortcodes::products_card()` reads the actual loop product; a multi-member card may use `series_title()`, and `family_payload()` explicitly pairs each ID with that product's view title. `product-family.js` changes a title only after an explicit member selection and uses that selected member's payload. The current response therefore provides no evidence of a wrong-ID mapping or wrong stored German phase phrase. The screenshot/AX/DOM state must be reconciled before editing content; possible browser-specific mutation or visual-reading causes are unproven here.

Hosted PDF links were resolved to the existing local uploads and read with pdftotext, with **no external requests**:

| Hosted filename | SHA256 | Bounded evidence |
| --- | --- | --- |
| `GW_ESA-3-10kW_Datasheet_EMEA-EN_V1.1.pdf` | `fea12735d2e6038977675eb85d69506cd9a2650cff5e7afc0eea69ebd6bf470d` | Contains the GW6K-EHA-G20 model column; native source/attributes identify phase 1. This diagnosis does not infer a new phase assertion from an ambiguous general battery-system voltage note |
| `GW_ESA-5-30kW_Datasheet-EN.pdf` | `b681fbb51b1688476883c7f2c23599f12a1e51020b6980c9d61da952cc80543f` | Header explicitly says Three Phase and technical columns include GW6K-ETA-G20 |
| `GW_ESA-5-30kW_Datasheet_EMEA-DE_V1.1.pdf` | `ce3e2552a6a21ff8b78988006f344619776c7cf01796cf172338040119569f9a` | Header says Dreiphasig; technical columns include GW6K-ETA-G20 |

Private actual reads, original HTML, parsed anchors, four product records and separate PDF text/hash provenance are under `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/family-title-readonly-20261022T051120964136Z`. The PHP 8.3 read process used sharedarchives PHPRC, disabled WP cron only for that process, and made no save/setter/cart/session/business/mail calls. An initial Python print-only summary encountered the absent German legacy array after the full successful PHP JSON capture; the captured four records remained intact and were read without rerunning or altering product data.

Pagination/source selection can pass its bounded HTTP checks while this reported browser discrepancy remains unclassified. Neither conclusion is a claim of whole-page visual or production acceptance.
