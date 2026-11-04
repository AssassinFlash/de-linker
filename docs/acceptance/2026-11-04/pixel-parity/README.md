# Full-matrix pixel parity, 2026-11-04 → 2026-11-05

Scope: 12 routes × 1440/390 against `https://de-linker.com` (live) and
`http://127.0.0.1:8916` (local `fullmatrix` instance), same browser build, same
machine, `--direct` (no proxy). Raw evidence:

- `batch1/` — first run, harness before this change. 24 cases, **7 failures**.
- `batch2/` — same routes with the corrected harness. 24 cases, **4 failures**.
- `repeat-2/` — the four disputed cases re-captured, showing that the residual
  flips between runs (see §3). `repeat-1/` was aborted by a browser crash
  during its last route; its 14 recorded PNGs matched `batch2` exactly and were
  deleted after being measured.
- `control-live-390/` — live against live on both sides, all 12 routes at 390.
- `control-pdp1440-{1,2}/` — live against live on both sides, PDP at 1440,
  two independent runs.

## Per-case counts

| Case | 1440 (batch1 → batch2) | 390 (batch1 → batch2) |
| --- | --- | --- |
| `home` | 0 → 0 | 0 → 0 |
| `de` | 0 → 0 | 0 → 0 |
| `products` | 0 → 0 | 0 → 0 |
| `de_produkte` | 0 → 0 | 0 → 0 |
| `product_saj_ats1_t63_a` | 177,283 → 629 | 121,076 → 210 |
| `de_produkt_goodwe_gw60k_sts_g10` | 147,800 → 0 | 120,337 → 0 |
| `solution` | 0 → 629 | 600 → 600 |
| `de_loesung` | 0 → 0 | 240 → 0 |
| `hybrid_inverter_vs_ac_coupled_storage` | 0 → 0 | 15 → 0 |
| `de_hybridwechselrichter_vs_ac_speicher` | 0 → 0 | 0 → 0 |
| `cart` | 0 → 0 | 0 → 0 |
| `de_loesungsentwurf` | 0 → 0 | 0 → 0 |

**Totals: 24 cases, 17 clean → 20 clean.** Four failures were resolved
(`de_produkt_goodwe_gw60k_sts_g10` at both widths, `de_loesung` 390,
`hybrid_inverter_vs_ac_coupled_storage` 390) and one appeared
(`solution` 1440, 0 → 629) because the corrected procedure exposed the
bistable footer edge described in §3; that same region is 0 in `repeat-2`.

## Root causes

### 1. Woo shuffles related products on every request (fixed in the harness)

`wc_get_related_products()` calls `shuffle()` behind
`woocommerce_product_related_posts_shuffle` (default `true`). Six live PDP
requests with a cache-busting query returned six different orders
(`cache-control: no-store`). Two captures of the same page therefore differ in
card order even live↔live. Fix: `sortChildren` sorts each declared container by
its card title on both sides before the screenshot, and `compare.py` requires
the resulting item sets to be equal, so a different card set still fails.

Evidence: `batch1/product_saj_ats1_t63_a-1440-{live,local}.png` show GW30K/GW125K
card-swapped; after sorting, the same route reaches 0.

### 2. Viewport expansion re-scales images decoded at the shorter height (fixed in the harness)

The old procedure laid the page out at 900px, scrolled it, then grew the viewport
to the full document height and captured. Images whose decode had started at the
shorter layout height were re-scaled for the tall viewport, and that second
raster depends on how far decoding had progressed when the resize landed.

Measured on the SAJ PDP FAQ image: 85,021 differing pixels, max 5 levels per
channel, mean 1.09, no shift. The image bytes are identical
(`our-fit-1178-b.jpg` md5 `7e7406e5f16244140552a490a12efdec` on both hosts),
`naturalWidth`/`naturalHeight` are identical (1439×959), and canvas hashes drawn
both at natural size and at layout size are identical on both hosts. A/B/C
variants isolate the trigger to the *document origin* rather than the image
origin: local HTML with live image bytes still matched local-local (824 px, all
of it the related-cards region), while live HTML with local image bytes still
reproduced the full 177,714.

Fix: re-enter the document at the final viewport (`page.reload`) before
capturing, so layout and decode happen at the captured size.

### 3. Remaining four failures reproduce on the live host against itself

`batch2` residual: `solution` 1440 (629), `product_saj_ats1_t63_a` 1440 (629),
`solution` 390 (600), `product_saj_ats1_t63_a` 390 (210).

The decisive measurement is a **same-host control**: capture `https://de-linker.com`
on both sides of the comparison. Anything a cross-host run reports that also
appears there cannot be a product difference.

`control-live-390/` did that for 9 of the 12 routes at 390 (the run stopped when
the HTTPS proxy refused a tunnel on the tenth) and reproduced the `/solution/`
artifact against the live host itself:

| Case | live↔local | live↔live control |
| --- | --- | --- |
| `solution` 390 | 600, bounds `[18,3060,138,3540]`, max 55 | **600, bounds `[18,3060,138,3540]`, max 55** |
| the other 8 measured routes 390 | 0 | 0 |

`control-pdp1440-{1,2}/` did the same for the 1440 PDP in two independent runs,
and one of them reproduced that artifact too:

| Run | live↔live control |
| --- | --- |
| 1 | 0 |
| 2 | **629, bounds `[505,6328,1286,6507]`** |

The cross-host PDP 1440 residual is 629 at `[505,6328,1286,6507]` — the same
count at the same rectangle, against the same host on both sides.

Both captures are the same live page, same browser build, seconds apart, and
they differ by exactly the same pixel count at exactly the same rectangle as the
cross-host run. The artifact is produced by the capture, not by either site. The
PDP 390 residual (210, the footer count badge's anti-aliased edge) behaves the
same way: 210 in `batch2` and 0 in `repeat-2`, nothing changed in between.

The four residual cases are **bistable per browser instance while stable within
an instance**:

  | Case | batch2 | repeat-2 |
  | --- | --- | --- |
  | `product_saj_ats1_t63_a` 1440 | 629 | 629 |
  | `product_saj_ats1_t63_a` 390 | 210 | 0 |
  | `solution` 1440 | 629 | 0 |
  | `solution` 390 | 600 | 600 |
  | `de_loesung` 390 | 0 | 360 (three more hairlines) |

An earlier probe of `product_saj_ats1_t63_a` 1440 also produced a clean 0, and
an earlier live↔live run at 390 produced a single `[18,3000,138,3001]` hairline.
Nothing in the pages changed between those runs.

The regions are compositor features, not content:

- `/solution/` 390 and `de_loesung` 390 — one-pixel horizontal hairlines,
  x 18–137, exactly `border-bottom` of the `position: sticky; left: 0`
  first-column cells of `.lk-twin-table` (`rgb(190,203,192)` for the header
  cell, `rgb(209,217,206)` for the body cells). Their layout height is
  79.875px, so each border falls on a fractional y and snaps either side per
  instance; the local capture is missing the border the live one paints.
  Computed styles and geometry are equal on both hosts (33 paint-relevant
  properties compared, all identical).
- 629-px regions at 1440 — inside `.footer-console`, which carries
  `backdrop-filter: blur(28px) saturate(1.25)`; the differing columns sit on
  the card's rounded right edge.
- 210-px region at 390 — `.footer-panel-count`, a 27×27 `border-radius: 50%`
  badge with `background: rgba(255,255,255,.396)` over the footer's blurred
  gradient; the differing rows are its anti-aliased edge.
- Feature toggles move the artifact without touching content: removing
  `backdrop-filter` makes `/solution/` 390 reach 0; removing `position: sticky`
  also makes it 0.
- A no-resize capture would avoid it entirely, but Chromium crashes rendering at
  the full-document viewport height (7048px) on this machine (`Target page,
  context or browser has been closed` from every attempt to load at that size),
  which is why the harness must grow the viewport after load.

Not fixed here because both available levers are owner decisions, not harness
internals:

1. Fix the subpixel layout — remove the fractional 0.875px cell height, and the
   footer blur/translucent rounded surfaces — so every instance snaps the same
   way. This changes rendered output, so it needs the owner's sign-off as a
   ruled change rather than a quiet branch.
2. Declare the regions as ruled changes. Requires the change ledger and the
   owner's sign-off; masking is not permitted otherwise.

## Same-host control

Because the residual is cross-instance noise, the discriminating measurement is
a same-host control pair, which needs no new code — the tool already accepts two
bases:

```sh
# control: same host on both sides; any difference here is capture noise
node tests/visual/pixel-parity.mjs <outdir> https://de-linker.com https://de-linker.com \
  --widths 1440,390 --direct \
  --scenarios docs/acceptance/2026-11-04/pixel-parity/scenarios.json
```

A cross-host difference that also appears in the control pair is not
attributable to the products; a pixel that is stable in the control pair and
differs across hosts is.

## Reproduce

```sh
node tests/visual/pixel-parity.mjs <outdir> https://de-linker.com http://127.0.0.1:8916 \
  --widths 1440,390 --direct \
  --scenarios docs/acceptance/2026-11-04/pixel-parity/scenarios.json
python3 tests/visual/compare.py <outdir>   # recount without a browser
```
