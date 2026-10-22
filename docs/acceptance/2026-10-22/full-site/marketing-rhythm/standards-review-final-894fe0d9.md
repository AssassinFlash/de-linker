# Marketing focus correction — independent Standards addendum

2026-10-22. **Narrow SOURCE PASS: the confirmed 9c89 hover/focus defect is closed in source.** No new Standards blocker found in this one-line delta. This report does not approve execution of the new stylesheet: the official cache generation has not yet been established as successful, and header visual acceptance remains open.

The exact old files and original manifest at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/marketing-rhythm-9c89-rejected/` were independently read and SHA-checked. Both current file sizes/SHA-256 and the declared `path + NUL + SHA256 + LF` algorithm match the new manifest, aggregate `894fe0d987d24085a160512c501bc34936ae4264209d30e3da5559534609f8e1`:

| Source | Bytes | SHA-256 |
| --- | ---: | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | 34623 | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | 3929 | `6a24c8eabc52ed559f28a84ddc5e968dbd0abb65b30e47086ec69680f13fdb2e` |

Byte comparison proves chrome is unchanged and marketing-rhythm differs from the exact 9c89 source only in `outline-color:#fff` becoming `outline-color:currentColor` on the photo-state language half's `:focus-visible`. Inset `-3px`, selectors, CTA rules, header menu state, breakpoints and every other byte are unchanged.

This resolves the identified combination correctly: normal photo-state text and its inset outline inherit white over the dark `#15352f` rail (approximately 13.27:1); a simultaneously hovered half inherits the existing forced dark `--proto-ink` text and consequently a dark outline over its existing light `--proto-neutral-50` background. It no longer draws a white line inside a light hover surface. `currentColor` preserves the original native CSS state machinery and needs no duplicate hover/focus selector. No source behavior or scope is added.

The previous 12 original CTA images remain bounded evidence for byte-identical CTA rules only. The old 9c89 BLOCKED report is retained as historical evidence; stale cache/header captures and a Generate button click are not converted into runtime PASS. A successful official compile with version/source readback, followed by actual photo top/scrolled/menu/hover+focus views, is still required. No browser, build, instance, product source or production operation was performed by this review; only this new document was written.
