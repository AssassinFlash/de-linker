# PDP + Solution Configurator present-flow fix — evidence (2026-10-13)

Branch `fix/present-pdp-configurator`. What is asserted, and the commands that
produced it. The pixel gate (live|local full-page diff) stays with the main
session; this run judges structure and geometry.

## What the fix changes

- `Templates::FILES` has carried `is_single_product` since #54 — the template
  sync set was never the gap. What was missing: the German product export had
  no install path (it goes into the English template's Polylang twin now,
  `Templates::DE_FILES` + `sync_page_type_twins()`), and the product page's
  `#fit` section and its `Applications` nav link were gated on
  `image > 0 && checklist`, which no live product with a checklist satisfies
  (measured below). The Solution Configurator's page had no template and no
  assignment at all: its mount lived in an instance-local mu-plugin
  (`100-t109-configurator-mount.php`) that was never deployed — it is a
  LiveCanvas page, `[linker_configurator]` (linker-tools `Configurator\Mount`),
  and `Templates::PAGES` now assigns `linker-planner` / `linker-planer`.
- `Materials::gallery_ids()` read `_product_image_gallery` as an array; Woo
  stores one comma-separated list, so every product lost a picture and the
  thumbnail strip needed two ids it never saw.
- The desktop gallery rules in `content/windpress/pdp.css` lost the cascade to
  the storefront-volume copy WindPress compiles after them (pair became a
  two-up grid, second image shown, main image 400 px wide where the live page
  shows one 813 px picture). The live page settles the same conflict with
  `product-page.css` loaded after the storefront stylesheet; the rules now
  carry the file's own `body:has(#tv-storefront-pdp)` prefix, and the phone
  strip is one scrollable row of 60 px tiles as live's `product-page.css` has
  it.

## Instance

t110 (8975) was being re-bound and re-`present`ed by a second session while
this ran (its plugin symlinks flapped between checkouts; that lane's `present`
at 02:25:28 rewrote template 234). The verification therefore ran on the
uncontended copy of the same data: **sweep (8990)**, bound to this worktree
(`just up sweep`), i.e. the t110 snapshot + this branch's plugins.

```
just up sweep
python3 tools/migrate/13-media-meta.py --snapshot ~/de-linker-data/20261011-1732 apply \
  --wp "/opt/homebrew/opt/php@8.3/bin/php /opt/homebrew/bin/wp --path=$HOME/de-linker-local/sweep/wordpress" --write
just present sweep          # templates: created 2, updated 4, unchanged 9
just windpress-compile sweep
just present sweep          # templates: created 0, updated 0, unchanged 14 — idempotent, cache fresh
python3 tools/faq/import.py --wp "just wp sweep" --from docs/faq --write   # 106 products, 221 items
node docs/acceptance/2026-10-13/pdp-present/tools/shots.mjs \
  docs/acceptance/2026-10-13/pdp-present/sweep-8990 http://127.0.0.1:8990
```

The media-meta and FAQ writes are data steps, not `present` work: a fresh
instance needs `tools/migrate/13-media-meta.py` (featured-image bindings) and
`tools/faq/import.py` (the reviewed `_linker_faqs` corpus) exactly as the #16
assembly did — `present` installs the presentation layer only.

## Marker reads (curl, `?cbq=` busted; shots.json `marker: true` for all 12)

| page | markers |
| --- | --- |
| `/product/goodwe-gw60k-sts-g10/` | `tv-storefront-pdp`, `pdp-purchase`, `pdp-gallery-pair`, `pdp-thumbs` (3), `href="#fit">Applications`, `id="fit"`, `Where this model fits`, `Product questions` |
| `/de/produkt/goodwe-gw60k-sts-g10/` | same German (`Anwendungen`, `Wo dieses Modell passt`, `Produktfragen`, `Artikelnr.`, no `Item number:`) |
| `/linker-planner/`, `/de/linker-planer/` | `data-linker-app="configurator"` ×1, no `The facts that decide`, no `qcfg-root` |
| `/shop/` | `sf-catalog`, `catalog-grid`, `tv-woo-b2b-catalog` (unaffected) |

## Geometry, local vs live, same browser (shots.json)

|  | local 1440 | live 1440 | local 390 | live 390 |
| --- | --- | --- | --- | --- |
| `.pdp-gallery-pair` | 813 × 640 | 813 × 640 | 190 × 245 | 190 × 245 |
| `.pdp-gallery-main` | 813 × 640 | 813 × 640 | 190 × 245 | 190 × 245 |
| `.pdp-gallery-secondary` | 0 × 0, `display:none` | 0 × 0, `display:none` | — | — |
| `.pdp-thumb` / count | 72 × 72, 3 | 72 × 72, 3 | 60 × 60, 3 | 60 × 60, 3 |
| `.pdp-thumbs` | 76 × 628 | 76 × 640 | 190 × 68 | 190 × 68 |
| section nav | Description · Technical data · Applications · Documents | identical | identical | identical |
| `#fit` | 907 × 758 | 1360 × 616 | 358 × 801 | 358 × 608 |
| `.pdp-faqs` | 907 × 188 | 1360 × 180 | 358 × 162 | 358 × 167 |

Residuals, measured and not papered over:

- The section column is 907 px wide locally and 1360 px on live (`.pdp-content`
  is a column of the `pdp-layout` grid here; the live page lets `#fit` and the
  FAQ span wider). The blocks themselves render; their width is a `pdp-layout`
  question, not this ticket's.
- `.pdp-thumbs` is 12 px shorter at 1440 (628 vs 640) — the container is
  transparent and the tiles sit at its top, so nothing visible moves.
- Products whose scenarios carry only a scene image (32 of them, e.g. the SAJ
  HS2) render the live page's *other* `#fit` variant ("Product views and
  project settings." + `pdp-scene-reel` scene cards). The scenes shortcode does
  not implement that variant; those products stay without a `#fit` block, as
  they were before this branch. Recorded in `docs/specs/19-tool-pages.md`.
- The purchase column adds rows the live page shows further down (Weight,
  Dimensions) and the in-stock dot is orange (`is-wait`) where live's is green
  — product data / availability wording, outside this ticket.

## Configurator

`configurator-{en,de}-1440.png` and `configurator-en-390.png`: the React app
renders in the fused lay-out (left rail: Inputs · Solution · Design report;
right: the sizing form), the old page-body application is gone, and the
page prints exactly one mount point. The app is the built
`linker-tools/build/configurator.js` entry (`Mount::HANDLE`).

## Files

- `sweep-8990/` — the final evidence set (12 shots + `shots.json`) from the run
  above, sweep (8990) vs live, same browser and viewports.
- `pdp-*.png` at the top level — the earlier run of the same script against
  t110, before the nav-link and gallery-cascade changes; kept as the "before".
- `tools/shots.mjs` — the shot script. `node … <out-dir> [base-url]`.

## PHP checks

```
plugins/linker-commerce: vendor/bin/phpunit            # 875 tests, 4184 assertions, 43 skipped (integration, no site)
plugins/linker-tools:    vendor/bin/phpunit            # 100 tests, 1641 assertions
plugins/linker-commerce: vendor/bin/phpcs -q          # clean; phpstan: no errors
plugins/linker-tools:    vendor/bin/phpcs -q          # clean; phpstan: no errors
```
