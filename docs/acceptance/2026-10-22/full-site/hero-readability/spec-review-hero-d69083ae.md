# Source Spec review: photographic hero readability

Verdict: **SOURCE PASS, bounded to aggregate `d69083aefc946cc4884e17d2774d9b503661f5e39cb151388649423791748661`.** No actionable source blocker was found in the new hero overlay. Compiled runtime, final photographs, hover/focus/input behavior and full-page accessibility are pending the parent's separate acceptance. No instance operation, browser, compilation, deployment, product edit or test edit was performed by this reviewer.

## Exact source and scope

I independently hashed all three files and recomputed the manifest's ordered `path + NUL + SHA + LF` aggregate. Every byte count and SHA matches `source-files.json`:

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `710fb37175f4b157816880e151fd9796b0e5e68ae5c3408f71a75aa0ecc80139` |
| `plugins/linker-commerce/content/windpress/hero-readability.css` | `034942b7178f8bc986b90441baa61cc738cb6bd1a80646b0f01510f47d312654` |

The first two remain the previously reviewed `d1b740ea…` bytes. The added stylesheet contains two `background` declarations on three existing section `::before` selectors. Its only targeted roots are EPC `#tv-solutions-developers-v1`, Application `#tv-solution-v1`, and Residential `#tv-rs-page-v1`; it does not target Commercial, Utility, About, ordinary content, the header, or an open menu. Text, language, links, JavaScript, native control markup and page composition remain unchanged. The user's broader visual-bug authorization covers repairing this demonstrated photo/text readability defect without a marketing-copy rewrite or page redesign.

## Actual saved markup and cascade

I checked the six real EN/DE saved public page contents from the frozen production JSON. The prior independent post-alignment readback established that current local content matches these bytes under the three existing origin substitutions. Each new selector matches exactly one existing `section` in its own native root:

| Family | IDs | Existing section | Saved background rule |
| --- | --- | --- | --- |
| EPC | 842 / 6867 | `section.lk-hero-split.epc-cover` | `#tv-solutions-developers-v1 .epc-cover::before` |
| Application | 746 / 6871 | `section.lk-hero-sol.sol-cover` | `#tv-solution-v1 .sol-cover::before` |
| Residential | 749 / 6923 | `section.lk-hero-cinematic` | `#tv-rs-page-v1 .lk-hero-cinematic::before`, including the later integrated-hero override |

These are stylesheet rules inside saved `<style>` blocks, not element `style` attributes. Each old selector has specificity `(1,1,1)`; adding the actual `section` type gives the new selector `(1,1,2)`. No saved stronger or `!important` background override was found on these three pseudo-elements, including the saved media rules. Thus the override is not dependent on placing the compiled stylesheet after the saved inline style tag. The Residential later low-opacity rule is covered by the same specificity increase.

The existing volume publisher discovers `content/windpress/*.css` (`Presentation/WindPressVolume.php:196–197`) and adds plain `@import` lines without a named layer (`:78`). The new file uses no `@layer`. This is the correct existing WindPress publication seam; no PHP layout, snippet or second stylesheet pipeline is introduced. Actual published imports, compiler output and computed backgrounds still need the parent's native present/official-compile readback.

The existing covers already establish their pseudo-element at `z-index:1` over the photo at `z-index:0`, with the content frame/stage at `z-index:2`. EPC and Application already use `pointer-events:none` on the pseudo-element. The new rule changes no position, inset, display, z-index, pointer events, size, padding, border, image crop or content stacking. In particular, it changes the pseudo-element's background rather than applying `opacity` to the whole hero, so it does not fade its labels, CTA or white Residential composer. Photographs remain present under a translucent overlay; the visual change is a stronger tint and must still be judged in the final images.

## Independent contrast-envelope check

I independently recomputed the supplied alpha composite and sRGB luminance contrasts, without using the JSON's result as the calculation input. For an opaque image whose channels lie in `[0,255]`, the all-white image is the brightest possible background under these overlays. The first two stops retain the same color/alpha; the final stops have darker/equal channels and greater opacity, so they do not produce a brighter segment than the initial 0.64-alpha plateau.

| Modeled text | Brightest composite RGB | Recomputed contrast |
| --- | --- | ---: |
| EPC/Application opaque white | `(96.28, 110.36, 125.08)` | `5.1943085795:1` |
| Existing small EPC badge `#eef8ff` | `(96.28, 110.36, 125.08)` | `4.8248669015:1` |
| Residential opaque white | `(100.12, 110.36, 107.8)` | `5.2436198108:1` |

All three agree with `contrast-envelope.json` within numerical precision. Application's saved eyebrow also uses `#eef8ff`, so the same small-text envelope applies there. The saved Residential footnote has `opacity:.9`; independently compositing that white foreground against the same brightest modeled background gives `4.6135929207:1`. The latter is an extra source-level control, not a claim that every other translucent text/button state was measured.

These values are a conditional lower bound for the specified text against the existing image-plus-pseudo-element layer. They do not certify ancestor opacity/filter/blending, another overlapping layer, a compiled cascade that has not yet been read back, all button/placeholder states, or every text element on the page. The supplied JSON appropriately states that limitation. The final screenshot must also preserve useful photographic detail and control distinction; a passing scalar does not settle those visual questions.

## Before-state evidence read and runtime gate

I read all 12 before-state JSON records for the three families and four language/width combinations. They describe the old low-opacity gradients and complete headings at 1440/390, with fonts loaded and no recorded horizontal overflow. I also actually reopened the three German 390 original JPEGs listed below. EPC shows white headline/eyebrow across bright sky and equipment; Application's small explanation crosses pale container sides; Residential's explanation sits over the light cabinet. They support the repair target. They are before images and do not show the new overlay.

- `before-epc-de-390.jpg` — SHA-256 `d78fb683b2f60e37d70446d22d8d5bf92708cb3399c6247d64cc36e11b8bcfb5`.
- `before-application-de-390.jpg` — SHA-256 `7a5b0a8011804938190bec868a1b28f4b4f8c9b343dcd546f009042394430621`.
- `before-residential-de-390.jpg` — SHA-256 `80b3aadb049d168fd9350580f0ec65a7bede4c57efb5cb75371eacd3f132ee4b`.

The parent should accept the post-compile state only after the new `::before` background is visible in actual computed CSS for all six EN/DE pages at 1440/390, with the intended source/cache bytes recorded. Compare final and before photographs, heading/eyebrow/description readability, unchanged image framing and block geometry, native CTA contrast and pointer/focus behavior, and the Residential white composer/suggestions in their actual states. Existing small targets or other page findings are not fixed by this overlay and must not inherit a PASS from it. No all-page, all-hero or production PASS is issued here.
