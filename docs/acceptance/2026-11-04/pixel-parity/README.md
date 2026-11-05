# Full-matrix pixel parity, 2026-11-04 → 2026-11-05

Scope: 12 routes × 1440/390, `https://de-linker.com` against
`http://127.0.0.1:8916` (local `fullmatrix` instance), same browser build, same
machine, `--direct` (no proxy), layout viewport held at width × 900 for the whole
capture.

## Result

`final/` (2026-11-05, live snapshot 20261105-1208 loaded into fullmatrix) —
**24 of 24 cases at exactly 0 differing pixels**, all sizes equal,
`sorted_containers_match: true` everywhere, no masks, no ruled regions, no
tolerances. `pixel-parity.mjs` exited 0 and the independent `compare.py`
recount exited 0 (48 zero-difference records).

This is the **uncompensated** matrix: no `pinImageSizes`, no DOM rewriting
beyond the declared normalizations (instant sweep, eager promotion, related
`sortChildren`, and the two timing settlements below). Live and local ran the
same deployed code.

### What the first two final attempts caught (both capture-side, both fixed)

- `attempt-20261105-related-order/` — 23/24, SAJ PDP at 390 one row shorter
  locally (9976 vs 9977). Every painted row was pixel-identical; Woo's
  add-to-cart.js appends a 1px screen-reader live region after load, and its
  arrival time differs per host. Fixed: Woo pages now wait for that final DOM
  before the CDP clip is measured.
- `attempt-20261105-srcset-race/` — same case, same heights. Direct probes
  showed the real cause: a lazy image's activation can race the final layout
  and keep an early srcset candidate. With byte-identical files and identical
  srcset/sizes, live painted the SAJ feature image at 211.125px from the 600w
  file and local at 210.875px from the 1280w file, shifting the document tail
  by 0.25px. Fixed: every srcset image is re-selected at the settled final
  state (both sides then choose the same candidate; measured 210.875px and
  equal page heights on both).

A related-products title-order change (PR941) was opened on the first attempt's
HTML diff and **closed unmerged as a misdiagnosis**: card order was already
normalized by `sortChildren`, and the zero row-level differences proved the
cards were not the cause. No production behavior change was needed for the
gate.

## Earlier capture proof

`batch3/` — 24 of 24 at 0 differing pixels, captured while the harness still
carried the `pinImageSizes` compensation. It proved the capture mechanism
deterministic before the product fix; the uncompensated `final/` above is the
actual gate.

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

Reproduce (after deployment; the same command with no compensation):

```sh
node tests/visual/pixel-parity.mjs <outdir> https://de-linker.com http://127.0.0.1:8916 \
  --widths 1440,390 --direct \
  --scenarios docs/acceptance/2026-11-04/pixel-parity/scenarios.json
python3 tests/visual/compare.py <outdir>   # recount without a browser
```

## What the earlier 7 failures actually were

`batch1/` (harness before this work) reported 7 failures across the same 24
cases. None of them was a product difference; each had a capture cause.

| Case                                     | 1440 (batch1 → batch2) | 390 (batch1 → batch2) |
| ---------------------------------------- | ---------------------- | --------------------- |
| `home`                                   | 0 → 0                  | 0 → 0                 |
| `de`                                     | 0 → 0                  | 0 → 0                 |
| `products`                               | 0 → 0                  | 0 → 0                 |
| `de_produkte`                            | 0 → 0                  | 0 → 0                 |
| `product_saj_ats1_t63_a`                 | 177,283 → 629          | 121,076 → 210         |
| `de_produkt_goodwe_gw60k_sts_g10`        | 147,800 → 0            | 120,337 → 0           |
| `solution`                               | 0 → 629                | 600 → 600             |
| `de_loesung`                             | 0 → 0                  | 240 → 0               |
| `hybrid_inverter_vs_ac_coupled_storage`  | 0 → 0                  | 15 → 0                |
| `de_hybridwechselrichter_vs_ac_speicher` | 0 → 0                  | 0 → 0                 |
| `cart`                                   | 0 → 0                  | 0 → 0                 |
| `de_loesungsentwurf`                     | 0 → 0                  | 0 → 0                 |

That intermediate comparison was 17 clean to 20 clean. It is retained to show
which failures were removed and which new compositor case appeared; it is not
the final gate. An aborted `repeat-1` had 14 recorded PNGs that matched batch2
exactly and was deleted only after that comparison, not to hide a failure.

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

First worked around in the harness with a `pinImageSizes` normalization (each
such image pinned to the width it actually paints at before its request is
made), which made the gate deterministic without touching the product. That
workaround has since been deleted: the real cause was that the pages never
emitted `sizes`, and it is fixed in the product now — see "Product fix" below.
`batch3/` was captured while the workaround was still present, so it is evidence
for the capture mechanism only.

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
(`captureBeyondViewport: true`). The installed Playwright already uses this same
engine path for `fullPage: true`; the defect was the separate viewport expansion
before calling it, not `fullPage` itself. An explicit clip keeps that resize out
of the capture and makes the full-document rectangle explicit. Every visible
image must have a selected source and decode successfully after the sweep;
missing sources and decode failures abort the capture rather than pass as two
identical blank images.

**The same 85,021-pixel signature still appears in one situation, and it is not
fixed.** With `pinImageSizes` removed, a live↔live control at 1440 reproduced it
on the SAJ PDP: two runs of the same URL against the same host, one 0 and one
85,021 at `[139,5032,510,5279]`, max 5 levels per channel, over the FAQ picture
and nothing else — the two crops are visually identical. That region is an
`<img>` painted far smaller than its file: the page serves `srcset` without
`sizes` today, so the browser lands on the 1536px-wide original and downscales
it, and the downscale rasterization is bistable in the renderer. It disappears
once the product fix ships, because `sizes` then picks a file close to the
painted width. It is recorded here rather than compensated in the harness: a
same-host control that fails is capture-visible renderer behaviour, and the
honest gate is the post-deployment run.

### 4. Woo shuffles related products on every request

`wc_get_related_products()` calls `shuffle()` behind the filterable
`woocommerce_product_related_posts_shuffle` (default `true`). Six live PDP
requests with a cache-busting query returned six different orders, with
`cache-control: no-store`. Two captures of the same page therefore differ in card
order even live against live.

Fixed by the declared `sortChildren` normalization: each declared container is
sorted by card title on both sides, and `compare.py` requires the resulting item
sets to be equal, so a different card set still fails.

## Product fix: `sizes` now ships with `srcset`

`ProductShortcodes::image_tag()` computed
`wp_get_attachment_image_sizes( $image_id, $size )` into `$sizes` and never
printed it. Every PDP image built by that helper therefore carried `srcset`
without `sizes`, which makes the browser assume `100vw`.

Two consequences, both real for customers:

- **Candidate choice was not tied to the painted width.** At 390 the SAJ feature
  image paints at 350px but the browser sized it as 390px and, on that basis,
  picked the 600w file on one host and the 1280w file on another from identical
  markup. A customer could receive a needlessly large download.
- **Layout was not identical between those two outcomes**, because the 600w and
  1280w files of that photo have different intrinsic ratios: 211.125px against
  210.875px painted height, which shifted everything below by 0.25px and made
  the document 9977px tall on one side and 9976px on the other.

Fixed in `ProductShortcodes::image_tag()`: when a candidate list is printed, the
computed size is printed after it as `sizes="…"`, escaped with `esc_attr()`, and
only when WordPress returned a non-empty string and the caller did not already
provide `sizes`. An explicit caller value such as `sizes="72px"` wins exactly
once; `srcset => null` still suppresses both, because a lone `sizes` attribute
selects nothing. Brand logos now carry their attachment's `sizes` from the same
WordPress source and print it alongside `srcset`. The attribute order remains
`width height src <caller attributes> srcset sizes`.

Covered by six unit tests in `ProductShortcodesTest`:
generated candidates carry `sizes` right after `srcset`; a `false` answer from
WordPress prints no `sizes`; the gallery main picture prints neither `srcset`
nor `sizes`; a quote inside the computed size is escaped rather than closing
the attribute; an explicit thumbnail `sizes="72px"` is not replaced or
duplicated; and the brand logo carries its attachment's computed size.

The harness's `pinImageSizes` compensation has been deleted. Nothing in the
capture rewrites page markup any more, so a red run now means a real difference.

## History

- `batch1/` — before this work. 24 cases, 17 clean, 7 failures.
- `batch2/` — after the first two normalizations (reload-at-final-viewport,
  related sorting). 20 clean, 4 failures, all four locally traced to the
  fractional layout produced by §2 and the compositor behaviour of §3.
- `repeat-2/`, `control-live-390/`, `control-pdp1440-{1,2}/` — runs that isolated
  the residue: same-host controls reproduced the same pixel counts at the same
  rectangles, proving the residue was capture-side. Kept because they are what
  ruled out a product cause for the sticky border and footer blur.
- `batch3/` — captured with the CDP clip _and_ the `pinImageSizes` workaround.
  24 of 24 at 0. Proves the capture mechanism, not an uncompensated matrix.
- `attempt-20261105-related-order/`, `attempt-20261105-srcset-race/` — the two
  23/24 final attempts; unique failure evidence for the live-region timing and
  the srcset activation race described in §Result.
- `final/` — the passing uncompensated matrix (24/24, both exits 0).
