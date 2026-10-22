# Photo header contrast — independent Standards source addendum

2026-10-22. **Narrow SOURCE PASS for `d1b740ea`; runtime acceptance is still pending.** No concrete Standards blocker found in this appended rule. The previous controls/geometry saved-view PASS must not be expanded to claim full small-navigation text contrast: a separate review sampled the bright Commercial photo at approximately 2.88–3.15:1 and identified a real remaining issue. Earlier independent reports stay unchanged; this addendum records that later evidence and its narrow repair.

Both files, sizes and the manifest's `path + NUL + SHA256 + LF` aggregate were independently verified against `d1b740ea801a440ba3a05ab60026a000ebfb06cd64484d53cb3467ee9fcd34e4`:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | 4549 | `710fb37175f4b157816880e151fd9796b0e5e68ae5c3408f71a75aa0ecc80139` |

Byte comparison with `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-8e-reviewed/` confirms unchanged chrome and a single appended CSS rule/comment. It requires an existing `[data-page]`, one of the six inventoried photo-state classes and the actual closed-mobile-panel condition. It changes only the existing inner header background to `rgba(21,53,47,.8)`. It neither toggles the photo state nor changes layout, assets, text, URLs, disclosure behavior or the existing language/focus/CTA rules. The matching header IDs give sufficient specificity over the earlier transparent inner surface; no `!important` is introduced.

The `:not(:has(#tv-mobile-panel[data-open="true"]))` exclusion preserves the existing open white mobile panel and its dark controls. When the photo class is removed after scrolling, the new rule stops matching and the opaque default header remains in charge. Desktop mega-menus can remain open over a photo because their own surface is white while the small header navigation benefits from the new dark surface. This follows the existing LC/WindPress ownership and requires no PHP, snippet or JS state duplication.

The alpha value has a direct worst-case contrast interpretation: over a fully white photograph, the composited surface is approximately RGB `(67.8,93.4,88.6)`; white text is approximately **7.08:1**. Darker photo pixels increase that ratio. This source calculation supports the intended correction but does not replace computed-color, ancestor opacity, image and actual render checks. The photograph still contributes 20% to the surface.

The parent's new compile-8c/source identity and six-family EN/DE desktop/mobile images must establish that this rule executed and that menu/top/scrolled/hover-focus transitions remain correct. None of the old 53 captures is relabelled as an after-image for this new background. This review performed no browser, build, instance, source mutation or production operation; this new report is its only repository edit.
