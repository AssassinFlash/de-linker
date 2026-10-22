# Product archive empty state — copy and LC-native design review

Status: **copy/design PASS for the final wording and native seams below; implementation and visual acceptance pending.** This is a review of the parent's draft, not a new product, sourcing or availability claim. No product source, template content, translation catalog or instance was changed by this reviewer. LC assignment implementation belongs to the separate implementer.

## Draft → challenge → final

| Surface | Parent draft | Review and decision | Final |
| --- | --- | --- | --- |
| EN, empty loop with no requested filters/search | No products are listed here. | Retain. Describes the page's listing only; does not claim stock, supplier capability or a future addition. The surrounding archive heading supplies the scope of “here”. | **No products are listed here.** |
| DE, same state | Hier sind derzeit keine Produkte aufgeführt. | Remove the unnecessary temporal qualifier “derzeit”. The page already states the present result. “Aufgeführt” is neutral German for a listing and avoids treating this as an availability notice. | **Hier sind keine Produkte aufgeführt.** |
| EN/DE, first action | All products / Alle Produkte | Retain the existing UI vocabulary. This names the destination and supplies an escape from an empty brand/category; it does not promise that all products are in stock. | **All products / Alle Produkte** |
| EN/DE, second action | Contact Linker / Linker kontaktieren | Retain the existing CTA and formal German site vocabulary. It is a contact invitation, not customer homework or a sourcing guarantee. It does not add a reply-time promise. | **Contact Linker / Linker kontaktieren** |

The rejected mutations are “No products available” / “Keine Produkte verfügbar” (unsupported stock/availability conclusion), “No products yet” / “Noch keine Produkte” (suggests a future addition), and an instruction to clear a filter when none was requested. Do not add “coming soon”, replenishment dates, sourcing assurances, apologies, testimonials or a new service promise.

An empty **filtered/searched** result retains the existing sentence and translation without rewriting:

- EN: `No product matches these filters. Clear one to see more.`
- DE: `Kein Produkt passt zu dieser Filterauswahl. Setzen Sie einen Filter zurück, um mehr zu sehen.`

This narrow review does not recertify that existing text as a new sourcing claim. Its prerequisite is that the user's request actually contains the existing filtering/search selection. `ProductFilters::requested()` reads the recognized facets and `q`; use that parsed authority, not arbitrary nonempty `$_GET`, the archive's inherent term, or its sort value. A zero-result DEHN root with no requested facet/search receives the new neutral sentence; a Chint `q` with no matches retains the existing filtered sentence. Unknown/404 and pagination behavior remain separate.

## Standards and fact boundary

Applied `linker-copywriting/SKILL.md` Hard Stops and procedure, with its encyclopedia, anti-pattern and positive-example references, and the repository's current `AGENTS.md` and existing PO terms as the controlling vocabulary. The skill's older commercial nouns or policies do not override the repository's current Product / Produkt terminology or business model. The one added dimension is **empty-list state and a useful onward destination**; this is status/navigation copy and does not need a manufactured marketing benefit.

Pre-delivery:

- [x] Non-PDP encyclopedia/reference lane read; the words remain existing products/contact UI vocabulary.
- [x] Hard Stops 1–9 hold: no borrowed credibility, technical proof inventory, defensive company claim, reassurance intensifier, logistics/time promise, helpdesk initiation or repair-shop selling.
- [x] Actor: no new second-person instruction in the new sentence; contact remains a CTA invitation.
- [x] Future: no invented customer trajectory, future product addition, supply or availability assumption.
- [x] Weight: the sentence describes this result area, not the whole company or a capability.
- [x] Duration: no continuing-service or future-time claim.
- [x] No slogan formula, banned brand, fabricated quote or unsupported technical noun.
- [x] EN reviewed as source; DE assessed independently for natural wording, using current German CTA terms.

Evidence for the empty-list statement is the actual resolved archive loop, not a stock number or a raw shared term count. A native term with zero results remains a valid page. Even when a filter produces zero results, that does not prove Linker cannot supply the product; the contact destination likewise does not promise that it can. The existing contact invitation below the grid is still present: inspect the final LC surface for redundant adjacent contact actions before calling its visual hierarchy accepted; do not solve that by silently rewriting its existing text.

## Installed LC supports the exact native condition

Read installed LiveCanvas at `/Users/chesterjohn/de-linker-local/sharedarchives/wordpress/wp-content/plugins/livecanvas/`. `modules/shortcodes.php:887–940` registers `lc_if`: it trims the condition string, recognizes a leading `!`, strips that prefix, verifies the remaining function exists, calls it, then negates the result. It renders the chosen branch through its own nested-shortcode processor.

Therefore this syntax is supported by the actual installed implementation:

```text
[lc_if condition="!have_posts"]
    …existing LC HTML for the two navigation actions…
[/lc_if]
```

The equivalent native branch form is `[lc_if condition="have_posts"][lc_else]…[/lc_if]`, but there is no reason to substitute it when the installed negation is explicit. Existing repository cart/PDP templates already use `lc_if` with registered functions; the native `!` support above supplies the missing negation evidence. No new global PHP condition, CSS-only hiding, fake product or page renderer is required.

Place the condition beside `[linker_products_empty]` **before** the grid or any loop-consuming shortcode, and check the real main archive query. WordPress `WP_Query::have_posts()` tests remaining loop entries; at an exhausted nonempty loop it can fire `loop_end` and rewind. It is not a context-free “zero total products” predicate that can safely be moved after the loop. The current export places the empty message before the product grid, and LC `lc_render_dynamic_template()` reads the template's content without replacing the main query with a template-post loop. Preserve this placement and verify nonempty archives never show the empty CTAs.

The empty-text selection may use the existing PHP shortcode's parsed requested filters to choose the correct translated data sentence. Do not add CTA HTML, layout or visual choices to that PHP method. The condition, placement, action markup and responsive layout belong to LC; appearance belongs to WindPress.

## Native destinations already exist

- **All products:** `[lc_wc_get_page_url page='shop']`. Installed `modules/templating-shortcodes-woocommerce.php:607–614` resolves `get_permalink( wc_get_page_id( 'shop' ) )`; this repository already uses the tag in product/compare templates. `I18n\Plugin` registers `woocommerce_get_shop_page_id`, and `Woo\Storefront::page_id()` selects the current language's paired Woo page. Use the native result and verify the DE destination; do not hard-code an English path, prefix `/de/`, or retain the empty archive's filter query in the destination. The native LC callback can fall back to `#` if a page is missing, so actual configured-page readback is required before acceptance.
- **Contact Linker:** reuse `[linker_contact_link class='…']` with classes authored in the LC template. Its default existing vocabulary is the reviewed CTA; `Shortcodes::contact_page_url()` resolves the current-language contact page through `PageUrls`, not a guessed path. The new generic archive action need not fabricate a model or project context. The existing product-contact block already owns its established archive context.

Do not invent a `param` argument for `[lc_wp_func]` to call `wc_get_page_permalink('shop')`: this installation's `lc_wp_func` only invokes a no-argument callable. The actual Woo-specific tag above is both available and already used. No additional PHP URL helper is needed for these two actions.

## Required implementation checks

The future implementation must retain the existing English/German product-archive template pair and native assignment mechanism. Verify at least an unfiltered genuinely empty shared root, a previously populated archive filtered to empty, and a nonempty control in both languages. Confirm the neutral versus existing filtered sentence, only the intended empty-state actions, native localized shop/contact destinations, working filter/search/Clear escape and no empty CTA on the nonempty control. Native LC rendering must remain active independently of a first product.

Computer Use at 1440/390 must read the state text, CTA hit targets, keyboard focus, usable wrapping, whitespace and onward navigation. No browser or instance was operated for this review, and no implementation, translation-build, deployment or visual PASS is claimed.

Inspected native file identities: `modules/shortcodes.php` SHA-256 `26fd9665a4e7ee39d649dcf1402594694ac030a5a417dfd7543fbc5899279650`; `modules/templating-shortcodes-woocommerce.php` `2027b57fccbf9226e801eb68fd93f62f75d26f89b2158076034ce56c8e5d79e3`; `modules/templating.php` `a9a1b4968f048c3741eb431a9c45fb1d9f78f3eae5944105bd23dd27cddd5fcd`.
