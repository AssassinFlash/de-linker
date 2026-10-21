# Marketing entry and document library — production readback

Production release `20261021T220117023196Z-d27f3dc3` (PR 524, merge `d27f3dc35126cd037db8f98f53da137cacbc52df`). Both PR CI and main CI passed. The retained database snapshot before deployment is 7,078,509 bytes; SHA-256 `068523dfe6eb312e6076b3f1d87c7f5171256d974e36730fd041d700d53fa09a`. The preceding atomic release remains available for code rollback. Production readback before and after the browser cases matched all 1,151 deployed package files and nine switched filesystem identities. WindPress native cache was 701,525 bytes, SHA-256 `4d6074dd98f7bd580671ddda12a60b35896d1b4a5449ae27bb5a8799c4320a3a`, with no reported cache defect. Full English and German privacy post-content hashes remain unchanged, with 29 backslashes each. See runtime-after-browser.json.

## Actual browser observations

The browser cases used the actual deployed native pages and shipped marketing/Genie/library scripts, with no model, speech, history or network mocks. Viewports were Chromium 1440×1000 and 390×1000; phone here means a responsive desktop-browser viewport, not a physical handset. The existing guest conversation was preserved. Only the task's own newly typed, unsent questions were cleared after capture. No new model turn, recording, file upload, inquiry, registration or mail was sent during these cases.

- Residential storage: EN/DE ×1440/390, four source-question→Voice input handoffs. Exact text and multiline questions remained in the real mounted composer. Source cleared only after acknowledgement. Dictate remained off and required its own action.
- Commercial storage: the same four states, complete text retained; source attachment and voice targets measured 44×44. Desktop helper remained nonmodal; phone used an aria-modal dialog, inert background and body scroll lock.
- Installer: EN/DE at390, two source-question→Voice input handoffs, exact text retained and explicit Dictate only. Desktop project planning remains outside this batch.
- Each of these ten own questions was cleared before closing. Escape/Close restored the source voice focus in observed residential/commercial/installer states. The per-state JSON and original screenshots bind the actual route, language, viewport and loaded script URLs. Earlier residential JSON used a source-control selector that returned an empty array; do not treat those arrays as size measurements. Later records use the actual aria-labelled controls.
- Library: EN/DE ×1440/390 AIO3 document searches all produced the three actual files with completed, nonzero-width, opacity-1 images, named download actions, and no page overflow. The German390 initial record shows a viewport failure described below; `manual-scroll` is only the subsequent manually corrected view. It does not erase that failure.
- Library search suggestion ArrowDown→Enter focused and expanded the named AIO3 FAQ summary in all four language/viewport combinations. Tab reached the visible product/source link; native EcoFlow next-page actions focused the new first summary and updated Previous/Next availability. All 228 product-specific FAQ summaries had nonempty product context in these observed pages. These focus checks do not establish correct active-category navigation.
- The actual German library download action returned the English AIO3 datasheet, 1,140,362 bytes, one PDF page, SHA-256 `1833312ad717e11d5fea900948ef7ac84446065af17d50565c9c2b42e4494ab1`. The English file language was explicitly shown to the customer.

## Failures and remaining boundaries

Early native Documents activation before enhancement can leave `#linker-library-panel-documents` in the URL while FAQ remains selected after enhancement. A second enhanced click works; this is not acceptance of the early path. The actual observation is retained in library-de-1440-early-tab-race.json.

Switching from deep FAQ/paging to a short document search can leave the viewport at the footer. library-de-390-doc-search.json records all three result rows above the viewport (the final row bottom78.74 is under the header). The manual-scroll screenshot is supplementary, not an automatic-positioning PASS.

Some screenshot shallow-gray navigation backgrounds initially looked like an incorrect selected brand. Independent source review identified that gray background as a hover style; these frames alone do not prove an incorrect aria-current. A separately controlled actual-script consumer does reproduce hidden-panel scrollspy pollution. The production focus records did not collect .is-active/aria-current, so do not use them as semantic active-category evidence. The navigation continuity repair and new regressions remain open.

Residential/commercial source textareas still need explicit accessible names. The installer source has an associated label despite aria-label=null. Photo-header language contrast and hero eyebrow/navigation overlap also remain global visual review items; do not claim full-page acceptance from the handoff captures.

No physical microphone, physical handset, new production model answer, all library files, full marketing page content, all templates or full-site chain acceptance is established by this readback. The whole-site goal remains active.

Screenshots in this CUA batch retain the original tool bytes. Several have a .png filename but native JPEG encoding; no image conversion, cropping or pixel editing was performed.
