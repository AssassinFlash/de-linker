# Photo language focus — independent Spec delta review

**Narrow source PASS. New-header runtime/visual acceptance remains PENDING.** Reviewed on 2026-10-22. This does not supersede the historical 9c89 report or the Standards runtime BLOCKED evidence.

Manifest aggregate `894fe0d987d24085a160512c501bc34936ae4264209d30e3da5559534609f8e1` was independently recomputed using the stated `path + NUL + file SHA256 + LF` algorithm in manifest order. Both source files match their manifest SHA values:

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `6a24c8eabc52ed559f28a84ddc5e968dbd0abb65b30e47086ec69680f13fdb2e` |

The exact installed 9c89 source copy at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-9c89-rejected/` was directly compared. Chrome is unchanged; the sole marketing-rhythm difference is the photo-language half’s `outline-color: #fff` becoming `outline-color: currentColor`. The `-3px` inset, 2px existing focus ring, selectors, language labels/hrefs/current-state underline, native 44×44px hit boxes, menu reset, CTA rules and all other bytes are unchanged. Reviewer source copies/manifest are at `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/marketing-spec-894f-4gbyoff_/`.

This closes the identified source cause of white focus on the hovered light surface: the existing `.lnk-lang-half:hover` declaration supplies dark ink with a light background, so `currentColor` makes its inset focus ring dark in that state. Without hover, the half inherits the cover rail’s white foreground over its solid dark-green background and keeps a white ring. The active underline already uses the same current-color mechanism. The change therefore preserves both state cues without changing text, navigation, focus order, or input behavior. No source-level Spec blocker is identified in this single-declaration delta.

This reviewer did not run a browser, instance, build, production operation or new runtime test. Only this report was written; prior source and reports were not changed. The producer’s compile6 was already rejected because the compiled cache did not advance. Its old header/menu/focus pictures do not prove this new source active or successful. Required runtime closure remains: actual compiled source readback and new EN/DE photo cover/scrolled/mobile-menu states, including keyboard focus with and without simultaneous hover. Earlier CTA visual observations remain scoped to their unchanged declarations; they do not imply the new-header gate or all-site acceptance has passed.
