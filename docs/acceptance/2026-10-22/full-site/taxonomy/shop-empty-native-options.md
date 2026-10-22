# Shop empty state: installed native options

**Decision: use the installed LiveCanvas `lc_label` tag.** The initial assumption that LC lacks a gettext label tag is contradicted by the installed plugin. Neither a new ProductShortcodes UI-word method nor a German shop-template twin is necessary for these two existing labels. This is a read-only capability/design finding, not an implemented shop fix or native/browser acceptance.

## Current source and data boundary

At the start of this lookup, `plugins/linker-commerce/content/livecanvas/shop_page.html` carried the unconditioned result strip, `[linker_products_empty]` without the new empty card/action, and literal English `aria-label="Product filters"`. The original shop export retained in the native baseline has SHA-256 `4d9854644ed3c2208dde57f7fe6ad66fa54bf9933fe6d95eb27abdd092a74b5b`.

The retained private `shared-LC-state-before.json` was read only for assignment metadata: 31 LC records; the only `is_shop_page` assignment is published EN template 6961. No DE shop assignment is present. The private snapshot SHA-256 is `b6681d4a88e44c028c191afd411dd3b275dd41b5936019522fb0ea5ec6a85548`; its stored HTML and other private content are not reproduced here.

`Presentation/Templates.php::FILES` maps `is_shop_page` to `shop_page`; `DE_FILES` has no shop entry. `I18n/DynamicTemplates.php::template()` supplies the EN structural template only when the current German Woo page has no template. Its `english_template()` temporarily changes Polylang's current language only around the template-ID lookup and immediately restores it. The code explicitly preserves locale and string translations, so retrieving an EN template does not imply that its data shortcodes or gettext labels must render English.

## Installed native capability, checked at source

Installed plugin root: `/Users/chesterjohn/de-linker-local/sharedarchives/wordpress/wp-content/plugins/livecanvas/`.

| Native option | Actual implementation and suitability |
|---|---|
| `lc_label` | `modules/shortcodes.php:818–826`, registered by the plugin's normal `modules/shortcodes.php` include at `livecanvas-plugin-index.php:43`. Accepts `text` and `domain` attributes and returns `__( $attributes['text'], $attributes['domain'] )`. It is the direct LC-native mechanism for the existing commerce phrases. |
| `lc_wc_label` | `modules/templating-shortcodes-woocommerce.php:486–493`; accepts text but fixes domain to `woocommerce`. It does not select the existing `linker-commerce` translations and is therefore less appropriate here. |
| `lc_wc_get_page_url` | Same Woo module, `607–614`; `page='shop'` uses `get_permalink( wc_get_page_id(...) )`. Keep this native href, with the site's existing localized Woo page-ID adapter. No new URL producer or hard-coded language path is needed. Its native missing-page fallback remains `#`; real configured href readback is still required. |
| `lc_wp_func` | `modules/templating-shortcodes.php:7–23`; calls the named function with **no arguments**. It cannot directly call `__('All products', 'linker-commerce')`. There is no reason to add a global no-argument wrapper now that `lc_label` exists. |
| `lc_function` | `modules/shortcodes.php:829–858`; likewise invokes a no-argument callable and captures its output/return. It offers no advantage over `lc_label`. |
| `lc_if` / `lc_else` | `modules/shortcodes.php:884–947`; supports negation and one optional condition parameter, branches by truthiness, then processes nested shortcodes. Use the established `have_posts`/`!have_posts` structure for result strip versus empty card. It is a condition mechanism rather than a gettext output mechanism. |
| Existing product data shortcodes | `ProductShortcodes::products_empty()` already returns the reviewed localized neutral/filtered sentence. `products_head()` and `products_filters()` already emit localized “All products” as part of larger semantic navigation fragments, not a standalone word. Reusing those entire fragments inside the CTA or an aria attribute would create incorrect nested markup/duplication. No data helper is needed for the label itself. |
| German shop twin | An available architecture for a genuinely different localized structure, but unnecessary for two existing gettext words and shared markup. It would add a new assignment/pair/export/present/rollback surface without solving a missing native capability. Keep the current structural fallback for this narrow repair. |

LiveCanvas's `lct_do_shortcode()` at `livecanvas-plugin-index.php:1867–1895` intentionally skips WordPress's HTML-tag preprocessor and runs the registered shortcode parser over the content; the adjacent comment specifically names shortcodes in attributes as the reason. This supplies an actual installed processing path for the static aria label, rather than a guessed API.

## Recommended LC composition

Use the existing archive empty card and empty-filter strip pattern in the shop export, keeping all composition in LC and all style in WindPress. Preserve the entire current result strip for `have_posts`, retain chips/Clear in the `lc_else` branch, and put the existing localized empty data plus one native shop action before the product grid when `!have_posts`. Keep the existing contextual contact data afterward.

The two language-dependent fragments in this shared structural export can be written as:

```html
<aside aria-label="[lc_label text='Product filters' domain='linker-commerce']">
  …existing filter data…
</aside>

<a href="[lc_wc_get_page_url page='shop']">
  [lc_label text='All products' domain='linker-commerce']
</a>
```

These are examples of the label/href seam, not replacement layout. Retain the real wrapper attributes/classes and the previously reviewed action style in the actual export. Use the existing sibling `lc_if` pattern; avoid inventing nested same-name conditional syntax.

The plugin's `lc_label` returns gettext output without context-specific escaping. For this narrow use, both messages are fixed, reviewed repository catalog entries with no markup or quotation marks; the attribute must retain double quotes outside and single quotes inside its shortcode attributes. Do not turn the tag into a way to render user-provided text/translation keys, or add an arbitrary runtime label registry. If those fixed translations later acquire HTML/quotes, review the attribute context explicitly. This observation does not justify a new custom translation channel for the present words.

## Independent isolated verification

Read the actual current commerce MO through a GNUTranslations reader: `All products → Alle Produkte`, `Product filters → Produktfilter`. MO SHA-256: `2fc43474afab74ba6c2afc8bffe5dfd3e014c762011eda6f029a790caaf41d00`. Both msgids also exist in the repository PO. No new customer-facing wording or new translation is proposed.

An external PHP probe loaded the installed WordPress shortcode parser, the installed LC shortcode-registration file, and the exact installed `lct_do_shortcode` function. A controlled gettext dictionary provided EN/DE values while recording the requested domains; this is deliberately not a WordPress request or native locale/catalog-loading test. Both the anchor body and aria attribute matched the expected EN/DE output exactly, with no raw `lc_label` remaining and all four calls using domain `linker-commerce`.

- Probe: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/shop-empty-native-label-probe.php`, SHA-256 `f66ffbbafc459de32f882510df219603842aef86e09ea13ebc437cfe5c58e603`.
- Output: corresponding `.json`, SHA-256 `b9c3d706738983251d793df5912828c958d5b886f5e5d6291143270b3117d569`.
- No `wp-load`, database, HTTP, instance bootstrap, product/source modification or production action occurred. An initial temporary harness quoting parse error was corrected before this successful callback/parser probe; it is not a product failure.

Native file identities: `modules/shortcodes.php` `26fd9665a4e7ee39d649dcf1402594694ac030a5a417dfd7543fbc5899279650`; `modules/templating-shortcodes.php` `bf739f0fb00d5655eeacd50567365c918e4ac048d7a130bcaebd9b6cb434290b`; `modules/templating-shortcodes-woocommerce.php` `2027b57fccbf9226e801eb68fd93f62f75d26f89b2158076034ce56c8e5d79e3`; `livecanvas-plugin-index.php` `9378b84f3754e448c8055a14468bdb5e79a8363d8b6f8a6d43f6595105a8c265`.

## Implementation acceptance still required

After the native capability was reported, the parent independently applied the narrow LC change during this review. The observed export SHA-256 is `9449e57fbd72d2c2afabeecfb232ddbc90d594ee9452b9726fe01d328acbecfe`. Its source diff follows the recommended native label/href/condition seam, retains the original populated strip and contextual contact fragment, and adds no PHP producer or German shop twin. This source observation does not establish the installed/native rendered result.

After the parent implements and publishes the LC export locally, verify EN/DE shop nonempty and search/facet-empty paths through the actual dynamic template. Confirm DE has `Alle Produkte` and `Produktfilter`, no English literal/raw shortcode, the neutral versus filtered empty sentence, zero-result count/sort omitted only when empty, chips/Clear/search retained, and native All-products href clears the empty query and lands in the same language. Confirm the ordinary populated shop remains visually unchanged and no new DE shop record/assignment is created. Official presentation/rollback, WindPress compile and desktop/mobile CUA remain separate gates.
