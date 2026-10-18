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
sRGB to avoid GPU dithering, disabled motion/caret, full-height layout before
decoding lazy images, and loaded fonts. The preview card is dismissed only in
each disposable browser context so the page is captured at rest. Historical
acceptance artefacts stay in their ticket directories; new runs call this tool.

For a disclosure or another state, use `--scenarios <json>` instead of
`--paths`. Each scenario contains a unique `name`, `path`, optional `widths`,
ordered `actions` (`click`, `fill: [selector, value]`, `press: [selector, key]`,
or `visit: "/relative/path"`),
and `ruledRegions: [{name, selector, padding?}]`. Selectors may match repeated
components; each matching rectangle is recorded separately, using the union of
the live and local bounds. A new component may be absent on live; it must exist
locally. Padding is an explicit part of the ruled region, for example the
existing shadow of an expanded account menu, and needs ledger evidence.

`--baseline` captures the local before images only (and reuses existing before
images). It does not compare or change the site. Normal capture keeps full raw
images and exact raw pixel counts. The comparator additionally reports
`outside_ruled_different_pixels`; any nonzero value fails. Different image sizes
are recorded as failures and are never cropped, padded or aligned away.

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
