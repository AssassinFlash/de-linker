# Closed photo-header surface — independent Spec delta

**Narrow source PASS; final runtime/visual acceptance PENDING.** This review does not overwrite the 8e report or close its observed commercial low-contrast state using source alone.

Aggregate `d1b740ea801a440ba3a05ab60026a000ebfb06cd64484d53cb3467ee9fcd34e4` and both file SHA-256 values were independently verified with the manifest’s `path + NUL + SHA256 + LF` algorithm. Base remains `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`.

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `710fb37175f4b157816880e151fd9796b0e5e68ae5c3408f71a75aa0ecc80139` |

The exact 8e copy at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-8e-reviewed/` was directly compared. The only delta appends a background declaration on the header’s inner `#tv-header-v2`, requiring `body[data-page]` and one of the six demonstrated photo-state classes. It explicitly excludes a header containing the open native mobile panel. All previous declarations, CTA rules, focus/current-language states, native links, content, dimensions, and events are unchanged. Reviewer copies are in `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/marketing-spec-d1b7-kw0t_lk2/`.

A dark background color with alpha changes the background only; it does not reduce text/icon opacity. The proposed `rgba(21,53,47,.8)` preserves a visible photographic contribution while stabilizing the white foreground. Even compositing over an all-white photo gives approximately RGB `(67.8,93.4,88.6)` and a nominal white-to-background contrast around 7:1. This analytic bound is a source check, not an actual rendered contrast measurement. The open mobile panel remains on the already reviewed white-surface/original-logo/dark-control path. When the photo-state class is removed, the new rule no longer matches and the opaque default header remains responsible for the scrolled state. Desktop mega-menu markup and its own panel background are untouched.

This is a focused WindPress remedy for the observed pale small navigation over the commercial photo and is within the authorized visual-bug repair. No source-level scope or behavior blocker was found. Before runtime PASS, the actual compiled CSS must be read back and all six families checked in EN/DE at 1440/390, including cover/hover-focus, mobile open/close, and scrolled states. The previous 894 captures cannot prove this appended declaration is active. This reviewer ran no browser, instance, build, production operation or new runtime test, and wrote only this report.
