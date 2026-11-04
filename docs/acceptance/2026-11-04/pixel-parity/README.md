# Full-matrix pixel parity, 2026-11-04 → 2026-11-05

Scope: 12 routes × 1440/390, `https://de-linker.com` against
`http://127.0.0.1:8916` (local `fullmatrix` instance), same browser build, same
machine, `--direct` (no proxy), layout viewport held at width × 900 for the whole
capture.

## Result

`batch3/` — **24 of 24 cases at exactly 0 differing pixels**, all sizes equal,
`sorted_containers_match: true` everywhere, no masks, no ruled regions, no
tolerances. The command exited 0.

```
home                                  1440  0   390  0
de                                    1440  0   390  0
products                              1440  0   390  0
de_produkte                           1440  0   390  0
product_saj_ats1_t63_a                1440  0   390  0
de_produkt_goodwe_gw60k_sts_g10       1440  0   390  0
solution                              1440  0   390  0
de_loesung                            1440  0   390  0
hybrid_inverter_vs_ac_coupled_storage 1440  0   390  0
de_hybridwechselrichter_vs_ac_speicher 1440 0   390  0
cart                                  1440  0   390  0
de_loesungsentwurf                    1440  0   390  0
```

The count was re-derived twice from the raw PNGs with Pillow alone, without
`compare.py`: 24 live/local pairs, 0 non-zero, 0 size mismatches.

Reproduce:

```sh
node tests/visual/pixel-parity.mjs <outdir> https://de-linker.com http://127.0.0.1:8916 \
  --widths 1440,390 --direct \
  --scenarios docs/acceptance/2026-11-04/pixel-parity/scenarios.json
python3 tests/visual/compare.py <outdir>   # recount without a browser
```

## What the earlier 7 failures actually were

`batch1/` (harness before this work) reported 7 failures across the same 24
cases. None of them was a product difference; each had a capture cause.

### 1. `scroll-behavior: smooth` defeated the lazy-load sweep

The site sets `scroll-behavior: smooth` on the root element. The old sweep used
`window.scrollTo(0, y)`, which starts an animation, and the next call interrupts
it, so the sweep never reached the lower sections. Measured at 390 on the SAJ
PDP: the loop asked for the document bottom and stopped at y = 3386 of a
possible 5927, five visible images still had an empty `currentSrc`, and
`img.decode()` on them never settled — the capture hung rather than failing
loudly. With `behavior: "instant"` the sweep reaches 5927 and 14/14 visible
images have a source.

This only became load-bearing once the viewport stopped being grown to the full
document height; the older procedure hid it by making every image lie inside the
viewport.

### 2. `srcset` without `sizes` made candidate selection timing-dependent

`img[srcset]` with no `sizes` assumes `100vw`. For the SAJ PDP feature image,
painted 350px wide inside a 390px viewport, the browser's choice was not stable
across hosts: three runs on the live host picked
`saj_ats1-t63-a_product_front-600x338.jpg`, three runs on the local host picked
`saj_ats1-t63-a_product_front.jpg`, from byte-identical markup (`sizes` absent
on both). The two files carry different intrinsic ratios, so the painted box was
211.125px on one side and 210.875px on the other, and every element below it
shifted by 0.25px — 324 elements differed, and the document was 9977px tall on
one side and 9976px on the other.

Fixed by the declared `pinImageSizes` normalization: each such image is pinned to
the width it actually paints at before its request is made, so both hosts fetch
and render the same candidate. The pins are recorded per side in `capture.json`.

### 3. Viewport expansion re-rasterized already-decoded images

The old procedure laid the page out at 900px, scrolled it, then grew the viewport
to the document height and captured with `fullPage: true`. Images whose decode
had begun at the shorter height were re-rasterized for the taller viewport, and
the result depended on how far decoding had progressed when the resize landed.
Measured on the SAJ PDP FAQ image: 85,021 differing pixels, max 5 levels per
channel, mean 1.09, no shift — while the image bytes, the
`naturalWidth`/`naturalHeight`, and canvas hashes drawn at natural size and at
box size were identical on both hosts.

Fixed by never resizing: the layout viewport stays at width × 900, and the whole
document is taken with a CDP `Page.captureScreenshot` clip
(`captureBeyondViewport: true`). `fullPage: true` is not used anywhere.

### 4. Woo shuffles related products on every request

`wc_get_related_products()` calls `shuffle()` behind the filterable
`woocommerce_product_related_posts_shuffle` (default `true`). Six live PDP
requests with a cache-busting query returned six different orders, with
`cache-control: no-store`. Two captures of the same page therefore differ in card
order even live against live.

Fixed by the declared `sortChildren` normalization: each declared container is
sorted by card title on both sides, and `compare.py` requires the resulting item
sets to be equal, so a different card set still fails.

## History

- `batch1/` — before this work. 24 cases, 17 clean, 7 failures.
- `batch2/` — after the first two normalizations (reload-at-final-viewport,
  related sorting). 20 clean, 4 failures, all four locally traced to the
  fractional layout produced by §2 and the compositor behaviour of §3.
- `repeat-2/`, `control-live-390/`, `control-pdp1440-{1,2}/` — runs that isolated
  the residue: same-host controls reproduced the same pixel counts at the same
  rectangles, proving the residue was capture-side. Kept because they are what
  ruled out a product cause for the sticky border and footer blur.
- `batch3/` — final harness. 24 of 24 at 0.
