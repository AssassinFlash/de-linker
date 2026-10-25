# Preserve the site fonts while reducing their transfer size

The full-site loading goal includes measuring actual browser loading, keeping EN/DE presentation and functional consumers intact. The current WindPress tokens serve four Plus Jakarta Sans weights and DM Serif Display as full TTF files. Convert those same files to WOFF2 containers and place each first in its existing native `@font-face` source list, with the unchanged TTF as fallback. Keep family, style, weight, display policy, every glyph, original fonts and both OFL files. No preload, new font, subsetting, theme change or script loader.

## Native ownership

All five source lists remain in `content/windpress/tokens.css`, installed by `present` and compiled by the official WindPress Generate control. The only PHP adjustment is file validation: `Tokens::fonts()` must inspect both URLs so `present` requires primary and fallback assets before writes. Its existing unit test now checks all ten files, the same design tokens and their intentionally updated normalized hash. No PHP layout or styling decision is introduced.

## Reproduction and evidence

The isolated worktree starts at `8f3d8e3921dc0d71fb11d76d0576988736ca23a3`; instance `font_transfer_format`, port9380, has the complete `20261022-0018` snapshot and no model or engine services. Before changes, a local full SQL export and affected source backups were saved under `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/font-transfer-format-20261022T2000Z/`. The five original fonts and both licences were separately backed up in the preceding `font-format-probe-20261022T1930Z/` directory.

Conversion uses fonttools4.67.0 with Brotli1.2.1 from the official package registry, `TTFont(source, recalcBBoxes=False, recalcTimestamp=False)`, `font.flavor = 'woff2'`, then `font.save(destination)`. Private `probe.py` records all source/output hashes and verifies glyph order, cmap, horizontal metrics, flattened coordinates, contour endpoints, flags and per-glyph instructions for every glyph. Head differences are confined to checksum and the2048 flag bit; glyph-location offsets can differ. These structural comparisons do not replace rendered acceptance.

File bytes fall by58.01–65.01%, before transport compression. Direct ordinary public GETs show that production already compresses its TTF responses; do not describe the offline percentage as production bandwidth or speed improvement.

The first anonymous benchmark used localhost while compiled CSS/font URLs were127.0.0.1. Native events proved four CORS font failures and extension-provided Inter fallback, despite `document.fonts.status` being loaded. Those runs are rejected and retained. Accepted A-v4/B-v4 use the registered127 origin, native four200 font responses, zero font failures and platform-font readback on actual text consumers. Legal h1 uses an Inter-based stack; successful Plus requests do not establish its rendered font. Existing UI candidates using localhost require separate font-sensitive revalidation.

## Acceptance boundaries

For each format, measure exactly three rounds of EN/DE Privacy at1440×1000 and390×844, cache disabled,100ms latency,524288bytes/s down and262144bytes/s up, no CPU throttling. Retain all slow samples and original lifecycle/network events per main Document loader. Preserve native platform-font readbacks and raw image pairs; compare formatting/geometry and exact unprocessed image pixels. Record a return to original CSS before restoring the final candidate and official cache.

Separately prove native fallback after an isolated primary-resource failure and the installer rejection of missing font files before any presentation writes. No production submissions, registrations, mail or model calls. No production writes by this worktree.

This is a local candidate. PHP static transport differs from production compression, and browser extensions remain present. Local FCP/load and resource changes are bounded results, not production Core Web Vitals or whole-site completion. Final independent review, exact-head CI, combined publication and production readback remain required. Revert the three text-file changes, remove only the five new WOFF2 files, then run native present/Generate/readback to restore original delivery; original font files and licences remain available throughout.


## Bounded current-source delivery

This prepared correction is delivered with the font, product-phone and library
patches in one batch based on accepted source18c85c31 (production589). The
PDP contribution carries only pdp.css and its specification; old header code
from its original branch is excluded. Current header, authentication, legal
and marketing content stay protected by the scoped publication readback.

Under AGENTS.md section0.1, reuse the accepted original fixtures and rendered
evidence for unchanged implementation, inputs and runtime conditions. Do not
replay the original complete matrix, fallback experiment or repeated font
benchmarks. Reuse exact font/glyph proofs after source/output hash checks;
perform only current-base integration, affected real browser controls and
public font resource/consumer readback. Record actual production compressed
bytes separately from offline file savings; do not claim a Core Web Vitals or
whole-site speed result from this batch. All newly found unrelated gaps stay
in the existing full-site goal rather than expanding this release.
