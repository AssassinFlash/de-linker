# Full-page pixel parity

One entry point captures live/local with the same Chromium build and compares
every RGB pixel. It uses `tests/e2e`'s existing Playwright installation and Python
Pillow. It never submits forms or changes either site.

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

Capture conditions preserve the already measured procedure: software raster and
sRGB to avoid GPU dithering, disabled motion/caret, full-height layout before
decoding lazy images, and loaded fonts. The preview card is dismissed only in
each disposable browser context so the page is captured at rest. Historical
acceptance artefacts stay in their ticket directories; new runs call this tool.
