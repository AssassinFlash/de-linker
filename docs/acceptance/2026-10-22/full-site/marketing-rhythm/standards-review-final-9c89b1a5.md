# Marketing rhythm 9c89b1a5 — independent Standards review

2026-10-22. **SOURCE BLOCKED: one P2 hover/focus combination defect.** The 12 saved CTA views pass their bounded visual check. Header runtime acceptance remains open; the unrefreshed header captures are rejected evidence, not proof that this source ran.

Reviewed against `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`. During the source read both byte counts/SHA-256 and the manifest's declared `path + NUL + SHA256 + LF` aggregation were independently verified:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | 3921 | `7357cfbcc59b6450a47fbb3f577f202ec2bc27803ea2db40a06ea5be3d2ca5c3` |

Aggregate: `9c89b1a5b425cb684342175ec7d7f744ddf35724059d597bb7f512ea33547c8d`. A later attempted source-copy step correctly refused the changed working-tree manifest; it was not treated as this reviewed candidate. Earlier reports remain unchanged. No source, build, browser, instance or production action was performed by this review.

## P2: inset white focus is invisible on the existing light hover background

`marketing-rhythm.css` adds `outline-color:#fff; outline-offset:-3px` to the photo-state language half's `:focus-visible`. But unchanged `chrome.css:188` sets the same half's `:hover` background to `--proto-neutral-50` (`#f7f8f8`) and forces dark text. On a simultaneously hovered and keyboard-focused half, the white outline is now inside that light child background: approximately **1.064:1** contrast. The dark parent rail cannot provide contrast for this inset line. This is a specific cascade/contrast defect, not a conclusion drawn from the stale header screenshots.

The narrow repair is `outline-color:currentColor`: normal photo state inherits white; hover inherits the existing dark text. That preserves the native focus geometry and avoids another duplicated state selector. This finding was sent to parent before this report; a subsequent source requires its own hash-bound verdict.

## Other source findings

The `#lc-header:has(#tv-mobile-panel[data-open="true"])` state uses the actual existing `header-menu.js::setPanel()` attribute, without changing disclosure behavior or ARIA. Its added ID specificity beats page-level photographic color/filter rules and restores one white surface with original-color logo, dark search/close/navigation and white-on-teal CTA. It does not force the panel visible, change geometry, or mutate the closed photo state. An unconditional media wrapper is unnecessary: existing `fit()` closes the panel when desktop navigation is visible and supports a folded navigation at wider widths. No new script, PHP design, snippet or style pipeline is introduced. The prior three-root CTA rules are unchanged. No other concrete source blocker was found.

## Twelve original CTA images inspected

Every `final-{installer,services,application}-{en,de}-{1440,390}.jpg` in `cua-local-20261022T0602/` was individually opened, and all 12 corresponding JSON files were read. The views were captured at 06:25 UTC from the earlier b278 CTA rules; those rules are unchanged here, but these images do not establish that the new header rules executed.

All 12 readbacks show two intact 14px action labels, 48px links, 12px action gap, 32px preceding-content gap and no horizontal overflow. Phone groups are full-width columns. Both desktop Installer/Services pairs remain aligned; the German Application desktop labels naturally form two rows with the same spacing and retain full text. Primary/secondary hierarchy remains clear, with no collisions, clipping of controls or empty third service-grid item. The screenshots are deliberately scrolled to the CTA: several Installer/Services headings extend above the sticky header, so these frames do not prove complete-heading visibility or section-top scroll alignment. Services/Application read back the actual preceding paragraph at 16px/26.4px; Installer's common probe reads a wrapper DIV, so that particular metric is not misreported as its paragraph measurement.

Exact image/JSON SHA readback is retained at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-standards-cta-20261022T063559751072Z/cta-evidence-readback.json`. Final successfully compiled photo top/scrolled/menu/focus views, compiled-source identity, intermediate widths/admin state and production readback remain separate gates. This review makes no whole-site visual or release claim.
