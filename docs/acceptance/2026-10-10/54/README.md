# #54 parity archive (2026-10-10)

Filenames: `<page>-<viewport>-<lang>-<state>.png` per `docs/acceptance/protocol.md` §3C.

Pages: cart, checkout (empty Proforma request / login gate), account, shop, product (`goodwe-gw60k-sts-g10`), archive (`ci-ac-coupled`).
Viewports: 1440, 390. Languages: en, de. States: `local` (`http://127.0.0.1:8912`) and `live` (`https://de-linker.com`). 48 files.

HTTP while capturing (`python3 /tmp/t54-parity-shots.py`):

- All **live** EN/DE URLs: 200.
- Local EN: 200 for every page type.
- Local DE cart/checkout/account/shop/archive: **404** (Polylang languages empty on this instance; `#12` W2 Twins pairing not merged). Local DE product URLs 200 (same English slug under `/de/produkt/…` is not routed).

Judgement of visual parity is for the review line; this directory is the archive only.

## Review round (2026-10-10, fix-forward of PR #57)

The review line found the original capture shot the pages while the template
utility classes had **no CSS**: the "WindPress rebuild demo" below had
hand-assembled the visitor cache (the old live cache + a first-line comment +
two rules) instead of compiling, and `present` neither enforced freshness nor
checked the compiled classes. All three defects reproduced on record before
fixing:

- visitor CSS = the live cache byte-for-byte plus a 393-byte prefix
  (`/* t54-windpress-rebuild … */` + two `.ring-…` rules); the assembled file
  is kept at `/tmp/t54-assembled-cache-backup-20261010-195909.css`.
- `py-10`, `max-w-[1160px]`, `lg:grid-cols-3`, `text-[#0c7f73]` defined in
  **no** stylesheet the checkout/shop pages load.
- `present` only logged "windpress: cache present (compile from the WindPress
  admin)".

Fix, all executed for real on the t54 instance:

1. Assembled cache deleted (backup above); the new `present` then **refused
   the run** ("Error: No compiled cache exists (WindPress has never compiled)").
2. Real compile through the official channel: WindPress admin → Settings →
   Performance → **Generate** (Tailwind v4.3.3 in the admin browser →
   `admin/settings/cache/store` → `Cache::save_cache`). Product:
   `uploads/windpress/cache/tailwind.css`, 318,803 B, first line
   `/*! tailwindcss v4.3.3 | … */`, no assembled prefix, and **py-10, px-4,
   bg-white, max-w-[1160px], text-[#0c7f73], lg:grid-cols-3,
   text-(--proto-accent), border-(--proto-accent), bg-(--proto-accent) all
   present**. `WindPressCache::defect()` returns null; `present` ends
   "windpress: cache is newer than the templates/tokens and contains the
   template classes / Success".
3. `present` now compares the cache mtime against the templates/tokens after
   installing (a stale cache **fails the run**, `--allow-stale` is the escape),
   and warns when the compiled CSS misses the templates' anchor classes or
   WindPress is inactive. Both failure modes were triggered live on record
   (stale after editing the templates: "Error: Cache compiled …, templates/
   tokens newest …").
4. The shortcode truncation the real compile exposed — WP's shortcode parser
   ends `class="… border-[#0c7f73] …"` at the first `]`, leaking the rest as
   text — is fixed in the exported templates by the Tailwind v4 CSS-variable
   shorthand (`text-(--proto-accent)` from `tokens.css`'s single source),
   and `text-(--proto-accent)` joined the anchor classes so a recurrence
   fails the class check.

Re-shot the pages the fix is visible on: **cart, checkout, account — EN ×
1440/390 local** (six files replaced). The other page types cannot re-shoot
against this fix any more: since `#12` merged, shop/product/archive render
through `linker-commerce`'s Storefront templates (`template_include` 99999
overrides LiveCanvas), which carry no Tailwind classes; their storefront CSS
additionally lacks the base `display: grid` declarations its selectors assume
(`.catalog-layout`, `.catalog-grid` — live's storefront declares them, the
plugin's copy does not), so those pages render unstyled until `#12`/`#16`
repair their own deliverable. The original LiveCanvas-rendered shots of
shop/product/archive below are the state PR #57 was merged with and are kept
as the record of that review.

Known, pre-existing, not this ticket: the header partial prints
`[linker_contact_link placement="header"]` literally (LiveCanvas partial
content, `#12` W3 scope).

Archive 301 (review round, 2026-10-10): the live archive URL the
`archive-*-live.png` shots were framed on no longer serves 200 —
`https://de-linker.com/product-category/ci-ac-coupled/` now answers
**301 → /product-category/commercial-storage/all-in-one-systems/** (the
category was moved after the capture). The files show the redirect target's
page, not the addressed one; the README's original "All live EN/DE URLs:
200" line described the capture moment and no longer holds for this URL.

## Round two (2026-10-10, fix-forward of PR #59): the compile is a recipe now

The owner found the instance serving unstyled pages after the round-two
present/rollback test loops had rewritten template content without a fresh
WindPress compile. `just windpress-compile <instance>` closes that gap as an
executable step: it mints the instance's one-time login, drives the WindPress
admin with Playwright (Settings → Performance → Generate — the only compile
that exists, Tailwind v4 has no server-side build), waits for the
`admin/settings/cache/store` answer, refuses unless the cache file got newer,
and then runs the plugin's own anchor-class check
(`WindPressCache::missing_anchor_classes`) over the product, failing on any
missing class. Playwright resolves from plugins/linker-tools; the recipe
drives the full chromium build (`channel: 'chromium'`, installed on demand) —
a DOM `dispatchEvent('click')` reaches the Generate button because WindPress's
review-request toast viewport swallows real pointer clicks.

Close-out evidence, all on t54 under the compile this recipe performed
(cache `?ver=1791647959`, 318,626 B):

- Class coverage spot check on the product: `.max-w-\[1160px\]` and
  `.text-\[\#0c7f73\]` both present (grep -F, served URL included); the
  recipe's anchor gate passed with `[]` missing.
- Screenshots (`*-1440-en-local-recompiled.png`, guest, full page): **cart,
  checkout (the empty Proforma request — `sf-checkout-empty` gate) and
  account are LiveCanvas-rendered and visually complete** under the fresh
  cache. **Shop, product and archive render through linker-commerce's
  Storefront path** (the `template_include` override from #12) and carry the
  pre-existing unstyled-Tailwind state recorded above — not cache-dependent,
  archived here as the current state for #12/#16.

Honest measurement note: an earlier grep with a mis-escaped pattern reported
the two classes missing from the pre-compile cache; the pre-compile file is
overwritten by this recipe's compile, so that claim is withdrawn — the fresh
compile and its verified product are what this round guarantees.

