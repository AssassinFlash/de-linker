# Full-page pixel parity

One entry point captures live/local with the same Chromium build and compares
every RGB pixel. It uses `tests/e2e`'s existing Playwright installation and Python
Pillow. It never submits inquiry, account or payment forms. The optional `visit` fixture
below can populate a disposable anonymous solution draft and then empty it.

```sh
node tests/visual/pixel-parity.mjs <outdir> <live-base> <local-base> \
  --widths 1280,1440,1920,390 --paths /,/de/ \
  --allow-header /de/:1440,1920:89
```

The caller supplies widths, routes and explicitly ruled header changes. The
example permits a German header change at 1440/1920 within its measured 89px
height. All other pixels must match exactly. There are no masks or tolerances;
dimension mismatches fail instead of cropping the evidence.

The output contains full-page PNGs, header pairs, red difference images,
`capture.json` (cases and allowed changes), and `results.json` (exact counts and
bounds). Recount without a browser using:

```sh
python3 tests/visual/compare.py <outdir>
```

Run the comparator's exact-colour and dimension regression fixtures with:

```sh
python3 -m unittest discover -s tests/visual -p 'test_*.py'
```

Capture conditions preserve the already measured procedure: software raster and
sRGB to avoid GPU dithering, disabled motion/caret, decoded images and fonts, and
native lazy loading; hidden lazy menu images are not awaited.

The capture never resizes the layout viewport. It stays at the requested width
and the established 900px height, the page is scrolled through once at that size
so native lazy images enter it, and the full page is then taken with a CDP
`Page.captureScreenshot` clip of the document rectangle (`captureBeyondViewport`).
`fullPage: true` is deliberately not used: Playwright implements it by resizing
the viewport, which re-lays-out the document and re-rasterizes images that were
already decoded at the shorter height. Measured before this change, that
re-raster differed by up to 10 levels per channel on the same page served by a
different host while the image bytes, the `naturalWidth`/`naturalHeight`, and
canvas hashes drawn both at natural size and at box size were identical.

The scroll sweep must scroll instantly. The site sets `scroll-behavior: smooth`
on the root element, so a plain `window.scrollTo(0, y)` starts an animation the
next call interrupts; the sweep then never reaches the lower sections, their
lazy images keep an empty `currentSrc`, and `img.decode()` on them never
settles — the capture hangs (measured: five images still without a source).

One input is normalized before the capture, because it is non-deterministic on
the live site itself and would otherwise turn a measurement artifact into a
reported defect. It is opt-in per scenario and recorded in `capture.json`:

- **Declared child sorting** (`sortChildren: [{selector, key}]`). Woo calls
  `shuffle()` in `wc_get_related_products()` behind the filterable
  `woocommerce_product_related_posts_shuffle` (default true), so the related
  products block renders in a different order on every request — verified by
  requesting the live PDP six times with a cache-busting query: six different
  orders, `cache-control: no-store`. Each declared container is sorted by its
  key text on both sides before the screenshot, and `compare.py` requires the
  resulting item sets to be equal, so a different card set still fails. This is
  not a mask: every pixel of every card is compared, only the order is fixed.

Nothing else is normalized. Image candidate selection in particular is
compared as the pages actually behave: the product pages emit `srcset` together
with `sizes`, so the browser's choice follows the painted width rather than a
`100vw` guess. The capture reads the markup as served and never rewrites it.

`docs/acceptance/2026-11-04/pixel-parity/scenarios.json` holds the current
full-matrix scenario list (12 routes × 1440/390), including the PDP routes'
`sortChildren` declaration.

For filled drafts, `capture.json` also records the selected cart image URL and
natural size for each side. The preview card is dismissed only in
each disposable browser context so the page is captured at rest. Historical
acceptance artefacts stay in their ticket directories; new runs call this tool.

For a disclosure or another state, use `--scenarios <json>` instead of
`--paths`. Each scenario contains a unique `name`, `path`, optional `widths`,
ordered `actions` (`click`, `fill: [selector, value]`, `press: [selector, key]`,
or `visit: "/relative/path"`), optional `sortChildren`, and
`ruledRegions: [{name, selector, padding?}]`. Selectors may
match repeated components; each matching rectangle is recorded separately, using
the union of the live and local bounds. A new component may be absent on live;
it must exist locally. Padding is an explicit part of the ruled region, for
example the existing shadow of an expanded account menu, and needs ledger
evidence.

`--baseline` captures the local before images only (and reuses existing before
images). It does not compare or change the site. Normal capture keeps full raw
images and exact raw pixel counts. The comparator additionally reports
`outside_ruled_different_pixels`; any nonzero value fails. Different image sizes
are recorded as failures and are never cropped, padded or aligned away. Every
`results.json` row carries the case stem, the route and the viewport width so a
reading can be traced to its scenario without cross-referencing indices.

`--direct` disables the system proxy only in the disposable capture browser,
for machines whose HTTPS proxy intermittently refuses CONNECT tunnels. It does
not change system settings or rendering flags; the capture manifest records the
network route. Default behavior remains the system route.

A scenario with `emptyDraftAfter: true` is an explicit disposable cart fixture.
Its `visit` actions can call Woo's existing `?add-to-cart=ID` on the same base,
then return to the draft. In `finally`, the capture follows that anonymous
session's native nonce-bearing `a.remove` links and verifies it is empty.
No signed-in cookie is loaded and no order, inquiry or email is submitted.
Use a language-specific add route (for example `/de/?add-to-cart=4107`) so the
native Woo notice is in the same language as the captured page. The manifest
records the declared scenario; the raw full-page images remain unchanged.
