# Replication spec — storefront, shop and product pages (2026-10-11)

Owner ruling of 2026-10-11: the storefront's design is replicated from the LIVE
site's rendered output, decomposed to its root and implemented anew. The design
truth is the rendered live page (measured, not read from the old stylesheet);
implementation text is written fresh. This document is the decomposition: the
measured token table, the per-component anatomy and geometry, and the carrier
decision for every component — LiveCanvas native tag first, Woo native
mechanism second, WindPress for styles, and custom PHP only as a documented
data fragment with its exhaustion proof here.

Page types in scope: shop (`/products/`, DE `/de/produkte/`), product archive
(`/product-category/inverters/`, DE `/de/produkt-kategorie/wechselrichter/`),
single product (reference `goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh`,
EN and DE), 1440 and 390 wide.

## 1. Method and evidence

- Measurement instrument: `.scratch/t16-closure/measure.mjs` — loads a page in
  chromium (same browser both sides), scrolls it so lazy images settle, and
  dumps per-element `rect` plus ~80 computed properties. Dumps:
  `.scratch/t16-closure/truth/live-{shop,archive}-{en,de}-1440.json`,
  `live-pdp-de-{1440,390}.json`, `live-shop-en-390.json`,
  `live-pdp-1440.json` (EN battery page).
- Paired captures: `.scratch/t16-closure/capture_pairs.mjs` — full-page
  screenshots, live|t16, same browser, same viewport, same wait protocol, into
  `.scratch/t16-closure/pairs/`.
- DOM anchors are the live class names (`tv-woo-b2b-catalog`, `sf-card`,
  `card-identity`, `card-facts`, `card-exact-article`, `tv-storefront-pdp`,
  `pdp-*`); they are the reconciliation handles between the two pages.

## 2. Token table (measured on the live pages)

| Token | Value (measured) | Where seen |
| --- | --- | --- |
| Typeface | `"Plus Jakarta Sans", Inter, system-ui, -apple-system, "Segoe UI", sans-serif` | 326/339 PDP elements |
| Mono | `ui-monospace, SFMono-Regular, Menlo, monospace` | order numbers, 11 elements |
| Ink | `#15352f` (`rgb(21,53,47)`) | 204 PDP elements |
| Muted | `#596e67` (`rgb(89,110,103)`) | 113 elements |
| Teal (accent) | `#0c7f73` (`rgb(12,127,115)`) | links, benefit card 1, active tab |
| Paper / cream | `#f7f7f1` (`rgb(247,247,241)`) | PDP root, section nav, catalog root |
| Soft green panel | `#f0f4ef` (`rgb(240,244,239)`) | stat wrap, doc icon chip, project-check |
| Beige description panel | `#eaf0e4` (`rgb(234,240,228)`) | `.pdp-overview` |
| Tab track | `#e9eee7` (`rgb(233,238,231)`) | `.pdp-info-tabs` |
| Card paper | `#fff` | cards, disclosures, stat wrap |
| Line | `#d6ded7` (`rgb(214,222,215)`) | 1px borders everywhere |
| Card inner panel | `#f3f7f2` (`rgb(243,247,242)`) | `card-exact-article` |
| Wait dot | `#f97316` (`rgb(249,115,22)`) | `.pdp-dot.is-wait` |
| Radii | 12px controls/cards inner, 16px thumbs+tabs, 18px cards/disclosures, 20px pairing cards, 22px benefit cards, 28px description panel, 999px pills | measured per component |
| Type scale | 46 (catalog title) · 32/600 heading (section titles, −0.8px tracking) · 30/600 (`.pdp-h1`) · 15 (reading intro, line-height 28.5) · 14 (body) · 13 (stat rows, tools) · 12 (SKU, pills) · 11 (pairing SKU) | measured |
| Catalog container | 1240px content, 1440 viewport | `wb-bar`, `catalog-layout` |
| PDP container | 1360px | `.sf-container` |

## 3. Component anatomy and geometry (measured, 1440)

### 3.1 Single product page

| Component | Geometry | Key computed facts |
| --- | --- | --- |
| `#tv-storefront-pdp` | 1440×3636, padding 20px 0 80px | background `#f7f7f1` |
| `.sf-container` | x40 w1360 | |
| `.pdp-crumbs` | h18, gap 8, margin-bottom 24 | 12px, muted |
| `.pdp-layout` | grid 3×453.33px, row-gap 44 | gallery spans 2, purchase 1 |
| `.pdp-gallery` | grid `76px 812.66px`, gap 18 | thumb column LEFT of the image |
| `.pdp-gallery-pair` | 812.7×640, 2 columns | main + secondary image |
| `.pdp-thumbs` | w76, flex column, gap 12 | |
| `.pdp-thumb` | 72×72, padding 5, border 2px teal, radius 16 | |
| `aside.pdp-purchase` | w453.3, padding-left 40 | |
| `.pdp-buy-inner` | w413.3, `position: sticky` | |
| `.pdp-brand-logo` | 160×31 | |
| `.pdp-h1` | 30px/600 | |
| `.pdp-designation` | margin-top 8, 14px muted | |
| `.pdp-sku` | margin-top 12, 12px muted | |
| `.pdp-price` | margin-top 20 | |
| `.pdp-spec-list` | margin-top 20, border-top 1px, h153 | four rows |
| `.pdp-avail` | margin-top 20, padding 16 0, borders top+bottom | |
| `.pdp-dot` | 8×8, radius 50% | `is-wait` = `#f97316` |
| `.pdp-btn` | w413.3 h48, radius 12, padding 12 16 | dark `#15352f`/white; secondary white + 1px line + shadow |
| `.pdp-product-tools` | grid 3 ×132.4, gap 8, margin-top 16 | |
| `.pdp-tool` | h76, flex column, radius 12, 13px/500 | white, 1px line |
| `.pdp-project-check` | margin-top 16, radius 12, bg `#f0f4ef` | closed: h43 |
| `.pdp-project-choice` | h38, radius 999, padding 8 13, 12px/600 | |
| `.pdp-section-nav` | h71, sticky, padding 12 0, border-bottom | cream |
| `.pdp-section-link` | h44, radius 12, padding 10 12, 14px/500 | |
| `.pdp-block` | padding 40 0 | |
| `.pdp-overview` | radius 28, bg `#eaf0e4`, padding 40, grid `673.19px 550.81px`, gap 56 | the beige panel |
| `.pdp-kicker` | margin-bottom 12, 14px muted | |
| `.pdp-section-title` | 32px/600, tracking −0.8px | |
| `.pdp-overview-intro` | margin-top 20, 15px, line-height 28.5 | |
| `.pdp-benefits` | grid 4×328, gap 16, margin 32 0 16 | |
| `.pdp-benefit` | radius 22, padding 24, gap 12 | first card teal + white text |
| `.pdp-disclose` | w668 (content column), h58 closed, radius 18, padding-x 20, margin-bottom 24 | white, 1px line |
| `.pdp-stats-layout` | grid `627px 692.98px`, gap 40, margin-top 20 | |
| `.pdp-info-tabs` | h58, radius 16, padding 5, gap 5, bg `#e9eee7` | |
| `.pdp-stat-wrap` | radius 16, white, h291.7 | |
| `.pdp-stat-row` | grid `320.48px 320.5px`, gap 20, padding 14 16, border-bottom | 13px labels, 15px values |
| `.pdp-doc` | w670 h85, flex, gap 12, radius 18, padding 20, borders | two per row (the 2×2 grid) |
| `.pdp-doc-icon` | 40×40, radius 12, bg `#f0f4ef` | |
| `.pdp-faqs` | padding 40 0, border-top | |
| `.pdp-pairings` | grid 4×280, gap 16, margin-top 16 | 11 cards on the battery page |
| `.pdp-pairing` | 280×229, grid `88px 138px`, gap 6/16, radius 20, padding 18 | image 88 + copy 138 |
| `.pdp-pairing-name` | 14px/600, line-height 18.9 | |
| `.pdp-pairing-sku` | 11px muted | |
| `.pdp-pairing-footnote` | w640, margin-top 16, 15px reading | |

### 3.2 Shop and archive

| Component | Geometry | Key computed facts |
| --- | --- | --- |
| `.sf-catalog` | 1440 wide, padding 34 0 100 | background `#f7f7f1` |
| `.wb-head` | h278 | |
| `.wb-bar` | grid `642.53px 561.47px`, gap 22/36, margin-bottom 26 | title + search |
| `.wb-title` | 46px/600 | |
| `.wb-intro` | margin-top 14, 14px muted, max 640 | |
| `.wb-search` | h52, w642.5 | |
| `.wb-metarow` | 10px/700 teal, margin-bottom 26 | |
| `.wb-scope` | flex, gap 28, margin-bottom 30 | pills h46 |
| `.catalog-layout` | grid `210px 998px`, gap 32 | filter rail + results |
| `.wb-strip` | h44, gap 14, margin-bottom 20 | count + sort |
| `.catalog-grid` | grid 2×488, gap 22 | |
| `.sf-card` | 488 wide, flex column, gap 14, padding 20, radius 18, 1px line | archive cards 630 tall, shop 604 |
| `.card-media` | 446×200, radius 12 | |
| `.card-identity` | 446 wide | |
| `.card-facts` | grid 2×215, gap 12/16, 12px muted | |
| `.card-exact-article` | 446×62, padding 12, radius 12, bg `#f3f7f2`, 13px | |

## 4. Carrier decisions (native first)

Legend: **LP** = LiveCanvas template markup (composition lives here) ·
**NAT** = LiveCanvas native tag · **WOO** = WooCommerce native mechanism ·
**FRAG** = custom PHP data fragment (last resort, exhaustion proof below) ·
**JS** = interaction referenced by the template.

### 4.1 Single product template (`content/livecanvas/single_product.html`)

| Component | Carrier | Detail |
| --- | --- | --- |
| Page composition, section order, wrappers, headings, static copy | LP | the template holds `#tv-storefront-pdp > .sf-container > .pdp-layout + .pdp-content`, all `section`/`nav`/`details` frames and the English copy; the DE twin (`content/livecanvas/de/single_product.html`) holds the German copy |
| Shop URL in the crumb | NAT | `[lc_wc_get_page_url page="shop"]` (language-aware through Polylang) |
| Brand name, model | FRAG | `[linker_pdp_brand]`, `[linker_pdp_model]` — `pa_brand` / `pa_model` term reads |
| Product title in the description heading | NAT | `[lc_the_title]` |
| price area | FRAG | `[linker_pdp_price]` — the price GATE is business logic (precedent `linker_price`); the fragment prints only the link or the price |
| SKU text | NAT + LP | `[linker_pdp_sku]` (bare value), the label is template copy ("Item number:" / "Artikelnummer:") |
| key figures (4 rows) | FRAG | `[linker_pdp_key_stats]` — registry figures in the type's order; no native tag reads the material registry |
| availability + delivery sentence | FRAG | `[linker_pdp_availability]` — the freight outcome is a policy derivation |
| CTA + contact buttons | FRAG | `[linker_pdp_cta]`, `[linker_pdp_ask]` — the pricing state decides label and href |
| tools row (compare / ask / documents), compare chip | FRAG | `[linker_pdp_tools]` — per-product ids and localized labels inside attributes |
| project entry (plan with …) | LP + FRAG | `details.pdp-project-check`, summary, body and feedback `<p>` are template markup; `[linker_pdp_project_choices]` carries the 4 buttons with their per-product messages |
| gallery main/secondary images, thumbs | FRAG | `[linker_pdp_gallery_pair]`, `[linker_pdp_gallery_thumbs]` — attachment IDs (`_thumbnail_id` + `_product_image_gallery`) cannot be iterated by any native tag |
| description intro | FRAG | `[linker_pdp_intro]` — ACF JSON branch |
| benefit cards, disclosure rows | FRAG | `[linker_pdp_benefits]`, `[linker_pdp_disclosures]` — ACF `feature_cards` |
| technical data deck (tabs + panels) | FRAG | `[linker_pdp_specs]` — ACF `spec_groups` (or Woo attributes as fallback); the tab strip is server-rendered like the live deck, the JS only switches panels |
| project-fit section | LP (frame) + FRAG (body) | the section frame is guarded by `[lc_if condition="linker_pdp_has_scenes"]`; `[linker_pdp_scenes]` carries the scenario blocks |
| documents (2×2 cards) | FRAG | `[linker_pdp_downloads]` — the ACF download rows merged with the registry documents |
| FAQ rows | FRAG | `[linker_faqs]` — `_linker_faqs` (rows only; the frame and title are template copy, guarded by `linker_pdp_has_faqs`) |
| compatibility records | LP (frame) + FRAG (rows) | guarded by `[lc_if condition="linker_pdp_has_pairings"]`; `[linker_pdp_pairings]` carries the cards and the footnote |
| gallery viewer / spec tabs / assistant entries | JS | `pdp-ui.js` (binds the markup the template renders), `compare-selection.js` |
| site chrome contact entry | FRAG | `[linker_contact_link]` — the header/footer partials call it; it renders the contact page link with the product as the request subject |

**Exhaustion proofs for the fragments** (why no native tag carries them):
The registry and ACF data of these blocks live in one JSON blob per product
(`_tv_legacy_acf_json` / `_linker_de_acf_json`) or in the plugin's registry
files; LiveCanvas offers no JSON branch iteration (`lc_get_cf`/`lc_the_cf`
return a single meta value, `lc_get_posts` queries posts, neither walks a JSON
array), no attachment-ID list to image markup conversion
(`lc_the_thumbnail` is the featured image only), and no registry reads. Each
fragment prints values and invariant per-item rows with the live class names,
zero styles and zero design decisions; every visual property is decided in the
WindPress stylesheet.

### 4.2 Shop / archive templates

| Component | Carrier | Detail |
| --- | --- | --- |
| page frame, strip, grid, pagination | LP | the template holds the composition |
| result count, pagination | NAT | `[lc_wc_result_count]`, `[lc_the_pagination]` |
| the loop | NAT | `[lc_loop]` |
| catalog head (crumb row, title, intro, search, scope pills) | FRAG | `[linker_catalog_head]` — queried-term reads and facet links |
| filter rail | FRAG | `[linker_catalog_filters]` — facet counts are a data derivation |
| sort control | NAT + FRAG | `[linker_catalog_sort]` wraps `wc_catalog_ordering` semantics |
| product card | FRAG | `[linker_catalog_card]` — per-product facts, compare checkbox, prices gate |

Exhaustion proof for the catalog fragments is the same one: term-scoped facet
counts, per-product fact rows and the price gate have no native tag;
`lc_get_posts` and `lc_loop` render the loop, the fragments carry the card's
values.

## 5. Styles (WindPress layer)

Styles reach the pages only through the WindPress volume
(`linker-commerce content/windpress/*.css` → `wp linker-commerce present` copies
them into `uploads/windpress/data/` and imports them from `main.css`; the
compiled cache is produced by the WindPress admin compile — `just
windpress-compile t16`). The plugin enqueues no site CSS.

**State on 2026-10-11 (honest):** the volume currently carries
`storefront.css` (4352 lines) and `catalogue.css` (228 lines) that were copied
byte-for-byte from the live site's old plugin stylesheet in commit `378cef7`.
The owner's audit ruled that byte transfer a violation ("旧 CSS 字节搬运为违规")
and this document is the blueprint for replacing both files with a fresh,
token-driven authoring: section 2 and 3 above are the values such an authoring
must land, and section 4 marks the components its rules have to cover. The
replacement is NOT done in this round; the files, their import lines and the
compiled cache still hold the copied text.

## 6. State of the replacement and open items

**Authored so far (this round):** `content/windpress/pdp.css` — the product
page's styles written fresh from the measurements above (desktop geometry plus
the collapsing rules at 1100/900px), installed through `present` and compiled
into the cache. It deliberately overlaps the copied `storefront.css` on the
`pdp-*` selectors so the measured values win; the copied files still carry the
catalog and remain the open part of the replacement.

**Round-1 review items, repaired (2026-10-11, measured live|t16 with
`.scratch/t16-closure/review-facts.mjs`, `.scratch/t16-closure/verdict-probe.mjs`,
`/tmp/detail-probe.mjs` and `/tmp/panel-probe.mjs`):** the layout's grid areas
(the purchase column is row 1 only; the content spans all three), the gallery
(the rounded soft box is the image: bg `#f0f4ef`, radius 26px; thumbnails fill
their tiles 58×58/60×60 with `object-fit: contain`, the default tile border is
1px transparent), the key figures (the live page hides `.pdp-app-stat-icon`,
rows are flex 8px/16px), the disclosure rows of the tab deck (the deck's own
summary is out of the flow at `details.pdp-tab-disclosure > summary`), the tab
strip (active pill `#0c7f73`, 12px/500, 10px 8px), the content grid (668px ×
668px, the two disclosure rows one per column), the benefit cards (13px, the
first card's text `#d6e4d9`), the documents (grid `670px 670px`, card padding
20px, height 85), the tab panel (the inner summary hidden, the stat wrap
border-less at 15px/1.9), the page body (cream `#f7f7f1` through
`body:has(#tv-storefront-pdp)`), the catalog card's compare checkbox (44×44,
absolute 8/8, radius 50%, `aria-label="Compare: <name>"`), the archive/shop
subtitle (the generic line in both languages, the live German wording), the
tokens delivery (the presentation run now removes the Additional CSS copy the
header partial already serves; `#wp-custom-css` is absent, `--proto-accent`
count 3 = live) and the ETA documents (`Multilingual` instead of `MUL`, 13
cards = live's 13).

**Measured gaps still open (2026-10-11, paired captures in
`.scratch/t16-closure/pairs/`, pixel comparison of the overlap):**

1. The catalog pages' styles are still the copied live stylesheet, not a fresh
   authoring; the shop and archive do not render at parity because of that and
   because of item 3 below.
2. Product page, 1440: about 45% of the overlap differs (it was ~80% before
   `pdp.css`); the residual is concentrated in the purchase rail's fine
   geometry, the pairing cards' inner layout and the below-the-fold blocks. At
   390 the mobile page is ~1,270px taller than live and the mobile rules need
   another pass.
3. The live shop lists **65 product families** (24 per page, "1-24 / 65
   product families") — a grouping the current shop query does not implement;
   t16 lists 104 individual products, 16 per page. The shop's card grid, its
   search chips ("Batch/item numbers", "Identify a device from a nameplate
   photo") and the compare checkbox on each card are not built.
4. The site chrome (header/footer partials) differs: the live header carries
   the search icon, cart, account and the EN/DE switch; the t16 header does
   not render those controls in the same place.
5. The product page's style rules previously never reached the page at all —
   the live PDP is styled by `terravolt-b2b-core`'s `product-page.css` (and
   `commerce-ui.css`), which the earlier port did not carry; only the
   `storefront.css` fragment (readings, chips) applied. That is why the
   pre-existing captures showed the PDP largely unstyled.
6. `data-faq-count` on the FAQ section (an internal counter of the live markup,
   no visual effect) is not replicated; the section carries the live classes.
7. `data-compare-article` on a German page carries the German twin's id
   (the live page carries the English id); the comparison page resolves the
   products by id, and the German object is the one the German comparison page
   should show.
8. The compare chip's icon and the `sf-compare-chip` behaviour need the compare
   page flow (#66) to be exercised end to end.
