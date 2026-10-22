# Empty product archive surface — Spec and Standards source review

**Verdict: source/wording PASS, no actionable blocker found in this narrow increment.** Native assignment activation, official `present`/rollback, actual rendered LC state, generated WindPress CSS and Computer Use remain the parent's separate acceptance gates. This does not close the open LC metadata exception finding or certify any local/production page.

The worktree is `/Users/chesterjohn/.codex/worktrees/shared-archive-routes/de-linker`, branch `codex/shared-archive-routes`, HEAD `d27f3dc35126cd037db8f98f53da137cacbc52df`. Review includes both EN/DE `archive_product.html` exports, the complete new `products.css` rules, the `products_empty()` change, untracked `EmptyProductsTest.php`, and the meaningful PO/POT/MO delta. Other contributors' assignment/i18n/ordinary-Genie files are outside this increment. The reviewer changed only this document and ran the four isolated PHP consumer cases; no source, instance, browser, full check, dependency installation or production operation was performed.

## Spec, copy and native authority

The implementation exactly uses the approved EN `No products are listed here.` and DE `Hier sind keine Produkte aufgeführt.`. It omits the draft's redundant temporal qualifier and adds no “yet”, supply promise, future addition, stock or service claim. The scope is the current listing, not the company or physical inventory. The existing filtered/search-empty sentence and German translation remain unchanged.

`products_empty()` first returns no output for a nonempty native loop. With an empty loop, its existing `ProductFilters::requested()` collaborator selects neutral wording only when the parsed request is empty; explicit `q` or recognized facets retain the existing filtered sentence. It does not infer user selections from the archive's inherent term, unrelated GET parameters or sorting. The added PHP branch only changes the data sentence inside the existing semantic fragment; it introduces no link, layout, style or new destination writer.

Both LC exports use the installed native `[lc_if condition="!have_posts"]` **before the product grid and any grid loop**, as established in [empty-state-copy-review.md](empty-state-copy-review.md). The same condition contains the message and the single onward action. Thus an unfiltered empty brand and a populated archive filtered to zero can retain the same existing LC product surface; a nonempty loop does not acquire an empty CTA. Correct native template selection is still a prerequisite and is not proven merely by reading this export.

The sole added primary CTA is the established EN `All products` / DE `Alle Produkte`, with `[lc_wc_get_page_url page='shop']` as its destination. The tag is installed native LC and resolves the native Woo shop page ID/permalink, including the existing language-page filter. There is no guessed path, English-only destination, retained empty-filter query, new PHP URL helper or JavaScript navigation override. A missing native configured page can still yield the LC tag's existing fallback; actual EN/DE href readback is required.

The parent explicitly refined the earlier two-action design to avoid a redundant generic Contact action. This is accepted: the exports leave the existing `[linker_products_contact]` in place after the grid/pagination, preserving its original contact wording and actual archive/search/filter context. No existing contact destination, address or business route is changed. The empty surface adds one browsing action and relies on that existing contact section for the next path; it does not manufacture a second context policy. This refinement supersedes only the earlier proposal for a second generic CTA inside the new box.

The templates retain all original head/actions/filter/search/chips/sort/grid/pagination/contact shortcodes and IDs. The new `role="status"` contains the visible state and native link, with no forced focus, added tab stop, hidden content substitute or live JavaScript rendering path. The real nonempty and filter/Clear consumers must still be exercised after activation.

## Presentation ownership and scope

Composition and action markup live in the two LC exports. The new CSS is confined to `body #linker-products.sf-products` and the new empty-state/action classes. It uses the existing shop ink/teal tokens, readable text, a width bound, one primary action, visible hover/focus treatment and a reduced-motion transition override. It adds no site-wide anchor style, PHP design decision, snippet, second CSS build or fixed-height clipping. LC utilities supply the responsive surface/padding and `min-h-11` action target; official WindPress scanning/compilation must still prove those utilities reach the visitor.

The new action occupies full width on the narrow layout and becomes content-sized at the established `sm` breakpoint. Source intent for a 44px minimum target, keyboard focus and contrast is sensible; actual computed geometry, wrapping, colors, whitespace and the remaining contact section must be checked at EN/DE 1440/390. Source values are not visual acceptance.

## Independent checks

`vendor/bin/phpunit --filter EmptyProductsTest` passed **4 tests / 10 assertions**. It executes the real `ProductShortcodes` method with the real `ProductFilters` parser for native nonempty, unfiltered empty, `q`-empty and facet-empty requests, restores the test's GET state in `finally`, and checks the data fragment does not acquire anchors or inline style. This is actual PHP data-consumer evidence, not native LC/WordPress layout evidence. No full Composer/PHP checks or installs were run by this reviewer.

The reviewer also parsed the current and HEAD PO/POT catalogs and loaded the compiled MO with Python's standard `gettext.GNUTranslations`, including message context and plural-index keys. Results:

- The only non-header meaningful PO change is the new message `No products are listed here.` → `Hier sind keine Produkte aufgeführt.`. Reordered source references and the preexisting removal-label entry are not new copy changes.
- POT adds that single message and removes no message.
- All **850 nonempty context/plural-aware PO translations** match the compiled MO catalog. There are no mismatches.
- Comparing current versus HEAD MO catalog values, excluding metadata headers, finds only that same added translation.
- MO readback retains the existing filtered sentence, `All products` → `Alle Produkte`, and `Contact Linker` → `Linker kontaktieren`.

An initial context-free diagnostic reported apparent mismatches for existing contextual terms; those were parser misuse, not catalog defects. The context/plural-aware comparison above is the validated result. `git diff --check` passed. No generated-file rewrite or rebuild was performed for this check.

## Reviewed identities and outstanding acceptance

All paths are relative to `plugins/linker-commerce/`:

| File | SHA-256 |
| --- | --- |
| `content/livecanvas/archive_product.html` | `9708b1e197dd4dd8b0e7cd705fab9dbe5a319a84b6b13eb59059772c4f572ba4` |
| `content/livecanvas/de/archive_product.html` | `f361b51854cae973aa0140213709537453eaaffc97cf51d5d1f35beb5283e5a9` |
| `content/windpress/products.css` | `30fd32016f2cfbf957ca23f7dc74a9e3082b4755d76076ee385ee4fb33c5ffae` |
| `includes/Presentation/ProductShortcodes.php` | `e398ee95652c3be9b09d52a4179b619407f7ceab3dbdd9031e84fa916bff9556` |
| `tests/php/Unit/Presentation/EmptyProductsTest.php` | `10573a60742253c7afee3b8380d0e453ece6dac7ddcca8674295cb71b227f6a0` |
| `languages/linker-commerce-de_DE_formal.po` | `abfedaed342bb86ee5fe5a21b3aed5bf2633c34146d4389705cea1f8144379ee` |
| `languages/linker-commerce-de_DE_formal.mo` | `2fc43474afab74ba6c2afc8bffe5dfd3e014c762011eda6f029a790caaf41d00` |
| `languages/linker-commerce.pot` | `7d70b3f487d8fa9b300e86839bcc547b0a45e2eb20532a6da5ffb6df7685f509` |

The parent still must prove official metadata installation/rollback and native LC selection for valid empty root and filter/search-empty requests, with a nonempty control in both languages. After official CSS compilation and translation loading, inspect the actual state text, single primary action, localized destination, working search/Clear, contact context, keyboard focus/hit targets and 1440/390 visual surfaces. Neither the earlier route HTTP 200 nor this source/catalog PASS closes that requirement.


## Empty toolbar refinement — design accepted, candidate/visual check pending

The parent discovered the new empty card still carried the existing `0–0 / 0` family count and ordering control. The proposed LC-only refinement keeps the complete existing `wb-strip` when `have_posts()` is true, and uses its native `lc_else` branch to retain `[linker_products_chips]` in a separate empty-filter row when false. Chips and their Clear/remove controls must remain available in both result states; only the meaningless empty count and ordering control are omitted. Use sibling conditions, not a nested same-name `lc_if` construct.

The reviewer read installed WooCommerce `wc-template-functions.php::woocommerce_result_count()` and `woocommerce_catalog_ordering()`: both return when the loop is not paginated or `woocommerce_products_will_display()` is false. That is a native precedent for omitting count/order in an empty result; it does not make the LC `have_posts()` condition literally the same predicate or prove a rendered result. The proposed state-specific composition stays in LC and leaves filter/search/request semantics and PHP unchanged. It introduces no new copy.

This addition records a **design PASS only** before the parent changes the two exports. The existing hash table above identifies the earlier empty-card candidate; it must not be used as the identity of a later toolbar version. Final source hashes, actual no-filter/filter/search-empty/nonempty consumers, visible Clear escape and EN/DE desktop/mobile captures remain with the parent.


### Toolbar candidate source readback

The parent has now supplied the two LC exports and narrow chip CSS; the reviewer read their complete delta and confirms the proposed branch is implemented. Source-only verdict for this refinement: **PASS**. The `have_posts` branch preserves the original `wb-strip` contents unchanged, including its chips/count/sort; `lc_else` contains exactly one chips fragment in a dedicated `.sf-empty-filters` row. The empty-card condition is a separate sibling. Filter chips/Clear remain available and the count/order shortcodes are omitted only in the empty branch. `empty:mb-0` avoids adding blank margin when the chips fragment itself is empty.

The new CSS targets only `.sf-empty-filters :is(.wbchip, .wbclear)` under the existing product root, giving those empty-state controls inline-flex alignment, 44px minimum height and padding. It does not change nonempty toolbar styles, filtering state, labels, links or PHP. Native/CUA proof of computed chip size, Clear recovery and unchanged nonempty layout remains with the parent after official compilation; the earlier first-card native install/rollback evidence is not automatically evidence for these later bytes.

Final refinement SHA-256: EN export `a0fb0b3f993c93edf67bd06f6de5ed098e301d12a8d6ca4099fc65caa3174652`; DE export `80c1ec1867f03c97923fb60c2ae8653048cf144e21b1e070e5dc8ec46413111d`; `products.css` `f3958e98c10665d654b76033e98452ccc00b9389224c950bc0835526b491ad26`. These supersede only the three earlier table entries for the toolbar refinement. No instance, browser or e2e was operated by this reviewer.
