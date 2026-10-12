# Header live sync — 2026-10-12

## Scope and status

Q5a/Q6: match live header composition, positions and density; only visual adjustments. Keep the approved Genie / Solution Configurator names and descriptions. Keep the repository's current Account\Menu items and Woo endpoint URLs, not live's former Quotes/Bulk order/payment flows. No production writes, passwords, shared browser tabs or account-content CSS edits.

**Functional: PASS. Official Computer Use: pending parent session. Zero-pixel parity: NOT PASS / not certified.** These isolated Chromium screenshots are functional evidence, not a replacement for the official visual gate. No masks or relaxed threshold were used.

Base: `b6bc08410d7c83a01fd6665b93e11bf555dccd5b` (`origin/main` fetched before branch creation). Branch `fix/header-live-sync`. Original t110 capture baseline came from main `2604c517b58f253cf9fcb0f7d8747482b5ea1a2a`; copied without modifying the main checkout or original filenames. Original dossier in `docs/research/2026-10-12-live-account-and-advisor/DOSSIER.md` remains unchanged.

## Complete gap inventory and repairs

| Component/state | Evidence before | Repair/result |
|---|---|---|
| Logo / EN six primary items | Existing sizes and x positions already matched | Preserved visual structure, links and density |
| Desktop Search | x1154.4 / 106.1px wide instead of live x1012.5 / 46px | LC mounts utilities; measured x1012.5, 46×46 |
| Desktop draft/cart | Missing; count could not render | Same Woo cart data, existing icon component, count only when nonzero |
| Desktop account | Missing; existing shortcode hard-coded guest labels, no interaction | Login state + Woo `wc_get_account_menu_items()` and `wc_get_account_endpoint_url()`; one disclosure controller |
| Desktop language | Missing | EN/DE native links with current-language marker; x1172.5, 88×44 at EN1440 |
| DE1440 fit | Missing utilities falsely kept desktop nav / contact CTA | Content-fit controller compacts then folds: folded=true, live coordinates search1109.6/account1217.6/lang1269.6 |
| Mobile Search / language | x276 instead of172; language absent | Language alongside hamburger; final 96px rail incl 4px each-side spacing restores search x172 |
| Mobile account / draft | Account absent; static draft had no count source | Semantic mobile data fragments, root account link; existing Menu remains desktop source |
| Products mega first open | 339.7px vs516.3 before deferred images loaded | Existing lazy loader retained; images decoded for open-state captures; image geometry remains LC + CSS |
| Solutions / Partners / About mega | Existing structures matched; needed full-state verification | Preserved hierarchy/card density; open/close/arrow/Escape checked |
| Tools mega / mobile | Approved rename, longer descriptions, three→two tools are intentional | Preserved #12 final copy and approved two-card composition; not masked as parity debt |
| Sticky / mobile panel | Sticky geometry matched but utility omissions persisted | Sticky 0 top after scroll; panel categories and close state checked |
| Account card shape | Small 200px generic dropdown rather than live visual | WindPress 292px /14px radius /41px row /native-source item count |
| DE utility labels | Sign in / My account / Cart missing from plugin PO | Added narrow professional German translations, rebuilt MO |

## Implementation ownership

- `content/livecanvas/partials/header.html` and `partials/de/header.html`: actual exported LC compositions. Component CSS and embedded interaction code removed from these exports; canonical site tokens/reset retained, font asset URLs point at new plugin.
- `content/windpress/chrome.css`: header visual declarations + language/account/count styling, one WindPress volume.
- `assets/header-menu.js`: sole header nav/account/mobile disclosure and content-fit controller. Hover, click, keyboard arrows, outside click, Escape/focus; no business rules.
- `CatalogShortcodes::header_utilities`: semantic fragments only. No parallel menu derivation; Woo's filtered menu is current Account\Menu authority. No CSS/inline layout or new business URLs.
- `Templates::sync_header_partials`: narrow existing-header + Polylang twin file sync, no substitute partial creation or assignment change; `present` now backs up partials before replacement.
- `Presentation/Module.php`: header script registration only. Account branch may independently add another consumer here; parent handles merge, no extra abstraction.

## Evidence and checks

Local site survives at **http://127.0.0.1:8975/** and **http://127.0.0.1:8975/de/**. t110 plugin symlinks bind this worktree, not main. Dependencies copied locally with correct classmap; old PHP workers restarted to discard symlink realpath cache. No snapshot rebuild or service/prototype change.

- `original/2026-10-12-header-gap/captures/`: prior live vs t110 screenshots and facts; no overwrites.
- `original/header-en.html`, `original/header-de.html`: original LC stored markup.
- `after/`: 66 state screenshots, eight combinations guest/customer-3 × EN/DE ×1440/390 (900px tall). Header open mega or folded drawer categories, account, base, sticky.
- `measurement.json`: precise boxes, current native menu URLs, error arrays, functional status. Mobile measurements at that checkpoint were x180 before final 8px rail correction; `final-delta.json` is the final authoritative narrow measurement.
- `check.mjs`: repeatable isolated functional checks. No live write; local magic-login only.
- WindPress official admin worker compile succeeded, cache570003 bytes; final rail correction compiled again (see `checks.json`).
- PHP syntax; changed-file PHPCS passed; focused TemplatesTest + ModuleTest **24 tests /87 assertions PASS**; JS syntax; git diff whitespace check passed.
- Eight real browser combinations PASS: no literal shortcode; account enter/arrow/Escape; all nav or drawer categories; mobile account root; sticky; zero browser page errors. Login via local one-time URL, no password.

## Parent's remaining official gate

Open each locale at1440/390, guest plus logged-in customer (mint `just login t110 --user=customer-3` locally). Check Search target, zero/nonzero draft count, account hover/click/keyboard close and current seven-item Menu URLs, language switch, all five megas or drawer accordions (DE1440 intentionally folds), tools approved copy, sticky scroll. Also compare screenshots using same official browser with animations disabled and fonts/images settled.

Actual pixel equality has not been measured/certified by the official surface; do not mark accepted merely from boxes. Approved tools rename/two-card layout and repository-only account menu text are separate change ledger items, not undeclared dynamic masks. Nonzero cart count is real session state; live-only logged-in data was not mutated or newly authenticated in this run. Account page inner content is another lane, excluded here.

## Seven required fixes — 2026-10-12 (follow-up on b01f46e)

HTML assertions below are `curl` of the local t110 instance (127.0.0.1:8975, plugin symlink to this worktree), not a browser verification.

1. Language switch keeps context. `CatalogShortcodes::language_url` reads Polylang's own switcher (`pll_the_languages`, whose URLs pass linker-i18n's `pll_translation_url` filter) and carries the request's account endpoint and the query keys the visitor actually set (`s`, `orderby`, `step`). Curl, both directions: `/my-account/inquiries/` ↔ `/de/mein-konto/inquiries/`; `/linker-planner/?step=roof` ↔ `/de/linker-planer/?step=roof`; `/products/?orderby=price` ↔ `/de/produkte/?orderby=price`; `/?s=battery` ↔ `/de/?s=battery`; `/product-category/home-storage/` ↔ `/de/produkt-kategorie/heimspeicher/`. A category no longer falls back to the home page.
2. The German header export no longer points at English solution pages. `de/header.html` links `/de/loesung/heimspeicher/`, `/de/loesung/gewerbespeicher/` and `/de/loesung/grossspeicher/` (the live German addresses), so a repeat `present` keeps them.
3. The tools roof carries its 35 panel cells as static `<rect>` markup in both header exports. The WindPress rule that drew them at `opacity:0` / `scale(.3)` now only sets their fill and stroke, so the cells are visible without the script that used to draw them.
4. The header's draft link reads Solution draft / Lösungsentwurf, including its aria-label. The `Cart` / `Warenkorb` pair is gone from the plugin's German catalog; the existing `Solution draft` entry translates it.
5. `PresentCommand::sources()` includes both header partials, so a missing or empty one is refused before anything is written. `Templates::sync_header_partials` refuses the same way.
6. The two header partials no longer inline the 8755-character tokens block or the 1434-character site-base reset. Both now live once, in the WindPress volume (`content/windpress/tokens.css`, identical to `content/tokens.css`, and `content/windpress/site-base.css`). A Tailwind 4.3 compile of the volume keeps every declaration, including `all: revert`.
7. An outside click and a focus leaving the mobile panel close it and clear `aria-expanded`, the same way Escape already did (`assets/header-menu.js`).

The `pll_get_post` stub the whole suite was missing is added inside the presentation tests, so `test_detach_partials` no longer depends on another test's mock.
