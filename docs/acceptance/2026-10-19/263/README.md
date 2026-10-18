# #263 · Links and language entries follow the language

Environment: local instance `c263`, live snapshot `20261019-0141`, branch
`feat/263-links-follow-language` on current `main` (includes #254). The merged
#254 German-address migration was applied locally before acceptance:
`wp linker-i18n german-urls --dry-run|--apply|--verify`, then
`wp linker-commerce present --allow-stale` and `wp rewrite flush` (as the
ticket instructs).

## Completion criteria

| # | Criterion | Evidence | Result |
|---|---|---|---|
| 1 | Every link finding of the audit is rechecked EN/DE | `link-audit-de.txt` (156 German URLs: 106 products, 10 posts, 25 pages, 10 product categories, 5 blog categories), `link-audit-en.txt` (167 English URLs), `findings-recheck.txt` (H1, H2, H3, H5, M2, M8 exact values), and the exhaustive sweep in `all-internal-links.txt`: **0** internal `<a href>` on any German page points outside `/de/` (except the English half of the language switch), and **0** `/de/` links appear on English pages (except the German half of the switch) | Pass |
| 1a | H1 — 104 German product pages send "Produkt anfragen" to the German contact page | `findings-recheck.txt` H1; the sweep checks every German product's `intent=product` href is under `/de/kontakt/` and the English product's under `/contact/` | Pass |
| 1b | H2 — header and footer language switches are one implementation and reach the twin | `LanguageLinks` is the single implementation (header `toggle()`, footer `footer()`, shortcode `[linker_language_switch]`); the footer partials no longer carry static hrefs. `findings-recheck.txt` H2; the sweep checks the footer on all 156 German URLs (EN half never the same German path) and all 167 English URLs (DE half on `/de/` and the twin). Header tests: `ProductShortcodesTest` account/confirmation/category paths | Pass |
| 1c | H3 — German legal pages link the German legal twins | `findings-recheck.txt` H3; the sweep checks all four legal pages carry `/de/impressum/`, `/de/datenschutz/`, `/de/verkaufsbedingungen/`, `/de/rueckgabe-erstattung/` and no relative English legal href | Pass |
| 1d | H5 — German category breadcrumb names and home link follow German | `findings-recheck.txt` H5; the sweep checks `/de/produkte/` and all 10 German product categories: home href `/de/`, no English crumb word | Pass |
| 1e | M2 — German blog posts, `/de/danke/`, category CTA and compare breadcrumb | `findings-recheck.txt` M2; sweep: 10 German posts contain no `/product-category/` link; `/de/danke/` → `/de/blog/`; `/de/kategorie/systemauslegung/` → `/de/produkte/`; compare "Startseite" → `/de/` | Pass |
| 1f | M8 — Polylang's 301 keeps `/de/` inside query values | `findings-recheck.txt` M8: both the contact source URL and a search value answer `200` (before: 301 with the `/de/` stripped). Unit fixture `CanonicalQueryTest` (6 tests) | Pass |
| 2 | CI rule forbids hard-coded `home_url('/…')` in plugins and is live in `just check` | `tools/checks/internal-home-urls.py`, recipe `internal-home-urls` in `just check` and CI (`just check`). `internal-home-urls-red-green.txt`: `--rev origin/main` → 27 literals, exit 1; branch → clean, exit 0 | Pass |
| 3 | Email-language fixtures for front-end, admin and scheduled triggers, including the #243 two-languages-in-one-process note | `plugins/linker-commerce/tests/php/Integration/LanguageLinksInMailTest.php`, 5 tests / 61 assertions, run twice (repeatable): front-end inquiry receipt; admin approval; admin Proforma; scheduled Outbox retry; EN→DE→EN in one process. Added to the CI integration filter | Pass |
| 4 | EN 0 differing pixels | `tests/visual/pixel-parity.mjs`, live vs local, same browser/viewport, animations off, decoded images bounded. 1440: `/`, `/contact/`, `/products/`, `/product-category/inverters/`, `/compare-products/`, `/faq-download/`, `/imprint/`, `/my-account/`, `/cart/` — 0 differing pixels each (`pixel-1440-home-contact.json`, `pixel-1440-batch2.json`, `pixel-1440-batch3.json`). 390: the same nine pages — 0 each (`pixel-390.json`). The English product page, blog index, blog single and Proforma request page already differ under the #254/#246 change ledgers (their redesigns), not under #263; on those, the footer region was checked separately (solution page footer: 0 differing pixels, 574-row box) and the #263 change itself is href-only. | Pass for #263's surfaces |
| 5 | Ruled German changes in the change ledger | `change-ledger.md` (H5 is the only pixel-visible German change; all others are href-only) | Pass |
| 6 | Customer-visible copy through the copy review | `copy-review.md`: no new copy; reused reviewed strings and German term data | Pass |

## Structural changes

- `Presentation\PageUrls` gained `home()` (current language's home) and
  `page()` (translated page or that home); every plugin address now goes
  through it. The one literal-friendly home fallback is inside `PageUrls`
  itself and is the CI rule's reference implementation.
- `LinkLocalizer` now resolves in **either** direction to the requested
  target language (`url( $url, $language )`, `localize( $html, $language )`),
  resolves retired category addresses through the one legacy map
  (`linker-tools/data/legacy-redirects.json`) instead of duplicating it, and
  memoises answers per request.
- `RenderLinks` (`the_content`, `the_excerpt`, `widget_text_content`, priority
  20, front end only) is the render-time fallback: stored German content gets
  German links without waiting for a translation job and without a data write.
- `CanonicalQuery` (`pll_check_canonical_url`, `redirect_canonical`) restores
  the requested query values that Polylang's global language removal
  corrupted.
- `Presentation\LanguageLinks` is the one language-entry implementation behind
  the header toggle and the footer switcher; the footer partials call the
  `[linker_language_switch]` shortcode.

## Tests run

- `just check` — green (PHPCS, PHPStan, JS/TS, Python, banned words,
  `internal-home-urls`, i18n coverage/validity, build reproduction).
- `just test` — green (PHPUnit unit suites, JS unit/E2E, pytest).
- `LanguageLinksInMailTest` against `c263` — 5 tests / 61 assertions, twice.
- `LinkLocalizerTest`, `RenderLinksTest`, `CanonicalQueryTest`,
  `PageUrlsTest`, `ProductViewTest`, `ProductShortcodesTest` — green.

## Production steps (Claude)

Deploying this ticket is the normal file deploy; the deploy already invokes
`present` (which installs the two footer partials and both compare templates).
No database migration and no data write are introduced by #263. Rollback is
the file rollback plus the deploy's own presentation rollback; flush rewrite
rules only if the presentation templates changed without `present` running.

## Out of scope

- German copy/data findings (M1, M3, M4, M5, M6, M10) belong to #264.
- German checks/tools (L1, L5, L7, template lint) belong to #265.
- The German address/title migration and its production application belong to
  #254.
