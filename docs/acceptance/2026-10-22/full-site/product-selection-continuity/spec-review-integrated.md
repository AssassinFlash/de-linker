# Integrated family pagination and Contact selection — final Spec review

**Verdict: PASS within the frozen 15-product / 31-artifact source scope.** No remaining Spec blocker was found in candidate **`14cb7f74…`**. The actual archive/Contact URL transport, Contact language migration and selected-search roundtrip defects found in the previous candidate are closed by the new implementation and named native consumers. This is source/consumer acceptance, **not final CUA, production, physical mail or full-site completion**.

## Fixed candidate and independent work

- Worktree `/Users/chesterjohn/.codex/worktrees/shared-archive-routes/de-linker`; base `03cb1a5cba8778fd4abdef72cbfee119e9f6a424`; branch `codex/product-selection-continuity` plus owned new/uncommitted files.
- Independently read the complete tracked diff plus new classes/tests; independently checked every final manifest byte, recomputed both compact sorted-key JSON aggregates, and compared to the previous complete freeze. **15 product sources:** `14cb7f7438fd677721106aa37d0f6ae569e60b469240ec4fb9929feff67395e6`. **Full 31 artifacts:** `d9876d3b8274039718b85d605b46c0d70cccce867e30324f9d58dcd46cf417bc` = 15 products, 14 tests and two generated catalogs. Full per-file map is below and in [source-integrated-files.json](source-integrated-files.json).
- This reviewer wrote only this report and private isolated probe/log files; no product/test/PO edit, dependency installation, build/i18n, browser/instance operation, real mail/model request, production write or deployment. Pure commerce unit tests reuse existing dependencies. Native HTTP/Woo evidence below was executed by the parent; it was read independently, not re-executed here.
- The historical [e3abd22e manifest](source-integrated-files-e3abd22e.json) remains **BLOCKED for that candidate**. Its report snapshot is preserved privately at `/private/tmp/selection-spec-50e75soe/spec-review-integrated-e3abd22e.md`; original reds and the diagnostic frame are retained. The old Contact-only `928f7049…` and earlier 30-file freezes are not recertified as the new 31-file source.

## Historical findings and exact closure

| Previous issue | Final implementation and reviewed consumer |
| --- | --- |
| P2: explicit native term canonical replaced on family page two | `FamilyNavigation::canonical` respects the same truthy `seopress_titles_canonical_term_option()` condition as the installed native custom-term branch. Independently replayed the same actual-class probe red → green. The term branch was proved; no invented Shop custom-canonical claim is made. |
| P2: `1e999` accepted as INF erased the whole selection JSON | The unique archive numeric producer now requires `is_finite`; strict finite comma-decimal control remains. Initial real unit red and subsequent green retained. |
| P2: raw JSON passed to native add_query_arg was damaged by esc_url | `products_contact` encodes the new JSON value before the native query writer. Corrected unit doubles no longer automatically encode it. The new integration fixture parses the actual escaped archive anchor, visits it over native HTTP and reads the real Contact input/summary. The old unavailable CUA frame is historical failure evidence, not passed output. |
| P2: Contact language toggle dropped selection and product intent | `SelectionContext::language_query` normalizes the current public source before carrying context; it resolves native post/term twins, uses installed Polylang language-link handling for untranslated shared terms and applies native URL filters. `LanguageLinks` carries only this verified JSON plus a supported intent, encoded once. Six real HTTP consumers cover both directions for shop, shared SAJ brand and translated inverter category, then visit the target Contact and require the exact selection/source/topic. |
| P2: `SAJ & GoodWe` split into a truncated q and extra query key | New query values in archive base/facet links, language links and Contact selected-result URLs are encoded once; native GET hidden fields remain ordinary text. Independent installed-WP-function red remains at `/private/tmp/selection-spec-50e75soe/native-url-value-red.json`. New HTTP consumers require exact decoded `SAJ & GoodWe "quoted" \ Rückfrage + 100%` through actual escaped links, selected-result return URLs and normalization Location. |

The native shop source has an additional necessary compatibility path: Woo serves it as an archive, so `url_to_postid` can return zero. The implementation falls back to the existing native Woo shop page ID only when its current canonical path matches, then performs the same publication/password/type checks. This does not add a guessed path or weaken public-source validation. German Woo page IDs already pass through the site's native page-ID language filter.

## Final WindPress-only delta — independent Spec and Standards

**Spec SOURCE PASS; independent Standards PASS for this CSS-only increment.** Compared all final 31 file hashes against the archived [7b9f8708 map](source-integrated-files-7b9f8708.json): only `content/windpress/contact-card.css` changed, from `a2720c8f…` to `2357b84c…`. The other 30 files, including all PHP, tests, PO/MO/POT and product CSS, are byte-identical. Earlier functional tests/native evidence remain bound to those unchanged functional bytes; they were not needlessly rerun for a CSS-only delta.

The new selectors stay inside `#contact-form .linker-contact-selection__summary`. The existing native source link keeps its href, link semantics and underline, gains 44px minimum width and height, uses existing `--proto-teal-700`, and has existing darker teal hover and focus-ring tokens. Static sRGB token calculation for `#0a665c` on `#edf1f5` is **6.0305:1**; this is a source-token calculation, not a claim about observed runtime styles. The two-column definition list changes from 1:2 to equal `minmax(0,1fr)` columns, retaining native dt/dd order and existing wrapping. No global element selector, new ARIA state, checkbox/inclusion rule, PHP layout, inline CSS or duplicate style pipeline is introduced. Repo presentation/token ownership is respected; no additional actionable CSS design smell was found.

The final one-line correction after the archived [59c8bf40 map](source-integrated-files-59c8bf40.json) adds `min-width:44px` to the same source anchor. Independently removing that single declaration from the final bytes reproduces the exact prior CSS SHA; all other 30 files remain unchanged. This closes the source-level short-label sizing gap without changing semantics or global scope. Both CSS increment axes remain PASS. Actual generated CSS specificity, measured source-link width/height for SAJ, long German label wrapping, hover/focus and all four viewports remain the parent's CUA gate. A source minimum-size declaration is not an observed 44×44 box; no runtime or visual PASS is claimed here.

## Complete family, navigation and SEO scope

The repair preserves the established full-family grouping/order, 24-family page size, existing card/model-picker anatomy, existing `product-page` contract and LC fragments. A single request-local `FamilyPage` supplies grid/count/pager/normalization/SEO. It never feeds the native sixteen-model slice into family grouping, splits a family or builds a new product grid/router.

Valid native `paged` aliases normalize by the authoritative family count and the validated selection/sort. SAJ's thirteen families therefore have only the root; a true later family slice retains the existing query page. Page-one/invalid/oversized explicit values normalize consistently; unknown/out-of-range native 404s remain native. The native redirect/SEO hooks are scoped to main HTML GET/HEAD shop/public-queryable product taxonomies, excluding admin/AJAX/REST/404/feed/embed/preview/native search and secondary queries. Later-family canonical/noindex/hreflang treatment uses the existing configured native policy; custom-term canonical remains authoritative. No independent language router or product-query visibility policy is added.

The native sort form matches the installed Woo delegated `.woocommerce-ordering select.orderby` consumer. Its normal GET action, search/range forms and hidden inputs retain other recognized selections and reset stale pagination. Facet/chip/pager URLs start from native localized roots and preserve allowed search/sort; Clear returns the native root. Header/footer switching retains the same recognized selection and actual family page through the existing native paired object/path implementation. Required data assembly remains PHP semantic markup; design/CSS remains in the existing WindPress files, with no inline style or copied LC layout.

## Complete Contact, recovery and queue scope

`SelectionContext` accepts only a currently published, unpassworded same-origin product/page/post or a viewable product taxonomy source; native object/path/title are authoritative. Revalidation runs at initial GET and POST. Unknown query keys, browser IDs/titles, credentials, fragments and foreign origins do not acquire authority. Recognized ranges are positive finite values; search retains sanitized text up to the existing full recovery-field bound, with oversized transport explicitly invalid rather than silently truncated. No product match, pricing right, stock fact or account entitlement follows from public navigation context.

The native checkbox's value carries the JSON. Unchecked successful controls omit it entirely from FormData; a separate data-free marker supports an explicit excluded recovery state. No hidden selection JSON remains after exclusion. The customer's message is never prefilled, appended to or overwritten by this context. Invalid included context blocks before proof/admission/write and can be explicitly excluded. A context-free Contact request and other submission doors retain their prior public payload shape.

Included context enters the protected semantic payload/fingerprint and distinct metadata through the existing Sender before receive/queue handling. Selection now uses a native **JSON string** metadata value so backslashes/quotes survive the real Woo store; `stored()` retains legacy-array read compatibility in both actual team/admin readers. Plaintext team output preserves characters rather than HTML-escaping them. Customer receipt stays fixed; native erasure includes the extra metadata key. Existing proof, logical UUID, native Woo session recovery, retry admission and Outbox remain the only submission mechanism. An inclusion change cannot reuse the same semantic completed request, retry does not duplicate queue records, and failure recovery retains original message/request ID plus validated context or the data-free excluded state.

The final native fixture reloads order metadata freshly and requires exact decoded context/search bytes before asserting queue/retry/recovery behavior. Actual native storage evidence here is the parent's configured HPOS store; classic-store compatibility follows the Woo string API and array-reader compatibility tests, **not an unperformed second native-store run**. No real SMTP delivery, extra mail destination or customer notification promise is introduced.

## Copy and preservation

English-first functional labels and independently written formal German retain the approved `Product selection / Produktauswahl`, explicit include/exclude choice and load-failure explanation. Earlier copy critiques are reflected: failed loading does not claim a product was withdrawn, and “will not be sent” includes the native POST rather than merely team metadata. New controls make no stock, price, saved-state or approval claim. Existing marketing/privacy/customer-message prose, product facts/SKUs/models and model/mail routes remain unchanged.

The generated catalog comparison against the base found nine approved label additions, no removed translations and the observed existing German Reset control corrected to `Zurücksetzen`. The final MO is byte-identical to the preceding reviewed MO; the final PO/POT differences are generated references/header after source repairs, not another German copy rewrite.

## Independent and parent-native verification

- **Independent final functional related pure unit consumers on unchanged 7b9 PHP/tests: 112 tests / 501 assertions PASS**, command PHP 8.3 with existing commerce PHPUnit config and `--testsuite unit --filter 'Contact|FamilyPageTest|FamilyNavigationTest|ProductShortcodesTest|ProductFiltersTest|FormRecoveryTest'`. Exact output: `/private/tmp/selection-spec-50e75soe/complete-related-7b9f-unit.xml`. No real WordPress instance used by this reviewer.
- Prior independent e3 suite was 111/497 PASS but did not prove native URL transport; that limitation and the original finite-overflow red are retained. The new native writer test boundary fixes the previously misleading mock instead of deleting the roundtrip expectations.
- **Parent's final native run: 8 tests / 458 assertions PASS**, private `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/contact-native-repair-20261022T045003109502Z/native.log`. Six cases perform real HTTP GET for EN/DE shop, shared SAJ and translated inverter category: actual escaped archive href → Contact → actual other-language href → target Contact, exact search bytes, source path, topic, return URL and normalization redirect; no recreated mock consumer. Two cases execute included/excluded protected Contact → fresh Woo metadata/Outbox, UUID replay and changed-payload rejection, plus native recovery.
- Independently read the fixture, native log, summary and before/after private snapshots. The two snapshot files are **byte-identical**, both SHA256 `d6192d83fa6cd1c2d3cc555cfb0172685292216d7fc5886a9848b21aac2c23ac`; they cover recorded options/queue/privacy/counts (531 products, 756 terms, 66 orders before and after; queue 0 before and after). The fixture's final transport guard asserts zero mail attempts. This is a review of parent-executed native evidence, not this reviewer's instance operation.
- The mistaken draft fixture expectation `/de/marke/saj/` was corrected to the actual native `/de/brand/saj/`, consistent with the existing native term API and earlier 90-request evidence. No route was changed to satisfy that mistaken assertion.
- Parent full commerce units/checks and official WindPress Generate are separate evidence. The final four-viewport CUA is ongoing at this report. A new source map, 200 responses, unit suite or queue check does not prove typography, hover/focus, inclusion visibility, geometry or deployed bytes.

## Remaining acceptance boundary

This final source PASS closes the named family/selection source defects only. Parent must complete same-version EN/DE ×1440/390 actual sort/filter/family controls and Contact include/exclude/unavailable/language journeys, visual review, generated/CI checks, backups and deployment/live readback. The eight new no-submit browser fixtures and actual CUA are separate from the native HTTP tests. No form/mail/model is submitted by the browser fixture. Contact message/selection consumers, source context and print/privacy/full-site routes are not collapsed into a generic all-site PASS. Ordinary Genie and other independent audit findings remain outside this 31-file scope.

## Reviewed final file hashes

### product sources

| Path | SHA256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/contact-card.css` | `2357b84cb55556af15407f48a668660444128074eabd62b81d44517f1cc50c65` |
| `plugins/linker-commerce/content/windpress/products.css` | `a9bfe0748fe1ee9fd57d85c3257fce26ae62a2e73c19f62afafb1b879af40367` |
| `plugins/linker-commerce/includes/Contact/Form.php` | `365bb6faf2e94b9e8b82b79623d6ea1c704532a7069196938fb84ea0b21a2d8e` |
| `plugins/linker-commerce/includes/Contact/Handler.php` | `83825b25e9147e1448574cf314e6b43f7acf0490df37b284f1c9922a758c5c5d` |
| `plugins/linker-commerce/includes/Contact/Module.php` | `0cf1f856ee293ebf414723963883a4111551b075895e03be968960f54e6946d1` |
| `plugins/linker-commerce/includes/Contact/SelectionContext.php` | `1efc949c963c0fd4eaeb08ae7235020d025dcbc6fae6330aca149143bc594a5b` |
| `plugins/linker-commerce/includes/Contact/SelectionView.php` | `d0b3a88d2b82409f0570f0f00123ff0b8108aac91c733196c8073b2ae19878e6` |
| `plugins/linker-commerce/includes/Contact/Submission.php` | `500a780d691cd329879799b6ced791b622f7096df485da37d4076ad618c2eeb3` |
| `plugins/linker-commerce/includes/Presentation/FamilyNavigation.php` | `b56ffddea507b0fd5889e6cebdbdfdcc0732596a95c491342ab9444b6f722c3e` |
| `plugins/linker-commerce/includes/Presentation/FamilyPage.php` | `6e78ee4c0d53ffc21502019ba3db6e1abd28a2c6bfeab31b806e97289c1215c8` |
| `plugins/linker-commerce/includes/Presentation/LanguageLinks.php` | `9e3f83dee694bc6ae04c2b9d7109a322ed590bd9ceedc23877971a4aba19e58d` |
| `plugins/linker-commerce/includes/Presentation/ProductShortcodes.php` | `76c01acd5c74fc9b4d03d50a61e6d84011fca847ef998c951ef1557fdbd9b6f7` |
| `plugins/linker-commerce/includes/Protection/FormRecovery.php` | `f6b2119e510fc7369d918d74fc387e6e0b726ebc5c03365a12813c3503834f0e` |
| `plugins/linker-commerce/includes/Storefront/ProductFilters.php` | `881446da25aed48a931596cc50af2d1972a363f73447ce8ce5c0352c6c6b8b3b` |
| `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.po` | `85528a09bafb835b79d677ae00f5207ef7d8221328dad2b467f8b335011e8205` |

### test sources

| Path | SHA256 |
| --- | --- |
| `plugins/linker-commerce/tests/php/Doubles/wordpress.php` | `c938a91155517d217b60ce1d725eebe0803add1e9c7e0c3e1893599a9bf927af` |
| `plugins/linker-commerce/tests/php/Integration/ContactNavigationTest.php` | `1cddb1dc5d61bb7a070f20b20390d61943bc4699ea863c35ccda3903438fdecf` |
| `plugins/linker-commerce/tests/php/Integration/ContactSelectionTest.php` | `ad3fbff3ad731207b3b0cb8dc5eb50d5c0d7cfc1556e9fc9270493d8af560efc` |
| `plugins/linker-commerce/tests/php/Unit/Contact/FormTest.php` | `aaa55e9d2178120e6b13b547f5996eb0c50fce69c4cfde44008fe2668955aac7` |
| `plugins/linker-commerce/tests/php/Unit/Contact/SelectionContextTest.php` | `d0c7ac465b09e1fa47ed4b89efa58f3a3048b241855714d330656b077450ced9` |
| `plugins/linker-commerce/tests/php/Unit/Contact/SelectionLinkTest.php` | `524886194e0d3ce51c40f998ed14bba44539ff19d5a0542755554d66f60a9c9e` |
| `plugins/linker-commerce/tests/php/Unit/Contact/SelectionViewTest.php` | `1d84a78037d2350dbfa8430602bc4b7c226a2dc7366bd0f0909ec734984ced5a` |
| `plugins/linker-commerce/tests/php/Unit/PluginTest.php` | `0c32c15fb115ee0d9680100430656a6d0390b397436ff18c9d7856d30615424b` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/FamilyNavigationTest.php` | `58055fe76cabdca3aecaf4e8c2a60b6c696005f0c9a8847fb4e481c8c48f3a36` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/FamilyPageTest.php` | `e6f653cac4ac476f09ed8a9e5c9fd08e961ac55733ef33518849cc6756d76f0b` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/ModuleTest.php` | `5426c00d5b56084919f081efb87b51e8efcac69599dd735c6119b79f3ccc92a5` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/ProductShortcodesTest.php` | `90008cbc952ab788ab4f69c0fab415685c825a06aa501c1971a699288a4fdf38` |
| `plugins/linker-commerce/tests/php/Unit/Storefront/ProductFiltersTest.php` | `4842a608bc44162f462e36863ba07244fdfaa3789688559be22443ad6da5d32f` |
| `tests/e2e/specs/contact-selection-continuity.spec.ts` | `738acb32a896e617a5958e62f76dad9f036a4a51708104384e61e2637a252320` |

### generated catalogs

| Path | SHA256 |
| --- | --- |
| `plugins/linker-commerce/languages/linker-commerce-de_DE_formal.mo` | `8c8d36b4eba357ffbdbad28f4a93832d83165a62ff07b58a132a208617d009e2` |
| `plugins/linker-commerce/languages/linker-commerce.pot` | `ea1a77f478e7d3195d71f542bdb6534a634fc81ce2349987ca0f41faf7475782` |
