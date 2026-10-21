# Library repair verification

Status: local source implemented; production and complete family coverage pending.

Changes preserve the existing FAQ answers, document records and file URLs. Product questions now carry their existing product field in the summary and suggestion context. Download names include the existing file title for assistive navigation. Every original/clone thumbnail reconciles its own cached or asynchronous load/error state. The fallback remains visible while waiting; failed images expose the type icon. Search selection focuses the actual summary and pagination focuses the first visible result. WindPress gives file/filter/paging actions44px targets and places phone file actions below the main text.

## Local proof

- `library-ui.test.mjs`: six regression cases added; the original source fails five (late clone load/error, cached error, suggestion focus and pager focus). Cached success already passed. The fixed source passes all28 tests. Private original/final logs: `library-regression-red.log`, `library-regression-green.log`.
- Existing LibraryPage fixtures:8 tests,61 assertions; WPCS passes. These existing tests only prove their own content/structure assertions, not every rendered product or file.
- Official WindPress admin compilation: cache mtime1792611780,696086bytes. Private log `library-windpress.log`.
- First browser run after JS/PHP source but before new CSS: four focus cases pass, four action-height assertions fail (desktop37.5px, phone34px). The subsequent compiled eight cases pass; their screenshots were independently reviewed and found to be obstructed by Cookie consent, so they are not accepted visual evidence.
- Final unobstructed browser run: `local/20261021T194746691Z/`, eight cases at EN/DE ×1440/390,18.0s. Uses actual native library fragments and holds image responses until the three search clones exist. Each clone then becomes loaded and visibly opaque; every file action has a distinct accessible title and height>=44, phone text width>180px. The keyboard checks require actual focused element rect to clear header/tab/chips and remain inside viewport after search selection, subsequent Tab and pagination. Cookie consent is dismissed through its real Reject all action. `summary.json` records16 items including geometry/focus.
- Computer Use on local DE390, with actual thumbnail bytes and no intercept: `local-cua-de-390-real-thumbnails.jpg`, `local-cua-real-thumbnails.json`; all three AIO3 images have natural width>0, complete=true, hidden=false, computed opacity1. This is local visual proof, not production readback.
- Independent Standards review: PASS; independently executed28 JS cases. Independent Spec source/semantic and final unobstructed visual review: PASS after viewing all8 final PNGs and the actual CUA thumbnail capture. Final pager focus tops approximately214/300/214/297px clear stickyBottom137/192px. The earlier Cookie-obstructed frames are retained as diagnostic evidence and are not the visual gate.

Additional native regression: existing `faq-download.spec.ts`10 cases pass, including EN/DE tab/query/count/filter/card pagination and both-width anchor geometry. A further four no-JavaScript contexts pass at EN/DE1440/390: both complete native panels remain available, actual details toggles open and reveal product context, a real document thumbnail loads with opacity1 and its accessible Download name contains the original title. No network interception is used in these four cases. This proves the basic no-JS fallback; it does not prove every file or a script-dependent filter without scripting.

Every document category/file, the remaining family states and new production acceptance remain open. No production data or customer communication was written by this batch.
