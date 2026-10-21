# Library navigation continuity — read-only diagnosis

Status: three related customer-path defects are under repair. This document records source diagnosis, parent-supplied online observations and independent temporary DOM counterexamples. It is not an implementation, browser rerun, release or production-acceptance PASS. The reviewer changed only this document and temporary files outside the repository; no implementation, instance or browser was operated.

The inspected worktree is `/Users/chesterjohn/.codex/worktrees/marketing-library-release/de-linker`. The inspected `plugins/linker-commerce/assets/library-ui.js` SHA-256 is `778870429481e3d400c753e93a3e5947c2e81e3bb273a684a7f4a3986a307f27`. Line references below identify that source version. They must not be applied blindly to a subsequent repair.

## 1. Native tab choice is lost when enhancement starts

The parent's [library-de-1440-early-tab-race.json](library-de-1440-early-tab-race.json) records the actual online German URL ending in `#linker-library-panel-documents`, while the enhanced, searching page still selects FAQ for `AIO3`. The parent reports a second click after enhancement works and writes `?tab=documents`. The reviewer read this record; the online action was performed by the parent.

Both actual LC templates supply native anchors: `faq_page.html:23–24` and `de/faq_page.html:23–24` point to the FAQ/document panel IDs. Both panels are available before JavaScript. `LibraryPage::config()` enqueues the external script in the footer with `defer`, so a valid interval exists in which these anchors already work but enhancement has not executed.

The source mismatch is deterministic:

1. `tabFromSearch()` at lines 143–145 reads only `?tab=documents`.
2. `state.tab` at line 199 initializes from that search string, ignoring the native fragment.
3. `start()` at line 1117 applies that state and hides the other panel.
4. Only afterward, lines 1120–1124 read the fragment and attempt to scroll to it. They do not reconcile its owning panel or selected tab.

A native early click therefore leaves a valid document fragment, but enhancement defaults to FAQ and hides the very destination that was selected. Subsequent search correctly filters the wrong active half. This is a progressive-enhancement state-handoff bug, not evidence of corrupted document data or a broken German download link. The inverse also fails: a native FAQ click before enhancement cannot override a stale `?tab=documents` query.

### Minimal repair seam

Keep the current LC anchors and the complete no-JS page. Before enhancement hides a panel, resolve the current fragment to an element **inside this library**, find its containing `[data-library-panel]`, and use that native destination's tab. A recognized panel/descendant fragment should outrank a conflicting older query; otherwise retain the existing query/default behavior. Use `getElementById()` rather than interpolating an untrusted fragment into a selector. Unknown or outside-library fragments must not manufacture a tab.

Apply the chosen tab before scrolling. When normalizing to the existing enhanced `?tab=documents` convention, use the existing URL helper and `replaceState`, preserve unrelated parameters and the valid fragment, and avoid a reload or an extra history entry. A hard-coded German path, new PHP route or second content renderer is unnecessary. If hash/history navigation is included in the repair, use the same location resolver so native Back/Forward destinations cannot again point into an inactive panel.

## 2. Scrollspy can select a hidden card; focus is a separate result

The parent's German [FAQ-focus JSON](library-de-1440-faq-search-focus.json) establishes that the SAJ summary is focused and in the reading area. The corresponding screenshot visibly shows the SAJ answer and a pale GoodWe background in the left rail. This proves useful focus and an apparent navigation-indicator discrepancy, but the JSON does not record `.is-active` or `aria-current` on rail/chip links.

The screenshot alone does **not** establish that GoodWe is semantically current: `faq.css:128` gives a pale background to `:hover`, whereas line 129 gives `.is-active` a white background, heavier text and border/shadow. A stationary pointer can retain hover during a keyboard move. Final readback must inspect the actual active classes/ARIA and separate them from hover. The reviewer inspected the saved screenshot, not the live browser.

There is nevertheless a reproducible source defect in the classification mechanism:

- `markActive()` at lines 828–855 uses **no IntersectionObserver**. It scans every `[data-library-spy]` in the whole root.
- It does not exclude the hidden inactive panel or its descendants. A layout-hidden target's bounding box has `top=0`; that satisfies `top <= stickyOffset()+24`.
- Each later matching target replaces `current`, so an inactive document card can overwrite the actual visible FAQ card. The subsequent loop updates all rail/chip links, including hidden groups.
- Search/suggestion activation makes the problem reachable: `applySearch()` calls `markActive()`, and the suggestion then correctly focuses/scrolls its FAQ row at lines 772–777. Later scroll events repeat the same unfiltered scan. Correct summary focus does not repair the independent current-link calculation.

An independent consumer fixture reproduced SAJ summary focus with `aria-current="location"` on a hidden document-GoodWe link and **no current link in the visible FAQ rail**. That is the established controlled failure; the exact live GoodWe/EcoFlow attribute state still needs a browser DOM readback and must not be inferred solely from background color.

### Minimal repair seam

Restrict spy candidates to laid-out targets in the current visible source panel; reject hidden ancestors and zero-box targets. While showing the flat search list, original hidden-panel geometry must not select a source category. Apply the result consistently to the visible rail and mobile chips, clearing stale current markers. Preserve the existing card/zone IDs and native anchor destinations.

Explicit suggestion/anchor navigation can immediately name its known target card, then reconcile from eligible geometry as the programmatic scroll settles. Avoid permanently treating focus as scroll authority or adding an unrelated observer system: normal reading scroll must still update the current card. The final assertion is the actual visible current link/chip for SAJ, not merely that the summary received focus or some link has an active class.

## 3. A shorter result list can leave the viewport in the footer

The parent's [library-de-390-doc-search.json](library-de-390-doc-search.json) records Documents selected and three valid `AIO3` document rows, but their tops are approximately `-642`, `-399`, `-156` pixels and the last bottom is about `79` pixels. The screenshot shows the footer. The image readiness and lack of horizontal overflow in that record do not mean the documents are readable at the current scroll position.

The relevant source paths are:

- `setTab()` at lines 385–390 renders the search half and **returns early** when a query exists. It bypasses the `moved` branch at lines 392–404 that otherwise adjusts the reading position after a tab change.
- Merely removing that return is insufficient. The existing moved branch calculates `top = tabbar.getBoundingClientRect().top + scrollY - headerHeight`. While the bar is pinned, its top is approximately the measured header height, so this yields approximately the current scroll position; `scrollY > top + 8` then does not trigger. The sticky bar's current viewport box is not the original content position or the new result destination. Its containment/clamping near the footer is likewise not a reliable content anchor.
- `applySearch()` hides the full panels and `renderSearch()` replaces the result host, potentially collapsing a long page into a few rows. Neither path settles an off-screen result region after the layout change.
- Existing suggestion activation and pager actions already have explicit focus/scroll continuation, but the filtered-tab transition does not share it.

These omissions are consistent with the parent's measured failure. The exact browser scroll anchoring/clamping behavior is supplied online evidence, not something JSDOM can establish. The independent DOM fixture confirms that this explicit filtered-tab commit renders three documents without requesting any positioning; it does not claim real viewport geometry.

### Minimal repair seam

Run a common, bounded reading-position step after an explicit tab/search-result commit, including the search branch currently skipped by the early return. Target the new result/empty-state lead or selected panel, use the existing sticky measurement/scroll helper, and correct only when the relevant reading target is outside the usable area. Do not reset to page top, steal focus from a typing/IME input, or scroll on every keystroke when the result is already accessible.

Use a **non-sticky content target** for this step, rather than moving the old sticky-tabbar rectangle calculation into a shared branch. This requirement was sent directly to the implementing Spec reviewer after reading the narrow navigation-continuity design.

For tab activation, preserve normal tab focus while bringing the resulting content into view. For an explicit FAQ suggestion, preserve the existing focused summary and its source-link keyboard continuation. If settling is deferred to an animation frame, use the latest committed state and ignore superseded work; an older query must not scroll to a detached or newly hidden result. Reduced-motion behavior remains part of the existing helper contract. Measure a useful heading/action under the sticky stack rather than requiring an arbitrarily tall answer/card to fit the viewport.

## Independent temporary counterexamples

Fixture: `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/library-navigation-diagnosis-z8rl7ip4/navigation-counterexamples.test.mjs`, SHA-256 `0a7a23ec1b89f6ca14261290c41ee5245656178ef6d585137781ec58383605a6`.

It reads the **actual EN/DE LC templates and actual library script** from this worktree, substitutes a small declared semantic FAQ/document row fixture for the PHP shortcodes, lets JSDOM perform the native anchor default action before script evaluation, and drives the real input/keyboard/click consumers. The spy case supplies controlled rectangles, explicitly returning a zero box under a hidden panel. It uses the already installed JSDOM from the separate privacy-review tools package because this release worktree has no `node_modules`; no dependencies or project files were installed or altered. An initial missing-module harness run was excluded and corrected before the consumer run.

Command: `LIBRARY_REVIEW_REPO=/Users/chesterjohn/.codex/worktrees/marketing-library-release/de-linker node --test <fixture>`.

Result against the inspected source: **5 expected-behavior assertions fail, 1 positive control passes**, exit 1. The original `run.log` is retained (SHA-256 `5a9f5a105f61f8dae7c925624186220f59b2b566165eeaca7c3d163b79cb2283`). The fixture always writes `observations.json`; a later candidate-source run overwrote that sidecar. It is **not** the original baseline observation artifact. Those candidate observations are separately preserved as `native-anchor-candidate-observations.json` (SHA-256 `26e6ae709b5adba82f7834a5bf761529c633eeb2b0540562327612d077990fe8`).

To restore an independently inspectable baseline sidecar without mislabelling it as the original run, the reviewer extracted the three exact source/template files from `d27f3dc35126cd037db8f98f53da137cacbc52df` into an isolated temporary tree and ran the unchanged fixture again. It reproduced **5 failures / 1 passing positive control**. The rerun is retained under `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/library-navigation-baseline-recheck-ivn7d_l4/`: `baseline-rerun.log` SHA-256 `b6ffbbdec5dee36f5fd1e0e2e6e639698e3b465a8104342078991ac62ec04ea6`, `baseline-rerun-observations.json` SHA-256 `ac481d369aa0858f36732495324515224ba7f7dc0665a1b0c9724e6c67287e46`, and `provenance.json` records the extraction and matching source hashes. This rerun did not change the implementation worktree or any instance.

| Counterexample | Observed source result |
| --- | --- |
| EN native Documents click, then delayed enhancement and document-only search | Fragment names Documents; FAQ selected; zero document results. |
| DE native Documents click, then delayed enhancement and document-only search | Same state mismatch on the actual German template. |
| Existing `?tab=documents`, native FAQ click before enhancement | FAQ fragment remains; Documents still selected. |
| Keyboard suggestion focuses visible SAJ; hidden document card has a zero box | SAJ summary focus succeeds; current link belongs to the hidden document group; visible FAQ current is null. |
| Deep filtered-tab commit shrinks to three document rows | Three rows render; no positioning request. This is branch evidence only, not browser-layout proof. |
| Positive control: click Documents after enhancement, then search | Documents selected and three document results appear. |

These red tests diagnose the existing source. They are not repaired-source tests or native browser acceptance, and the positioning-call diagnostic should not become the final acceptance criterion in place of real geometry.

## Meaningful permanent consumer tests

1. **Slow external script, real native click.** Gate only the actual `library-ui.js` network request before navigating. Use `goto(..., { waitUntil: 'commit' })` and wait for the server's native tab/content DOM; do not await `DOMContentLoaded` while a deferred script is held, because that event waits on the script. Assert not enhanced, click/keyboard-activate the native Documents anchor, verify the fragment, then release the script in a `finally`-safe gate. Once enhanced, verify selected ARIA, panels, normalized URL and actual document-only search results **without a second click**. Repeat EN/DE at 1440/390. Also cover native FAQ over a stale Documents query, a descendant document fragment, and unknown-fragment fallback. Disabling all JavaScript permanently tests another useful contract but cannot test this handoff race.
2. **Focus and current category independently.** Keyboard-select a real SAJ FAQ suggestion; assert its summary focus and visible geometry, then separately require the eligible SAJ rail link/mobile chip to carry current state. Read `.is-active`, `aria-current`, hidden ancestry and target IDs. Include a later inactive-panel card and scroll away/back so a hidden zero-box candidate cannot win. Do not identify current state from hover color alone.
3. **Short result list at a deep reading position.** Start from a real deep FAQ position, commit the query/tab transition to a small nonempty document set, and inspect the resulting first readable heading/download action beneath the actual sticky stack. Assert document result type/count, `top >= stickyBottom`, useful viewport intersection and expected keyboard focus. Preserve the current query and do not call `scrollIntoViewIfNeeded()`, manually scroll, or refocus the results in the test after the action: that would repair the consumer's failure before measuring it. Exercise empty results and reduced motion as applicable.

Current coverage misses these boundaries: unit tab tests boot before clicking and only exercise search-string location; the rail test at `library-ui.test.mjs:286–298` explicitly tolerates all-zero layout and checks attributes exist rather than selected identity; existing geometry e2e checks focus/pagers but not the current rail/chip. Existing thumbnail e2e also scrolls images into view explicitly, so it cannot close the deep result-visibility failure.

## Version and acceptance boundary

The inspected template hashes are EN `f9d1c42ea4a0f8828a6f23767a43f6ecfe1ed07b8595c844ae1e52530f7fec10` and DE `b1d82f2328cafd8fe7698fc42cf76c0cfd55301b839c8d73653e13073a0d6a4d`; unit test file SHA-256 is `2caf4b0b26f4201bfab6ee383d794b1965971e421de48bd4c4a44c7161b3e04f`. The original online early-click JSON SHA-256 is `cf79d57ea6b5e70b9f31d5d914f05697d0dca83e27e723cbf9f0532cd30e9775`.

The parent assigned implementation in a separate navigation-continuity batch. This diagnosis does not authorize this reviewer to edit those files, merge or deploy. Original online red records remain red until the corrected, version-bound actual consumers and screenshots close each corresponding behavior; a good PDF thumbnail, correct focus or a passing re-click does not close all three navigation defects.
