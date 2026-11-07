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
The installed Playwright already uses this engine path for `fullPage: true`; an
explicit clip makes the rectangle and no-resize contract visible. The earlier
error was the separate `setViewportSize` call before that screenshot, not
`fullPage` itself. Measured before removing that call, re-rastering differed by
up to 10 levels per channel while image bytes, intrinsic dimensions and canvas
hashes at natural and box size were identical. After the sweep, every visible
image must have a selected source and decode successfully; a missing source or
decode failure is an explicit capture failure, never an empty-image pass.

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

# Deterministic layout self-check

`layout-selfcheck.mjs` loads real pages, evaluates `layout-probes.js` in the
page and reports layout defects as selectors and measured numbers — no
screenshots are read, so nothing depends on a human (or a model) looking at
pixels. It uses the same Playwright installation as the capture above and
adds no dependency.

```sh
just layout-selfcheck                      # production, 1440x900 + 390x844
just layout-selfcheck --selftest           # planted-fixture suite
node tests/visual/layout-selfcheck.mjs \
  --base https://de-linker.com --out .scratch/visual-selfcheck/run \
  --widths 1440,390 --heights 900,844 --only proforma
```

The six production pages are `home`, `products`, `proforma-request`, `cart`,
`faq-download` and the guest inquiry confirmation at
`/proforma-request/inquiry-received/8457/?key=…`. Each page's German twin is
resolved from its own `<link rel="alternate" hreflang="de">` at run time, so a
changed permalink does not silently test English twice.

For an already language-specific batch (for example product-matrix
representatives), pass exact paths instead. `name=path` gives the report a
stable name; the value may be a bare path (starting with `/`, may carry a
query string whose `=` is not a separator) or an absolute URL whose origin is
stripped. German is inferred from an exact `/de` or `/de/` prefix, and no
alternate resolution may substitute another record:

```sh
node tests/visual/layout-selfcheck.mjs \
  --base https://de-linker.com --out .scratch/visual-selfcheck/products \
  --widths 1440,390 --heights 900,844 \
  --paths 'gw3k=/product/goodwe-esa-gw3k-eha-g20-3-kw-single-phase-power-module/,gw10k=/de/produkt/goodwe-esa-gw10k-eha-g20-10-kw-einphasiges-leistungsmodul/'
```

What it checks, all from `getComputedStyle` and `getBoundingClientRect`:

| type                   | rule                                                                                                                                                                                                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `overflow-x-visible`   | `scrollWidth - clientWidth > 1` while `overflow-x: visible`, reported once at the innermost element that spills                                                                                                                                                                |
| `clipped-by-ancestor`  | element extends past the padding box of a `hidden`/`clip` ancestor; an `auto`/`scroll` ancestor makes that axis reachable (content beyond it is scrollable), the other axis can still be reported; content inside a closed `<details>` is a hidden state and is never reported |
| `opt-out-of-centering` | grid container with `justify-items: center` (or `align-items: center`) whose child sets `justify-self`/`align-self` to start/end and measurably hugs that edge while narrower than the container — the confirmation-page CTA signature                                         |
| `text-clipped`         | single-line text (`nowrap` or a line clamp) whose `scrollHeight` exceeds `clientHeight` under a clipping `overflow-y`                                                                                                                                                          |
| `focusable-invisible`  | `a`/`button`/`[role=button]`/`[tabindex]` in the tab order while `visibility: hidden`, `opacity: 0` or clipped to 1px                                                                                                                                                          |
| `small-target`         | an in-flow interactive element smaller than 24px in either axis (WCAG 2.2 inline-text and screen-reader-text exceptions applied)                                                                                                                                               |
| `image-broken`         | a complete `img` with a source and zero `naturalWidth`                                                                                                                                                                                                                         |
| `font-error`           | a `document.fonts` face whose status is `error`                                                                                                                                                                                                                                |
| `horizontal-scroll`    | `documentElement.scrollWidth > clientWidth`, with the offending elements listed                                                                                                                                                                                                |
| `overlap`              | two in-flow sibling blocks whose intersection exceeds 40% of the smaller one (fixed/absolute/sticky layers excluded)                                                                                                                                                           |

A hit that instead sits inside a laid-out track wider than its clipping frame
(the metrics carry `carousel`) is a carousel slide, not lost content, so
`overflow-x-visible` and `clipped-by-ancestor` report it at `review` severity;
the track only counts when an ancestor actually clips it, otherwise the spill
stays a defect. `opt-out-of-centering-vertical` and `small-target` also carry
`review` severity: they are real measurements but the verdict can legitimately
be "intended". Everything else is `defect` severity and makes the command
exit 1.

Overlay exceptions are declared in `OVERLAY_SELECTORS` in the runner (cookie
banner, Genie button and panel, Woo store notice, skip links); their overlap is
their purpose. `--selftest` opens `layout-fixture.html` from disk, which plants
one instance of every defect class plus nine near-misses that must stay silent,
and fails if any planted class is missed or any control is reported. Run it
whenever a probe rule changes — a suite that finds nothing on production is
only informative if it can still find the planted bugs.

The run is read-only: navigation and `page.evaluate` only. It never submits a
form, adds to a cart, creates an order or sends mail. It writes
`layout-selfcheck.json` under `.scratch/visual-selfcheck/` (untracked).
