# Chint brand language switch discovery

Status: confirmed live customer-path defect; repair and full taxonomy coverage pending.

On the actual production desktop page `https://de-linker.com/brand/chint/`, the header and footer German language links both point to `https://de-linker.com/de/brand/chint/`. The English page renders one product family, Chint DTSU666, product2281. Clicking the observed header DE link opens the German page titled “Seite nicht gefunden | Linker”, with the rendered 404 recovery screen and no product cards. The document language is de-DE. This is an observed site link, not a guessed German URL. A separate native HTTP read confirms status404.

Source-page DOM has `archive tax-product_brand term-chint term-205` and canonical `/brand/chint/`, establishing the actual taxonomy resolver for this sample rather than assuming the same-URL pa_brand alias is serving it. Native WP-CLI reads term205 as product_brand, slug chint, count2, language false, translated_taxonomy=false and the same English URL. This is not a count defect: two raw term assignments and one displayed family are different measures. The missing German route and current language-link construction still require a root-cause repair; these observations do not establish that changing the taxonomy translation setting is the correct fix.

Raw Computer Use captures: `chint-en-1440-source.png` and `chint-de-1440-switch-404.png`. The source capture was taken after returning from the failed switch; it is not a fabricated pre-click frame. Browser emulation was reset before this discovery and the actual innerWidth was1440. This is discovery evidence under the current live release, not final version-bound acceptance or proof of all brand/series routes.

The inventory's39 lang=false term records (34 unique URLs with five aliases) remain unresolved as a group. This first actual language switch proves that a baseline URL count alone misses a customer-visible destination failure. Inspect each native switch/resolver/product set; do not manufacture all German URLs by prefixing `/de/`, mark the destinations passed, or call this one Chint case proof that every brand is broken.
