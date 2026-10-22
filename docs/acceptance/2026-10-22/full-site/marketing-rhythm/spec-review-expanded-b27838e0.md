# Expanded marketing CSS — independent Spec review

**Source-level bounded PASS; final runtime/visual acceptance pending.** Reviewed on 2026-10-22 against `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`. The declared two-source manifest aggregate is `b27838e0a28be5ae6d5f601e37eb432a2a7f95561c2f8b65fe1d383562755e32`. Both file SHA-256 values were independently verified, and the exact two bytesets plus manifest were copied into the reviewer-owned directory `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/marketing-spec-b278-sfmai_yo/` before further producer work.

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `63e6e9ef602dc5bfbbabdada8d7544b10771fb3b8b62d8528f3d4e53af757ea3` |

Only this report was written. No implementation, tracked tests, browser, instance, build, or production was changed by the reviewer. The earlier Installer-only report remains unchanged and does not establish acceptance of the expanded compiled stylesheet.

## Source scope and behavior

The chrome change remains exactly the earlier one-rule default-header repair: opaque white background and removal of backdrop blur. Positioning, admin offsets, sizes, links, and menu logic are untouched. This is a deliberate global default change, so evidence from Installer alone cannot establish every page’s header state.

The new stylesheet keeps the already reviewed Installer footer rules and adds presentation rules for the existing Service `#service-redesign #start` and Application `#tv-solution-v1 #contact` action groups. The two-ID specificity addresses their saved page-style cascade. These rules change native anchor presentation, not destination or submission behavior: body 16px/1.65, installed paragraph/action spacing token, 12px action gap, 14px complete button labels, 48px minimum height, flex wrapping, and a full-width column below 640px. Buttons grow naturally for long German labels instead of fixed-height clipping. Focus remains the existing 2px site ring with offset. The Application outline gets all four borders; Service’s extraneous direct `br` no longer becomes a mobile flex/grid item. PHP, LC content, prose, hrefs, IDs, input values, and JavaScript are not changed in this two-file delta.

Two selectors are intentionally page-root-wide rather than subsection-wide: `#service-redesign .lk-cta-actions > br` and `#tv-solution-v1 .lk-cta-actions > .lk-btn-outline`. This broader spelling was queried rather than assumed harmless. The producer’s actual published-page inventory, independently read from `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-action-source-inventory.txt`, identifies 10 pages/five EN/DE pairs and one action group per page. Service IDs 2748/6700 have the `service-redesign/start` ancestors; Application 746/6871 have `tv-solution-v1/contact`. Installer is 826/6869; Capability 874/6919 and Thank You 623/6873 have other roots and do not match these new Service/Application rules. There is no demonstrated additional current match. A future additional action group within either page root would share the corresponding `br`/outline treatment; this is the actual source boundary, not a claim that every selector includes `#start` or `#contact`.

## Photo language controls

The new language-rail rules require `body.rs-at-cover` or `body.cs-at-cover` and the actual `#tv-header-v2` control classes. White text has a solid dark-green surface rather than relying on the current photograph. The active underline follows `currentColor`, including the existing light-background/dark-text hover state. Each language half retains its pre-existing 44×44px hit box and native link semantics. The existing chrome focus declaration supplies 2px solid outline plus 2px offset; the cover override changes its color to white. No language is hidden or made inert by this CSS. The page’s existing cover-header transparency and scroll-state logic are not replaced by PHP or a new class producer.

The source therefore addresses the reported contrast problem without changing link targets, language routing, hero content, or navigation state. Actual cover/top, scrolled, hover, keyboard focus, and open mobile-menu colors still require computed and visual evidence. In particular, outline visibility against the photograph cannot be guaranteed from the white outline declaration alone.

## Evidence and acceptance boundary

The saved `final-services-en-1440.json` was read: it reports row flex, 12px action gap, 32px paragraph gap, 16px/26.4px body, 14px buttons, 48px link heights, hidden direct `br`, loaded fonts, no admin bar, and no horizontal overflow. This is one local computed observation; it is not the final 12-view matrix or a browser verdict by this reviewer.

The producer’s `compile3-rejected-*` captures are historical rejected cascade evidence and are not accepted results. At this report’s source-review stage, the final post-format/compile Installer/Service/Application EN/DE × 1440/390 images, their actual compiled version, and the photo/menu consumer evidence have not all been delivered for independent visual inspection. Consequently this report does not grant expanded visual PASS, actual destination-arrival PASS, photo-header PASS, production PASS, or full-site PASS. The earlier seven-image Installer review remains valid for that earlier local batch only.

No concrete source-level Spec blocker was found in these exact two files. The user has authorized visual bug improvements, and the implementation stays within existing WindPress presentation and native-link behavior. Expanded visual acceptance must be added only after the final runtime captures are actually inspected; a successful compilation or numeric geometry alone does not close that gate.
