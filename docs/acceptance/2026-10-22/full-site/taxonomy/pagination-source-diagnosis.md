# Product-family pagination: source diagnosis and minimum consistent repair

## Result and boundary

The duplicate SAJ page is caused by **two different pagination units and consumers**. WordPress/WooCommerce paginates individual products using native `paged`; the customer-facing LC grid re-queries the entire archive, groups product families, and slices only by the `product-page` query parameter. No current consumer translates the native product page into a family page. This is not a failed native taxonomy match, an LC template assignment failure, or a reason to redesign the grid.

This was a read-only investigation of the shared-archive worktree and already captured evidence. No product/test source, instance, option, cache, process or production environment was changed. The only output is this document. Existing uncommitted taxonomy, LC, empty-state, PO and metadata work is preserved. No fresh HTTP/browser acceptance was performed.

## Replayed actual evidence

I independently replayed the captured records with Python, comparing the arrays rather than inferring success from HTTP status:

| Saved consumer | Root | Native page two | Comparison |
|---|---:|---:|---|
| Actual EN browser `View product` destinations | 13 family-card links | 13 family-card links | Exact same ordered destinations |
| Native main-query product IDs | 16 products | 16 products | Zero shared IDs; page-two `paged=2` |

Browser evidence: [root](browser-20261021T223526140Z/en-390-saj-root.json), [EN page two](browser-20261021T223526140Z/en-390-saj-native-page2.json), [DE page two](browser-20261021T223526140Z/de-390-saj-native-page2.json). Native evidence: [stable 90-request record](20261021T222929002875Z-758f5591/native-http-results.json). The later 90-request run `20261021T235706763717Z-8367eccc/` is separate evidence for the final shared-archive/empty-root source; neither run proves correct displayed pagination.

The saved browser page-two addresses also propagate `/page/2/` or `/seite/2/` into filter links. Those are native path links, not evidence of a second family slice. The root has canonical plus EN/DE/x-default alternates; native page two has neither. Cookie text in those early captures limits visual conclusions, but does not change the captured destination arrays or native query records.

## Exact causal chain

1. WooCommerce `WC_Query::product_query()` sets the main-query page size through `loop_shop_per_page` unless already specified, then calls `woocommerce_product_query`. The captured request has `posts_per_page=16`, `paged=2`, `wc_query=product_query`, correct shared `product_brand` identity and language. See the locally available upstream source `20261021-1023/live/plugins/woocommerce/includes/class-wc-query.php:566–605`.
2. `ProductFilters::filter()` returns early for no facet selection plus Recommended sort, leaving this ordinary native paging intact ([ProductFilters.php](../../../../../plugins/linker-commerce/includes/Storefront/ProductFilters.php), lines 61–80). A selected filter or nondefault sort instead sets main-query `posts_per_page=-1`. Thus filtered and unfiltered requests already expose different native paging behavior.
3. `ProductFilters::archive_product_ids()` performs a separate `get_posts` with `posts_per_page=-1` and the queried taxonomy/term; `filtered_product_ids()` applies the site's filters and ordering to that complete set (same source, lines 634–708). The family renderer deliberately does not read the native main-query slice.
4. `ProductShortcodes::products_families()` groups that complete set via `family_rows()`, reads only `$_GET['product-page']`, and slices 24 families (lines 1456–1473). `PER_PAGE_FAMILIES=24` is the existing displayed design, not the native 16-product size (line 33). `family_rows()` retains all in-scope mutual members and one lead per family (lines 1679–1699).
5. The LC archive template invokes `[linker_products_families]`; there is no native product loop around it (EN/DE `content/livecanvas/*archive_product.html:36–40`). Count and pager independently repeat the whole-family calculation and independently read `product-page` (ProductShortcodes lines 1482–1521).
6. SAJ has 13 displayed families. Both `/brand/saj/` and `/brand/saj/page/2/` lack `product-page`, so both select family page one and render all 13. The family pager emits nothing because `ceil(13/24)=1`. A correct native 16-product slice therefore proves a different consumer from the one customers see.

## What missing head tags actually establish

**Hreflang cause is exact:** Polylang's `PLL_Frontend_Filters_Links::wp_head()` returns immediately for `is_paged()` before constructing alternates or invoking `pll_rel_hreflang_attributes`. See local upstream `20261021-1023/live/plugins/polylang/src/frontend/frontend-filters-links.php:199–246`. Our `Seo::hreflangs()` and `GermanRoutes::hreflangs()` filters cannot restore a tag when that upstream call never happens. The header/footer switchers use a separate native translation consumer and may still preserve the page number. Missing page-two hreflang is existing native behavior; it must not be represented as proof that the new shared taxonomy rule failed.

**Canonical remains conditional:** available SEOPress source skips registering canonical output when the effective noindex result is `1` or `yes`, unless the canonical-on-noindex filter opts in. Paged-noindex is one possible source of that result (`options-titles-metas.php:794–835, 1147–1148`). If canonical output is enabled, its paged branch uses the current path (lines 1194–1249). The stored probe did not capture the effective noindex result, `seopress_titles_paged_noindex`, robots output, or this gate's filters. The parent confirms no such option readback is available yet. Consequently this document does **not** claim the exact runtime canonical-suppression condition is proven. A scoped native read of that effective value and emitted robots is still needed.

For a true `?product-page=2` request, WordPress does not automatically set `is_paged()` from this Woo-shortcode parameter. The available default SEOPress path construction also omits query strings. Without a family-aware policy, true second-family-page content can therefore receive root metadata while native product page two receives paged treatment. This is source-derived risk to verify, not a newly captured HTTP fact.

## Invalid and out-of-range `product-page` behavior

These are direct consequences of current renderer/count/pager source; this reviewer did not request these URLs from an instance:

| Request value | Grid reader and count | Pager reader | Present consequence |
|---|---|---|---|
| Missing, `0`, negative, nonnumeric | Cast then lower-bound to 1 | Lower-bound to 1 | First-family-page display; no shared address-normalization contract |
| Valid positive page within family count | That family slice | Same numeric current page | Intended family behavior |
| `2` with SAJ's 13 families | Empty slice; count `25–13 / 13 product families` | No pager, because only one family page | Native main query still has posts; LC `!have_posts` does not show the empty-state guidance |
| Page beyond last on a multi-page family set | Empty slice and `from > to` count | Clamps current indicator to the final family page | Grid, count and current-page control contradict each other |
| Very large or nonscalar value | No scalar/strict positive-integer validation before casts and offset multiplication | Separately clamps | Must be normalized before offset arithmetic; do not assume casting is a complete validation contract |

`products_family_pagination()` generates only numeric `1..ceil(families/24)` links for the current computed family set. **It does not generate SAJ family page two.** The unwanted native address enters through native routing, direct/bookmarked requests and the language/path consumers, not the SAJ family pager.

There are related continuity defects within the same mechanism:

- `archive_base_url()` starts from native term/shop root and does not add the current filter/search/sort parameters; family pager URLs can drop the selected set despite its source comment saying they are retained (ProductShortcodes lines 1657–1662 and 1510–1519).
- `filter_url()` preserves the request path and all existing GET parameters except the changed facet/sort, so it can retain both a native `/page/2/` path and a stale `product-page` (lines 367–372). Removing a filter drops `product-page` but still retains a native paged path (lines 530–531).
- `LanguageLinks::LANGUAGE_QUERY_KEYS` currently does not include `product-page`, `q` or the family facets/sort. A language switch can reset a true family page or selection even though native path paging is preserved (LanguageLinks lines 28 and 118–151). This requires actual header/footer consumers in the repair's acceptance boundary; do not infer it from a language-correct root.

## Smallest coherent recommendation

Preserve the current card anatomy, family grouping/order, 24-family size, model picker and `product-page` public contract. No replacement grid, copied template, new rewrite pattern, synthetic family products, or global unpaged Woo query is needed for this narrow fix.

1. **One data-only family-page state.** Reuse the current filtered IDs and family grouping, calculated once per request, to provide total families, last family page, strictly validated requested page and current rows. Grid, count, pager, redirect policy and empty-state decision must use the same result. Keep full in-scope family members for model selection. This removes the present independent clamping and repeated query/group calculations without redesigning markup.
2. **Normalize addresses through native canonical/redirect seams.** Scope only to ordinary HTML shop/product-taxonomy requests already served by this family surface. Derive the root with native term/shop URL functions; retain allowed existing selection/sort/query context. Treat `/page/N/` and `/seite/N/` as compatibility addresses for the displayed family view and redirect to its existing `product-page` address after checking the family last page. Do not add another router or hand-build localized taxonomy bases.
3. **SAJ's specific decision:** with 13 families, the only valid family page is root. Native `/page/2/` represents a duplicate displayed first page, so a canonical redirect to that language's root is the minimum corrective behavior. It must not remain a 200 duplicate and must not become an empty family page merely because native `paged` says 2. A brand with more than 24 families has a real family page two; its alias should resolve to the existing root plus `product-page=2`, yielding different family cards. Native `max_num_pages` based on 16 individual products cannot decide either case.
4. **One out-of-range normalization.** For compatibility with the existing pager's upper clamp, redirect invalid/oversized family-page requests to a normalized valid family address (last family page for an excessive positive number, first page for invalid/nonpositive input). Empty results retain their valid empty root. If the project chooses native 404 instead, apply it consistently before rendering using the same family last-page calculation; it is a different explicit contract. Do not silently mix empty-grid rendering, last-page highlighting and a 200 response. Conflicting path/query page numbers need one deterministic precedence and one redirect, without a loop.
5. **Use existing native URL/pager machinery.** Woo already supports `product-page` for paginated shortcodes (`class-wc-shortcode-products.php:193–195`) and `woocommerce_pagination()` supports explicit loop metadata (`wc-template-functions.php:1767–1798`). Supply authoritative family total/current/per-page to the existing semantic surface, or use WordPress `paginate_links` with the same data. LC's `[lc_the_pagination]` by itself reads native `paged` and `wp_query->max_num_pages` (`templating-shortcodes.php:697–737`), so merely swapping tags would reintroduce product-unit paging. Keep the existing UI wording and WindPress classes unless native markup is deliberately adopted and visually checked.
6. **Apply selection and metadata to that same normalized address.** Pager keeps the validated current filters/search/sort; changing a filter/search/sort resets to family page one. Header/footer switches preserve the corresponding family slice and selection. Canonical should describe the normalized displayed family page, not automatically root every valid later slice. Preserve the site's deliberate noindex policy until its actual configuration is read; do not broadly enable page-two hreflang or canonical as a workaround for the display bug.

A deeper alternative would put only family leads into the native main query and paginate that query at 24, allowing native `found_posts`, last-page/404, Woo loop and LC pagination to agree. That requires making every query/visibility/filter/sort consumer use the same family index and preserving full member payloads. It is more invasive than compatibility-address normalization and is **not required for this narrow repair**. Simply feeding current native 16-product slices into `family_rows()` is incorrect: it can split a family across pages, repeat cards and remove model options.

## Required real consumer checks

- SAJ EN/DE root and legacy `/page/2/`/`/seite/2/`: final status/address, exactly 13 family cards, same unchanged products and full model choices, no empty grid or impossible count, no redirect loop. A native product page and a displayed family page must be asserted separately.
- A real set with more than 24 families: first/second/last family pages differ; ordered family leads do not repeat, union equals the complete expected family set, member options remain complete. Direct URL, actual Next/Previous/number click, back/forward and reload agree.
- `product-page=0`, negative, text, nonscalar, enormous number, just-beyond-last, `product-page=1`, and conflicting native/query page values: assert the chosen normalization or native 404 contract, valid counters and no PHP error.
- Search/filter/sort from deep pages: preserve intended selection/order, reset page where appropriate, handle zero results with existing LC guidance and clear action. Numeric pager targets alone are insufficient.
- Header and footer EN→DE→EN on a true later family page, including search/facets/sort; inspect the returned family identities, not only language or term ID. Read final canonical, robots and any actual alternates after redirect; scope SEO claims to the configured native policy.
- Shop, product category, brand, series and another public product attribute; shared-taxonomy aliases, valid empty root, unknown term and native feeds. Exclude feed/REST/admin/secondary queries from HTML normalization. Keep existing native term IDs, translations, stock/catalog visibility and LC twin assignments unchanged.
- EN/DE ×1440/390 visual/keyboard acceptance of the existing pager, counts, long German labels, sticky clearance and filter transitions. This investigation supplies no visual PASS.

Only the source diagnosis and already captured duplicate-display evidence are established here. The proposed normalizer and all new edge consumers remain unimplemented and unverified.

## Subsequent native SEO readback on current main

The parent subsequently captured [the native shutdown-phase SEO values and emitted head](native-pagination-seo-shutdown-before.json) on the rebased local instance. This resolves the runtime uncertainty above without changing the original investigation's claims. The temporary observer was removed. The earlier `native-pagination-seo-before.json` sampled too early for the effective-noindex function and remains a diagnostic record.

The configured `seopress_titles_paged_noindex` is `1`. EN and DE SAJ roots have effective noindex `""`, index robots, root canonical and normal alternates. Their native second-page requests have `is_paged=true`, effective noindex `1`, `follow, noindex` robots, no canonical and no alternates. The English-form German `/page/2/` address first reaches the native `/seite/2/` address. These observed values establish the canonical-suppression gate for this instance; they do not justify disabling that deliberate policy.

The actual EN and DE shop `?product-page=2` requests have `is_paged=false`, effective noindex `""` and index robots. Their canonical is incorrectly the shop root while their alternates retain `product-page=2`. Thus the metadata mismatch for a real family page is confirmed by the native consumer, in addition to the display mismatch previously captured for native product paging. A repair must keep metadata consistent with the family address while respecting the configured paged-noindex policy. None of that normalization has been implemented by this document or by the basic shared-archive/empty-state candidate.
