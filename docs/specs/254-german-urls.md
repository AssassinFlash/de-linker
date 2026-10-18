# German addresses and independent titles

Authority: the owner's 2026-10-17 German-only ruling and [i18n · 切到德语就全是德语：地址与标题](https://github.com/AssassinFlash/de-linker/issues/254), including its product-address and historical-category comments. The implementation is rehearsed on snapshot instance `c254`; Claude owns review, merge and deployment.

## Contract

- Descriptive German paths use German words; manufacturer names, model codes, figures and technical abbreviations remain intact. ASCII transliteration uses ae/oe/ue/ss.
- Every previous address reaches its final German address with one 301. Endpoint values and query strings, including reset tokens and inquiry keys, survive unchanged.
- All public canonical German pages and functional account endpoints have independent German document titles. Redirect aliases and arbitrary 404 paths are not separate pages. Pagination includes its page number; inquiry detail includes its inquiry number.
- Links in content, templates, menus, customer emails, the sitemap, canonical and hreflang use the new addresses. English addresses and copy remain unchanged. The owner subsequently requested coherent inquiry and product-detail-page designs in this session; these visual changes are explicit exceptions recorded in the change ledger. All other English page types retain the zero-pixel gate.
- Existing German objects keep their migrated addresses on later source saves. New products obtain a slug from German copy. `SameSlug` still permits identical proper names across languages.

## Native mechanisms

Polylang owns post/term language pairs and permalinks; WordPress `wp_update_post` and `wp_update_term` own stored slugs. WooCommerce's stable query keys and `woocommerce_get_endpoint_url` own endpoint dispatch and generated links. The i18n plugin's existing segment layer supplies German aliases without changing global English endpoint options.

WordPress 7.1.3's `wp_check_for_changed_slugs` and `wp_old_slug_redirect` expressly exclude hierarchical post types. They also do not cover taxonomy paths, translated bases or Woo endpoints. Product history uses the native old-slug metadata with a language check; the existing redirect entry point supplies explicit German compatibility routes for the uncovered cases. No second redirect system or paid extension is introduced. If core first finds English history, the native old-slug metadata lookup is narrowed to German before choosing a destination.

Woo aliases emit the configured endpoint variable, which Woo then maps to its stable internal key; its endpoint predicates therefore remain active. Address children use `woocommerce_edit_address_slugs`. Pagination copies both the companion rules and Polylang's `(de)/` rules, preserving native capture positions. Polylang intentionally omits hreflang on paginated archives (`src/frontend/frontend-filters-links.php::wp_head`); this behavior is retained. Pagination switches preserve their page number. WordPress uses the German request-local `pagination_base` when generating subsequent links, avoiding nested page segments. The header reapplies the native language URL filter after appending request context. Logout remains a native action: its compatibility response is 301 to the German action, followed by Woo's normal redirect. It is excluded from document-title uniqueness.

Acceptance reproduced a database/cache disagreement: the database contained the new rules while the autoloaded option cache retained the old rules. Native `update_option` then returned without repairing that stale cache. Apply and rollback invalidate this site's `alloptions` and `rewrite_rules` option-cache keys before native rewrite regeneration; verify checks the written German endpoint rules. No Redis database or other instance is flushed.

LiveCanvas content stays in repository exports, installed by `present`. The migration never writes `lc_partial` or `lc_dynamic_template`; language pairing and per-page template assignment survive renames. German template exports update their URLs. No PHP layout or additional CSS is introduced.

## Migration interface

`wp linker-i18n german-urls` defaults to preview. `--dry-run` reports pending changes, completed rows, conflicts and backup state. `--apply` checks all targets before writing and retains original values. `--verify` reports remaining defects and exits nonzero on failure. `--rollback --dry-run` previews restoration; `--rollback --apply` restores the saved values.

Objects resolve through their English source and Polylang pair, not fixture IDs. An existing value must equal the recorded old or desired new value. A separate seven-object title manifest records the reviewed post titles, SEO titles and category names, so the first apply also rejects independently edited copy before writing. A reviewed new post title with its reviewed old SEO value is resumed to the final SEO value. A missing pair or occupied target fails before writes. A repeated apply must perform no data changes and must preserve the first backup. The original import entry point must not undo this migration. Once active, the historical bootstrap script's plan/apply entry returns zero changes before configuring or re-importing its payload; the normal import API and automatic source synchronization remain available. URL references are processed as whole references so external hosts and opaque query values stay intact. Existing independent German SEO titles remain native unless the reviewed title itself changes.

## Agreed tests and evidence

The public test seams confirmed by the owner are HTTP responses, the WP-CLI interface, and captured local mail. Work proceeds one failing behavior and its implementation at a time. Integration fixtures preserve and restore their data, options and scheduled tasks; the suite is run twice. Standard stack tests may create their own isolated temporary instances.

Acceptance records include the live sitemap/crawl union, every old/new route and its first/final response, independent title review, email links, preview/apply/repeat/rollback results, and the actual snapshot time. Computer Use covers EN/DE at 1440 and 390, including account states. English comparisons use the same browser, dimensions and fully loaded fonts/images, with animations disabled. Captures with missing lazy images are rejected. The unmasked changed-pixel count must be zero outside the owner-requested inquiry and product-detail-page design corrections. German title changes and both design corrections are recorded in the change ledger.

## Deployment handoff

Claude first backs up and deploys the reviewed files, runs the migration dry run and reviews conflicts, applies it, then runs `present`, rebuilds native WindPress cache and rewrite rules, and reads back presentation, routes, titles, sitemap and mail URLs. Rollback restores migration values and presentation backup before the preceding file release, then refreshes rewrites/cache and verifies both languages. Exact commands and evidence are supplied in the PR.

## Additional owner visual correction, 2026-10-18

The owner rejected the compatibility-product area while inspecting the actual screenshots: dense long names, tiny images, prominent SKU lines and wrapping pill labels were visually poor. Rework this area in WindPress for both languages, retaining native product facts/links and keyboard access. Record it alongside the inquiry redesign as an explicit exception to EN screenshot parity; unaffected page types still require zero changed pixels. The compatibility-product area is the primary design correction. The owner subsequently explicitly accepted the related gallery/information proportions, title hierarchy, auxiliary controls and document density optimizations and asked to see them again. The final product-page correction includes those refinements and the solid mobile action bar. Native data and behavior remain unchanged; presentation stays in WindPress and is delivered in both languages.
