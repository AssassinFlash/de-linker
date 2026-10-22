# Hero backdrop source Standards review — d69083ae

Verdict: **SOURCE PASS, bounded to the new 23-line `hero-readability.css` and aggregate `d69083aefc946cc4884e17d2774d9b503661f5e39cb151388649423791748661`.** No actionable architecture, scope, cascade or interaction regression was found in this source delta. This is not a compiled-runtime, visual, full-hero interaction, all-text contrast or production PASS. The twelve after images and actual native readback are separate acceptance evidence.

## Exact source independently checked

I independently read and hashed all three files and recomputed the ordered `path + NUL + file SHA256 + LF` aggregate from `source-files.json`. All match; the first two are unchanged from the earlier d1 review.

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | 4549 | `710fb37175f4b157816880e151fd9796b0e5e68ae5c3408f71a75aa0ecc80139` |
| `plugins/linker-commerce/content/windpress/hero-readability.css` | 621 | `034942b7178f8bc986b90441baa61cc738cb6bd1a80646b0f01510f47d312654` |

Private fixed source/calculation evidence:
`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/hero-source-standards-20261022T075752700715Z/`.

No source, instance, dependencies or browser was changed by this reviewer. No build or production operation was run. I read the existing native publisher, the actual saved public page markup/CSS from the frozen production snapshot, the supplied before JSON and the contrast derivation, and independently recalculated the color composites. The prior actual image review already established the targeted visible weaknesses; it is not used as evidence of the new runtime.

## Architecture, scope and cascade

The file uses the existing WindPress publication mechanism. `Presentation/WindPressVolume.php::files()` discovers `content/windpress/*.css` (lines 195–197); `install()` copies the files and `import_from_entry()` appends plain imports to the existing volume entry. The new source introduces neither a named cascade layer nor another runtime stylesheet pipeline. Page structure stays in native LC markup; there is no PHP layout, inline design, snippet or new JavaScript.

The entire delta consists of two `background` declarations on three existing section pseudo-elements:

- EPC: `#tv-solutions-developers-v1 section.epc-cover::before`;
- Application: `#tv-solution-v1 section.sol-cover::before`;
- Residential: `#tv-rs-page-v1 section.lk-hero-cinematic::before`.

Each is tied to an existing page root and actual `section` class; there is no generic `section`, global `::before` or broad `.hero` selector. About, Commercial, Utility, the header/menu and later photographic sections are not matched. One shared declaration for the two existing identical EPC/Application cover modes is a direct CSS relationship, not a new abstraction or a concerning duplicated-code smell. No actionable Fowler heuristic finding was identified in this small delta.

I independently parsed all six frozen saved page contents (842/6867, 746/6871, 749/6923): each expected root and cover section occurs exactly once. The corresponding EN/DE style blocks are byte-identical within each pair. Their combined CSS hashes are:

| Family / IDs | Saved CSS SHA256 |
| --- | --- |
| EPC 842 / 6867 | `913ad0e3687ef045a937e2190a16ac84dd7397fe1627140f72568000d8b0c3af` |
| Application 746 / 6871 | `a834d53f5ec79253d41e91436b00b8cb6d3fa19c35ec1d101e3de508d6561432` |
| Residential 749 / 6923 | `259793be7d5045e99b00836ea88593e96ff876ed9d5d3557e1b507f7ef4ff41c` |

Frozen native source: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/local-render-root-cause-20261022T072224138583Z/production-different-published-pages.private.json`, independently verified SHA256 `14795610654ea37ad6043fddca078ba67fe0a636d076380fd6e7bd1af7aa408f`. No production fetch is implied by reading that file. The independent root/section count and content/style hashes are saved in `native-source-readback.json`, SHA256 `9f66ecef6f8c212568fc810cd161a98f5e0d84a28c2c77fc84c1b22a29542e8f`.

The relevant existing saved background rules use specificity `(1,1,1)` (root ID + class + pseudo-element), including Residential's later integrated-cover override. Adding the actual `section` type makes the new rules `(1,1,2)`. Existing lower-specificity media rules therefore do not restore the weak background after this declaration, and the result does not depend on which style tag comes last. No stronger/important final cover background rule or inline style was found on the targeted cover/contents in the frozen six pages. Their existing obsolete earlier hero variants are superseded by the final cover-specific rules; the new declaration overrides the active final background rather than reviving an old layout.

## Stacking, text opacity and native controls

The native cover structure already places the image at z-index 0, the full cover pseudo-element at 1, and the content frame/stage at 2. EPC/Application pseudo-elements already have `pointer-events:none`. Residential's content stage is also above its existing pseudo-element. The patch changes only the pseudo-element background; it does not change inset, width/height, display, position, z-index, pointer events, isolation, crop, typography, layout, links, native text fields or handlers.

In particular, the patch does **not** apply `opacity` to a parent hero. White titles, explanation text, CTA backgrounds, and Residential's white composer remain separate layers above the stronger image tint. The section and its relevant frame have no newly introduced opacity/filter/blend operation. There are no element-level inline styles within the three hero sections in the frozen native content. Existing cover text is opaque white except the pale `#eef8ff` EPC/Application eyebrow and the Residential white `.lk-hero-footnote` with `opacity:.9`; the latter must not be treated as opaque in the envelope.

The explicit 0.64 minimum layer is supported by the contrast-envelope derivation and the demonstrated bright-image defect. The 62%/60% plateau positions continue a dark reading backdrop before the already darker final stops; they do not create a transparent gap. The source comment's older 8%/22% minima are traceable to the actual saved gradients. This is a deliberate narrow visual adjustment under the user's visual-bug repair scope, not a copy/layout redesign.

## Independent lightest-background derivation

I calculated these values from the source RGBA colors, not by copying the supplied JSON results. For an image whose channels are within 0–255, an all-white image is the brightest input. At the initial 0.64-alpha plateau the composite is `0.64 × tint + 0.36 × white`. The later final stops have darker/equal tint channels and larger alpha; they do not introduce a brighter reading region than the initial plateau under this model.

| Source text model | Brightest composite RGB | Recomputed luminance contrast |
| --- | --- | ---: |
| EPC/Application opaque white | `(96.28,110.36,125.08)` | `5.1943085795:1` |
| EPC/Application opaque eyebrow `#eef8ff` | `(96.28,110.36,125.08)` | `4.8248669015:1` |
| Residential opaque white | `(100.12,110.36,107.8)` | `5.2436198108:1` |
| Residential existing .9-opacity white footnote, foreground composited again over that background | `(100.12,110.36,107.8)` | `4.6135929207:1` |

The mathematical values agree with the supplied opaque-text derivation; the independent foreground-alpha check also agrees with the existing .9 footnote. I additionally calculated .9/.92/.95 controls in private `independent-envelope.json` to guard against mistakenly claiming the pale badge would retain its opaque bound if made translucent. The current saved badge is not .9-opacity, so that hypothetical lower value is not a source blocker.

These are conditional lower bounds for the specified text and existing image/pseudo-element structure. They do not cover browser/ancestor opacity or blends not represented in the source model, another foreground color/state, text over a white composer, native placeholder/disabled/focus colors, or proof that this file was actually compiled and won the runtime cascade. A stronger scalar also does not prove the photograph remains useful. Final after images and actual computed backgrounds are still required.

## Remaining gates and honest scope

The parent reports native present and official Generate with a new cache, and has supplied twelve after pairs for a separate visual review. This SOURCE verdict does not rely on a clicked Generate button or assume the new cache is visible. The separate review must inspect all twelve before/after photographs at their actual viewports, confirm the new background, preserve useful photo detail and unchanged geometry, and check titles/eyebrows/descriptions/visible CTA/composer separation.

Known target-size findings remain open under the same overall user goal: Application's secondary link is reported by root as 28 px high / 12 px text (primary 45.5 px), and Residential prompt chips as 35.59 px / 11 px. These are neither introduced nor fixed by the backdrop file. They do not inherit a whole-hero interaction PASS from source tint or visual legibility. No broader full-site completion or production acceptance is claimed.
