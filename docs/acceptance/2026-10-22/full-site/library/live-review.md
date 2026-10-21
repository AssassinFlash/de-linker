# FAQ / Documents live review

Status: partial discovery, repairs and final acceptance pending. This is an actual interaction record, not the full family acceptance.

Production WordPress runtime: `20261021T183520720401Z-4f722c26`. English route `/faq-download/`, German route `/de/faq-dokumente/`. Native source inventory: 244 FAQ and 159 document records in English. Existing screenshots are first discovery captures; they are not a new release-bound screenshot run.

## Observed behavior

- English 1440: open a trade FAQ, select the EcoFlow navigation link and wait for smooth scroll to settle; target appears below the sticky stack. Search AIO3 gives 12 combined results (9 FAQ, 3 documents). ArrowDown/Enter selects the actual AIO3 question and opens the original answer. Documents tab preserves `?tab=documents`. Clear resets to 403. No-result query displays a localized empty state and Ask Genie link. Downloaded the existing AIO3 datasheet through its rendered Download link; `pdfinfo` reads one unencrypted page. SHA256 `1833312ad717e11d5fea900948ef7ac84446065af17d50565c9c2b42e4494ab1`.
- English 390: switching FAQ/Documents preserves the live query and respective 9/3 counts. Search Enter expands and scrolls to the actual AIO3 answer, while focus stays on search input. Next Tab reaches the sticky FAQ tab rather than the answer. EcoFlow Next shows the second page (12 remaining of 32), Previous enabled and Next disabled. Re-rendering removes the clicked pager control; active element becomes body. Follow-up keyboard focus repair pending.

## Confirmed repair candidates

1. Search thumbnail race. `cloneRow` clones source rows without the once-bound image listeners from `prepare`. Rendered valid images have complete=true, naturalWidth>0, parent `.has-src` without `.has-img`, CSS opacity 0, and hidden fallback SVG. At 390, first AIO3 thumbnail eventually showed, second naturalWidth305 and third153 stayed opacity0. On desktop all three initially stayed opacity0. No load error was present. Fix shared initialization for source and every clone, with positive complete/load and cached failure/error paths; show a type fallback while pending or failed. Test delayed source load, clones created first, cached success and cached failure.
2. Ambiguous collapsed product questions. Multiple identical generic questions appear under a brand with product context only in the expanded answer's source link. `$answer['product']` already exists; render it in the summary and search suggestion context without altering the question/answer facts. Trade questions should not acquire invented model names.
3. Phone document geometry. Visible rows are348px wide. Thumbnail52px plus107px action leaves about120px for filename/model text. AIO3 rows measured192/192/212px high; Download is34px tall. Give main text usable width and an intentional action row with at least44px target; preserve file language and real URL.
4. Keyboard selection/paging. Move focus to the actual FAQ summary on suggestion selection and an appropriate surviving heading/result boundary on pager re-render. Preserve scroll offset/reduced motion and native details semantics. Verify ensuing Tab reaches answer links and controls, not detached or earlier-page controls.

## Evidence cautions

- `faq-ecoflow-en-1440-before.jpg` is an intermediate smooth-scroll frame; use `faq-ecoflow-en-1440-settled.jpg` for settled geometry.
- `normal-after-escape-en-1440.jpg` shows normal results because Escape clears a no-hit query by the existing handler; it is not an empty-state screenshot. `no-results-en-1440.jpg` is the correct empty state.
- The downloaded file remains in the user's Downloads folder; no deletion was performed, since an identical filename could have pre-existed.
- Generic Ask Genie navigation has not been classified as lost-query functionality. An automatic question handoff would require its own product contract.
- German, keyboard pagination after repair, all document categories, no-JS behavior, all real file downloads, query language switch and the remainder of the full state matrix are still pending.
