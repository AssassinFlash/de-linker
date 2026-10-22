# Empty shared archives — native switching and LC rendering design

Status: source-backed design recommendation, pending isolated local probes and an implementation decision. This document does not claim an implemented fix, a native matcher probe or a visual PASS. The reviewer read source and retained parent evidence only; no source, instance option, template assignment, term or production state was changed.

## Evidence and separate defects

The parent-executed `20261021T222929002875Z-758f5591/native-http-results.json` contains twelve root observations for the six empty brands DEHN, LAPP, MBS, Mersen, Stäubli and Trina Solar, each in EN and DE. The reviewer independently inspected those records: each returns 200, has a matching canonical and a real shared `product_brand` term, and the opposite-language switch points to the language home. These are valid empty archives, not missing routes. Shared term count zero is a fact to retain; do not turn it into a synthetic positive count or a missing German translation.

The parent's saved `browser-20261021T223526140Z/en-1440-empty-brand-current-fallback.jpg` also shows a separate rendering defect: a small DEHN title, native breadcrumb and default Woo no-products notice occupy the area between the site's header/footer, instead of the existing LC product-archive surface. The reviewer inspected that saved image, not the live browser. The parent reports nonempty Chint uses the normal LC surface. HTTP 200/canonical success does not close either the language-continuity or empty-surface requirement.

The parent subsequently reports a second actual empty-loop consumer: the otherwise populated Chint archive with `q=linker-owned-no-match-20261022` also falls to bare Woo, losing `#linker-products` and its search/Clear escape. This source has `ProductFilters::requested()` reading the existing custom `q` filter. The rendering repair therefore cannot be limited to raw zero-count brands; it must preserve the established LC surface for valid product-taxonomy requests whose existing filters/search yield no products. This observation does not broaden the separate empty-root language-hide policy to unknown pages or arbitrary searches.

## Native language-switch root cause

Inspected Polylang 3.8.11 source is under `/Users/chesterjohn/de-linker-local/sharedarchives/wordpress/wp-content/plugins/polylang/` (the same relevant native code was also read from the privacy-review installation).

- `src/frontend/frontend-links.php::get_translation_url()` reaches **Other archives** for untranslated-but-filtered shared taxonomies. Lines 149–159 collect the post type and filtered-taxonomy query variables, count the target-language posts, then call `pll_hide_archive_translation_url` with `!$count`, target language and the count arguments.
- When the archive is empty, the default hide value is true, so the native branch does not call `get_archive_url()`.
- `src/switcher.php` lines 151–171 sees the missing translation URL and uses the language home unless the caller asks to hide that entry. `Presentation\LanguageLinks::translated_switcher_url()` already requests `hide_if_empty=0`; that option concerns languages with no content, not the earlier archive-count decision.
- `LanguageLinks::translated_permalink()` finds no translated term for this intentionally shared taxonomy and retains the native switcher result. Inventing a term pair to defeat this branch would violate the shared-term model.

The already reviewed `woocommerce_product_query` declaration addresses an *incorrect* empty post-type count for nonempty product archives. It does not make a genuinely empty target archive nonempty. These are distinct causes.

## Exhaustion of existing language seams

| Existing mechanism | Assessment for this defect |
| --- | --- |
| `pll_the_languages(... hide_if_empty=0)` | Already used by the adapter; does not override the archive-count hide decision. Changing only this cannot repair the case. |
| **`pll_hide_archive_translation_url`** | Preferred narrow native seam. Permit the valid shared root despite zero target posts; Polylang continues to generate the actual URL through `get_archive_url()`, configured language model and existing project filters. No fake count or custom URL builder is needed. |
| `Presentation\LanguageLinks` adapter | Possible fallback for header/footer only, but would bypass the native decision and require a separate target-language shared-term URL path. It would not by itself fix native alternate-link consumers. Do not add this second policy before probing the native hide filter. |
| `pll_translation_url` or `pll_pre_translation_url` | Possible later/earlier fallback if the native hide seam proves insufficient. Requires native language resolution and archive/term-link generation, preserving existing valid results and avoiding recursion. More responsibility than changing the existing hide decision; not the first choice. |
| `pll_the_language_link` | Can replace only switcher links after native resolution. Leaves other native translation consumers divergent; less suitable than the archive seam. |
| Translated terms, OR taxonomy query, forged count, hard-coded `/de/` prefix | Rejected. These change identity/data or replace native routing to conceal a display policy. |

### Proposed hide-filter contract

Return the incoming hide decision unchanged outside a **valid current shared product archive root**. Inside that narrow case, return false so the existing native branch calls its own `get_archive_url($language)`; do not return a fabricated URL or change the count.

Eligibility must be based on the resolved main query and real queried `WP_Term`, not a guessed URL:

- Main archive query, real positive term ID, taxonomy in the approved filtered/shared list, and actual public product-taxonomy registration.
- The term remains untranslated/shared. Its current query variables and product context must correspond to that same resolved taxonomy/term; explicit unrelated post-type queries are not silently broadened.
- Not 404, unknown term, search, feed or paged request. Restrict this first change to the valid root; retain native behavior for out-of-range pages and the separate pagination issue below.
- The target language is a configured native language; existing valid native links remain valid. Preserve the adapter's established query handling and current-language self link.

This hook must be registered before the first native translation URL is cached/rendered. A late filter added after the switcher's per-language URL cache has been populated does not prove normal request behavior. A small native integration test must prove the target URL follows `get_archive_url()` and the configured `brand` base in both directions, including the existing German route filters. The `brand` option pin and its explicit rewrite activation remain prerequisites; this design does not reintroduce locale-dependent `Marke` paths.

Using this native seam also keeps header/footer and native translation consumers on one policy. Actual canonical/hreflang output must still be read back; a generated switch URL alone is not proof that the relevant head renderer emitted alternates.

## Why the empty archive misses LC

The installed LiveCanvas native matcher is `modules/templating.php::lc_use_dynamic_templates()`:

1. For a taxonomy archive, lines 62–65 look first for `is_archive_for_tax_<taxonomy>__<slug>`, then `is_archive_for_tax_<taxonomy>`.
2. If neither assignment exists, lines 71–76 try post-type archive assignments by comparing **`get_post_type()` of the current global post** with registered types. This is not `get_query_var('post_type')`.
3. The repository `Presentation\Templates::FILES` currently owns `is_archive_for_post_type_product`; its German twin uses `de/archive_product.html`. A nonempty product archive can reach that fallback through a product post. With an empty loop there need be no such post, so the generic product assignment is not a reliable matcher.
4. If no template ID is found, native LC passes through the theme template. Picostrap's `woocommerce/archive-product.php` prints its wrapper, breadcrumb/header, then calls `woocommerce_no_products_found` when `woocommerce_product_loop()` is false. This matches the parent's bare-Woo capture.

This is a source-backed matcher explanation awaiting native readback of the actual empty request's global post, assignment lookup and chosen template ID. The existing Woo query fix supplies a query variable; it cannot by itself make an empty global post exist for `get_post_type()`.

### Preferred LC-native repair

Use LC's existing taxonomy assignment mechanism so the chosen template does not depend on a first product. `modules/templating-admin.php:77–85` exposes generic public taxonomy archive checkboxes and per-term assignments, including empty terms (`hide_empty=false`). Native `lc_get_template_id()` reads those assignment meta keys.

First inventory both languages' existing assignments and exact template IDs. If no conflicting explicit ownership exists, add these native generic assignments to the **existing product-archive EN/DE template pair**:

- `is_archive_for_tax_product_brand = 1`
- `is_archive_for_tax_pa_brand = 1`
- `is_archive_for_tax_pa_series = 1`

Reuse the same owned template IDs and same EN/DE HTML exports. Do not create a parallel page layout, copy one template per empty brand, or overwrite an intentional per-term template. Encode the assignment installation, drift/readback and rollback in the existing `present`/template metadata contract; an ad hoc local assignment must not be presented as a reproducible deployment. Preserve native Polylang pairing/language lookup, unrelated assignment keys and any preexisting explicit taxonomy/term templates. Refuse or report a conflict rather than silently taking another template's assignment.

These three assignments are the immediate shared-taxonomy set, not an authorization to leave other existing product archives broken when filtered empty. Inventory the currently supported public product-taxonomy archives (including translated categories and attributes) and their native LC assignments; the same existing product-archive template must remain reachable for their valid empty filter/search states, independent of a first product. Add only the missing, approved native assignments or prove an already existing supported matcher. Preserve explicit custom template ownership; do not indiscriminately assign every taxonomy or change LC's global search-template precedence. Test the real custom `q` path separately from WordPress's `is_search()`/`s` path.

Once LC resolves the existing export, `archive_product.html` already includes `[linker_products_empty]` within `#linker-products`; `ProductShortcodes::products_empty()` at line 410 checks `have_posts()` without advancing the loop and supplies the current translated empty fragment. All container/layout/styling continues to come from LC and WindPress. Verify its current guidance is useful for an unfiltered empty brand; a Clear action that stays empty is not by itself a useful escape. Reuse native localized products/contact destinations for any approved guidance, and apply the required EN/DE copy review if wording changes.

### Other render seams considered

| Mechanism | Assessment |
| --- | --- |
| Native LC taxonomy assignment | Preferred: already exposed by the installed admin/matcher and independent of a product being present. Keeps the existing page composition and template pair. |
| Woo `woocommerce_no_products_found` / native notice | Correct native indication that the loop is empty, but reached inside the fallback theme after wrappers/breadcrumb/title. Styling or appending a whole LC page there cannot restore the same full surface cleanly. Do not build PHP layout in this hook. |
| Existing `[linker_products_empty]` | Already available inside the accepted LC surface. Its absence in the screenshot is a matcher problem first, not proof that its conditional needs replacing. |
| `lc_modify_template_id` narrow adapter | Native extension point if actual probes establish an assignment limitation. Must then select an existing LC ID only and preserve explicit assignments; no rendered PHP layout. The generic assignment path must be tested before taking this custom fallback. |
| New theme override, template takeover, dummy product, forced positive loop | Rejected as the first repair. They bypass the native matcher or falsify the product/empty state. |

Back up exact assignment metadata and template pair identities before any local write. A future production metadata change is a data write with the project's full/incremental backup and exact readback requirements. Rollback restores prior meta presence/values and template selection; it must not delete preexisting templates or alter term relationships. This reviewer performed no assignment or instance write.

## Required boundary tests and native probes

1. Drive the actual native archive-hide filter for the twelve known empty root URLs. Before/after counts, shared term IDs and product assignments stay unchanged. Header/footer EN→DE→EN remain on the corresponding empty brand, with matching canonical/language and no redirect loop. Also read native alternates; do not infer them from link construction.
2. Guard negatives: unknown term, actual 404, out-of-range `paged`, feed, search, other taxonomy, non-product explicit query and non-main context preserve native decisions. Nonempty shared archives, translated categories, shop, singular products and account endpoints retain existing behavior.
3. Native LC matcher probe before changing assignments: record `get_post_type()`, main query type, queried term, generic/per-term taxonomy assignment lookups, existing product archive ID and `lc_rendered_dynamic_template_id`. Compare empty and nonempty EN/DE. After the controlled metadata change, the empty request must resolve the intended existing language template and the real LC export must render.
4. Test `present` idempotence, drift detection, metadata conflict refusal and rollback with an existing template pair; content bytes, unrelated assignments and term data must survive. A second run must not create more templates or assignment duplicates.
5. Actual EN/DE × 1440/390 empty-state captures: raw zero-count brand and existing populated Chint with the no-match custom `q` filter, plus a supported product-category/attribute empty filter case. `#linker-products` and the accepted layout remain present; the real input/Clear action can return to the populated result without manual URL repair. Require no duplicate native wrapper/title/notices, honest zero results, readable branded heading and useful localized navigation; no stale model/price, horizontal overflow or fake product cards. A 200 alone cannot satisfy this test.

## Separate open pagination/presentation issue

The parent observes native page-2 requests rendering the same complete thirteen product families as the root, without an actual family pager, and with missing canonical/hreflang. Preserve that observation as open; native post-ID slices and HTTP success do not prove displayed pagination.

There is a source boundary explaining why native-query assertions are insufficient: `ProductShortcodes::products_families()` and `products_family_count()` read `$_GET['product-page']` (lines 1457/1482), while `products_family_pagination()` emits `product-page` links (lines 1494–1516). The displayed family grid reads `ProductFilters::filtered_product_ids()` across the archive, not the native main query's `paged` slice. No family page is implied merely by `/page/2/` or `/seite/2/`.

Choosing the canonical/pagination contract for those addresses is separate from preserving a valid empty root switch. Keep the empty-root hook scoped so it does not manufacture page-2 alternates or relax native 404 behavior before that presentation/SEO defect is designed and verified.
