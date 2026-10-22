# Shared archives and empty states — final source Standards review

**PASS for the current complete source candidate. No remaining actionable Standards blocker was established in this diff.** This conclusion binds the 22 files below against `d27f3dc35126cd037db8f98f53da137cacbc52df`, including the four new, untracked PHP/test files. It does not reuse an earlier three- or six-file freeze as the final candidate, and does not constitute native runtime, visual parity, CI, deployment or production acceptance.

Reviewed in `/Users/chesterjohn/.codex/worktrees/shared-archive-routes/de-linker`. Scope: seven i18n source/test files; six LC metadata producer/backup/test files; empty-message producer and test; EN/DE archive exports, shared shop export, WindPress products styles, PO/POT/MO. Complete aggregate of all 22 files: `00e7e6ee28ed9730b11cf1df96b7dd3490b8a7d028fc9d6a6209e9909ab0aa54`, calculated as SHA-256 of sorted `file-SHA256 + two spaces + relative path + LF` lines.

## Native routing and language authority

- `Plugin::register()` declares `pll_filtered_taxonomies` before Polylang's cached taxonomy declaration. The whitelist is exactly `product_brand`, `pa_brand`, `pa_series`; it preserves native/other-plugin entries and does not place these proper-name terms in the translated-taxonomy list. No copied terms, manual route family, OR taxonomy merge or counterfeit product count was added.
- Woo's `woocommerce_product_query` adapter changes only empty/null post type on the main approved shared taxonomy query to `product`. Explicit product, post, any or list declarations and secondary/other taxonomy queries are unchanged. This keeps Polylang's native product count/query path meaningful without replacing it.
- The empty-root visibility adapter changes only an existing true hide decision for a positive native term ID, untranslatable whitelisted public/queryable product taxonomy, matching native product/slug count arguments and configured target language. False decisions, search, feeds, paged requests, missing terms/404s, other taxonomies/types and unknown languages pass through. Polylang continues constructing switcher/hreflang URLs; this is not a custom URL generator.
- The rewrite fingerprint includes both the existing German declaration and the shared-taxonomy whitelist. A changed declaration requests the existing soft flush; warm matching values are inert. Permanent tests now use actual JSON serialization and constrain the complete declaration, so removing the shared field is observable rather than hidden by a constant mocked hash. The earlier cache-test gap is closed.

## LC assignment ownership and failure recovery

- `ArchiveAssignments` discovers the currently registered public/queryable product taxonomies and writes only LC's native generic assignment metadata onto the existing EN archive anchor and its existing DE twin. No PHP template renderer, `template_include` takeover, new DE shop assignment, speculative language slug or duplicate LC post is introduced.
- Conflict detection follows native **metadata existence**, not truthiness. Another published same-language or unknown-language owner is a preflight refusal even if its stored value is `''` or `'0'`. Other-language owners and per-term keys are preserved. Preflight occurs before the template batch and again immediately before assignment writes; the primed scan avoids an N-taxonomy query-join graph.
- Exact value lists are captured before writes, including absence versus empty rows and multiple values. Present's outer backup is read back before settings/templates/assignments change. Assignment writes require persisted readback; local recovery restores only the saved ID/key set, adds `wp_slash` for native metadata writes, preserves literal backslashes/quotes, and compares the complete resulting lists.
- Both the write and local-recovery catches now cover `Throwable`. Successful local restoration rethrows the same original Exception/Error object. A failed restoration reports both causes with the original as previous; the outer present backup is retained. Operator rollback reads the saved keys rather than today's registry and cannot consume the backup after a thrown restoration or failed readback. Prior plain-Exception/Error bypass is closed in the present bytes.
- Permanent tests execute the real `Templates`/`PresentCommand` consumers, including same-language zero-valued conflicts, unknown-language conflict, partial writes, wrong success readback, refusal, multi-row/slash/absence restoration, Exception/Error after persistence, restoration failure and retained outer backup. The unchanged broad template tests explicitly default to no discovered product taxonomies rather than accidentally testing the new assignment behavior through unconstrained mocks.

The backup/local-recovery code is an operator publishing mechanism, not a database transaction around all presentation work. A later unrelated failure still requires the retained official rollback; source review does not convert a partially completed command into an atomic successful deployment. No new concurrent writer is introduced. The parent separately reports actual native WordPress hook-fault and official present/rollback proof; those runs are not represented as this reviewer's executions.

## Empty composition, language and populated controls

- All three LC exports retain the original populated `wb-strip`, filter rail, grid/family producer, pagination host and contextual contact fragment. The positive `have_posts` branch keeps the count/sort untouched. Its empty `lc_else` branch retains chips/Clear; only the meaningless zero count and empty ordering control disappear. The sibling `!have_posts` block adds the reviewed empty card before the grid. There is no nested same-name conditional or hidden form/search escape.
- PHP changes only the data sentence for an empty native loop with no explicit search/facets. `requested()` empty yields EN “No products are listed here.” / DE “Hier sind keine Produkte aufgeführt.” Search/facet emptiness preserves the existing filtered guidance. Nonempty output remains empty. The PHP fragment adds no action, inline CSS, layout or model/data promise.
- Archive EN/DE actions use the existing “All products” / “Alle Produkte” wording. The shop's single structural export uses the installed native `lc_label` with the `linker-commerce` domain for both its action text and `Product filters` aria label; LC's native Woo page URL tag supplies href. Installed callback/parser evidence is in `shop-empty-native-options.md`; no custom UI-word PHP method or new German shop twin was necessary. The fixed current catalog labels contain no markup/quote characters; the existing LC tag does not context-escape arbitrary dynamic translation input and is not used here as a user-input channel.
- New CSS selectors are limited to the existing products surface plus new empty-state/filter/action classes. Populated card/grid/control selectors are not changed. Empty chips gain the established 44px target; hover/focus and reduced-motion states are explicit. Layout remains in LC and WindPress, with no snippet or second CSS pipeline.

Independent PO comparison, including context/plurals, found **897→898 messages: one addition, zero removals, zero changed existing translations, zero duplicate keys**. POT includes the complete PO key set. Independent compiled-MO comparison found only the same new sentence, no removed or changed existing translations. Apparent line/reference movement and the relocated “Remove %s…” entry are not semantic copy deletions. The final new DE sentence is exactly the approved neutral wording, without “yet”, availability claims or an implied future listing.

The added-line/source audit established no reintroduced legacy implementation identifier/channel in this scope. Existing semantic/design class names do not supply a new PHP implementation. There is no model, account approval, inquiry, mail routing, privacy-body or product-data change. Fowler smells did not justify an additional refactor: the native assignment writer is a cohesive metadata/restore responsibility and remains separate from LC composition.

## Verification and remaining boundaries

This pass re-read the current complete diff/new files, checked the current hashes and compared PO/POT/MO semantics. The earlier isolated installed LC/WordPress shortcode probe confirms parser/callback use for body and aria labels; its gettext dictionary was controlled and its actual MO was independently read. No instance/bootstrap, browser, dependency installation, product edit or production operation was performed here.

The parent reports a successful full `just check`, commerce 1361 tests / 6125 assertions with 161 existing skips, and i18n 274 tests / 623 assertions. Those are parent-executed gates, not substitute executions claimed by this review. Existing native cache lifecycle, LC write-hook failure/rollback and original browser frames retain their own source/version attribution; a newer shop/toolbar presentation must be accepted under its own published bytes and compiled CSS.

**SAJ pagination remains outside this candidate's claimed repair.** Native product IDs or a 200 response do not establish family pagination presentation, canonical/hreflang or navigation correctness. The independent investigation is still open; this source PASS must not be read as resolving it or closing the full-site visual goal. Final EN/DE ×1440/390 CUA, relevant native final readback, CI, production backup/cutover and deployed readback remain parent-owned gates.

## Exact reviewed files

| File | SHA-256 |
|---|---|
| `commerce/content/livecanvas/archive_product.html` | `a0fb0b3f993c93edf67bd06f6de5ed098e301d12a8d6ca4099fc65caa3174652` |
| `commerce/content/livecanvas/de/archive_product.html` | `80c1ec1867f03c97923fb60c2ae8653048cf144e21b1e070e5dc8ec46413111d` |
| `commerce/content/livecanvas/shop_page.html` | `9449e57fbd72d2c2afabeecfb232ddbc90d594ee9452b9726fe01d328acbecfe` |
| `commerce/content/windpress/products.css` | `f3958e98c10665d654b76033e98452ccc00b9389224c950bc0835526b491ad26` |
| `commerce/includes/Cli/PresentCommand.php` | `68d95821f2b15f34317bdf46b2d65c68bd98ec6813a406cdcc6d83cd6b9b89a7` |
| `commerce/includes/Presentation/ArchiveAssignments.php` | `7c6e982e781efb469bdec33089c846774316e94e4c8019e86928f0dfb7fd6b14` |
| `commerce/includes/Presentation/ProductShortcodes.php` | `e398ee95652c3be9b09d52a4179b619407f7ceab3dbdd9031e84fa916bff9556` |
| `commerce/includes/Presentation/Templates.php` | `e61ef26a53124651e9e6cf48792c27b327572c24843e491ad7b4695e7e7fab56` |
| `commerce/languages/linker-commerce-de_DE_formal.mo` | `2fc43474afab74ba6c2afc8bffe5dfd3e014c762011eda6f029a790caaf41d00` |
| `commerce/languages/linker-commerce-de_DE_formal.po` | `abfedaed342bb86ee5fe5a21b3aed5bf2633c34146d4389705cea1f8144379ee` |
| `commerce/languages/linker-commerce.pot` | `7d70b3f487d8fa9b300e86839bcc547b0a45e2eb20532a6da5ffb6df7685f509` |
| `commerce/tests/php/Unit/Cli/PresentCommandTest.php` | `634c00cce8d73f1a207da87dbde5d5744d8311a44fe90bc7c16edc26021200c2` |
| `commerce/tests/php/Unit/Presentation/ArchiveAssignmentsTest.php` | `5e81e7dd67a98410892d8d3ec7dc1550a24ff4be654c610427d4f12d04e763cd` |
| `commerce/tests/php/Unit/Presentation/EmptyProductsTest.php` | `10573a60742253c7afee3b8380d0e453ece6dac7ddcca8674295cb71b227f6a0` |
| `commerce/tests/php/Unit/Presentation/TemplatesTest.php` | `484502cce1ac71cc89948e6fbaf2e483eac6ab747a4bc50ec1fe3c02c4084b78` |
| `i18n/includes/Plugin.php` | `e8e1635829f43bb1e58f510fad83c3d74c489344a30564a82de87108e910fde0` |
| `i18n/includes/TranslatedTypes.php` | `ebf4f82fa644cd6b30f5a9dc3954ce6c84b5b2527fb14f65fdc8aa8eb6383a6c` |
| `i18n/includes/UrlSegments.php` | `bf12d0cb7764600c43014944e214272f1ed71368489d87eb0571e9ff06c18ed8` |
| `i18n/tests/php/Unit/PluginTest.php` | `a6e8c0fed90eea7dd2f8100ae6f5f56823b8cfe4c4b42224b81e2dbd19ef3d8b` |
| `i18n/tests/php/Unit/SeoTest.php` | `6b008a384269a05b07576f210c477aaedbeee010648293fd7c831417e548cf41` |
| `i18n/tests/php/Unit/SharedArchiveLinksTest.php` | `69bd2515663ac6ad9de3960c5dc0f8806f78f81b7db53185ff7772612c18f11d` |
| `i18n/tests/php/Unit/UrlSegmentsTest.php` | `8fffddb0fa7224857820576b1d1c8460960398983b7e1c2b060c804d9c96e710` |

Table abbreviations: `commerce/` means `plugins/linker-commerce/`; `i18n/` means `plugins/linker-i18n/`. The aggregate uses the full repository-relative names, not these display abbreviations.
