# Marketing rhythm — final six-state source Standards review

2026-10-22. **Bounded SOURCE PASS for `8e054bad`; no actionable Standards blocker found.** The 41 successfully compiled Residential/Commercial header captures and 12 current CTA captures pass their bounded saved-view visual review. Newly added About/Utility/EPC/Application photo states still require their own successfully compiled runtime evidence. No whole-site or production acceptance is asserted.

## Exact source and history boundary

Baseline: `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`. The two source byte counts, SHA-256 values and declared `path + NUL + SHA256 + LF` aggregation were independently verified:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | 4161 | `ef1ea27f2ea50c066d1379bf10a2145c3274ec3d9ea90305da1ad9a6cfa44578` |

Aggregate: `8e054badeb1cfe56443ef55f73eebb0db2937b45028ff920ae9c1b839bf3878d`. The intermediate `80317c23` was independently checked against the exact `marketing-rhythm-894-reviewed/` copy: only three photo-language selectors added `.about-at-scene`, plus formatting; chrome stayed identical. The final source was compared with the exact `marketing-rhythm-803-reviewed/` copy: those same three lists add `.us-at-cover`, `.epc-at-cover`, `.sol-at-cover`, plus formatting. No other rule changes. Intermediate 803 marketing SHA was `743fe4d4b8778eff9da4755b03b7c2e15a6cd174d4c7b595a21297a6dc4c9e24`; this records its readback without mislabelling later source as 803. Earlier reports and rejected cache images remain unchanged.

The parent's native published-page inventory at `marketing-header-and-local-service-raw-inventory.json` was read locally; all six actual photo-state classes occur. This supports a finite inventory-based extension rather than invented future selectors. The new lists retain the same specificity, native state dependency and `#tv-header-v2` boundary. Header transparency, page composition, text, destinations, disclosure JS and inactive/scrolled behavior are untouched. The prior LC/WindPress placement, native `data-open` menu adapter and `currentColor` inset-focus findings remain valid. No PHP design, snippet or second CSS pipeline is introduced.

## Original images individually inspected

All following JPEGs in `cua-local-20261022T0602/` were individually opened and their corresponding JSON read; this is inspection of parent-run evidence, not a browser run by this reviewer:

| Group | Exact saved-view coverage | Finding |
| --- | --- | --- |
| `current-{installer,services,application}-{en,de}-{1440,390}` | 12 views, new complete-heading framing | Complete headings and both action labels are readable; no control clipping/collision. Natural German Application desktop wrapping retains both full labels. Phone buttons form full-width columns. All readbacks retain 48px links, 14px labels, 12px action gap, 32px preceding gap and no horizontal overflow. Installer's shared `previous` probe is a wrapper DIV, so it is not presented as a paragraph line-height measurement. |
| `final-header-residential-{en,de}-1440-{top,menu,hover-focus,scrolled}` | 8 views | Transparent white photo navigation, readable desktop menu, stable dark language surface, visible dark inset hover/focus outline and opaque white scrolled header. |
| `final-header-residential-{en,de}-390-{top,menu,closed,language-focus,hover-focus,scrolled}` | 12 views | The expanded white menu has visible original-color logo, search/menu control, dark links and filled contact action; closing restores the photo header. Normal focus remains white inside the dark rail; simultaneous hover/focus becomes dark inside the light half. |
| `final-header-commercial-{en,de}-1440-{top,menu,hover-focus,scrolled}` | 8 views | The same states remain readable over the brighter commercial photo; no unexpected header collision or content showing through the white scrolled surface. |
| `final-header-commercial-{en,de}-390-{top,menu,closed,language-focus,hover-focus,scrolled}`, plus DE `escape-closed` | 13 views | Menu surface/controls remain visible; recorded close/Escape frames restore the photo styling. Focus and hover/focus are visibly distinct and fit the 44px language controls. |

All 41 header readbacks report loaded fonts and no horizontal overflow. Thirty-eight declare the actual compiled CSS URI version `1792651246`; three earlier records omit the CSS list, so this review does not fabricate a per-response identity field for them. Menu/scroll/focus computed states and their original images corroborate the fixed behavior. The parent's successful compile-7 store/index/network/cache readback is separate execution provenance; these screenshots exercise the 894 rules, which remain byte-identical in the final expanded source.

The old `current-header-about-en-1440-top.jpg` was also inspected: dark language text sits directly on the photograph. It is a valid before-example for the extension, not an after-PASS. Actual browser text and focus colors in the Residential/Commercial captures match the source correction: white-on-dark language text about 13.27:1 and dark-on-light hover/focus about 18.09:1. No stale rejected cache image or Generate-button click is used as evidence that a rule executed.

## Evidence retained and remaining gates

Exact final source copies, manifest and all 53 inspected JPEG/JSON hashes are retained at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-standards-8e-20261022T065442403559Z/`; `inspected-53-artifacts.json` SHA is `f950314503349139c37cb4781295c4c1fbb83632554a09da896f000ce2930c48`.

Final compiled-source/version readback and EN/DE × 1440/390 evidence for newly added About/Utility/EPC/Application photo headers remain open, together with any separately requested intermediate-width/admin-bar and production checks. The finite saved-view PASS above does not establish every page or downstream destination interaction. This reviewer changed only this new report; no product source, build, browser, instance or production operation was performed.
