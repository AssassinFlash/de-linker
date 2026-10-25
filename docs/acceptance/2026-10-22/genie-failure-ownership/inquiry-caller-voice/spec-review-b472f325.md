# Independent Spec review — b472f325

**Bounded Spec SOURCE PASS. No remaining reproduced source blocker was found in this frozen candidate.** This closes the three fd04 data-loss counterexamples for the exact source below. The fd04 BLOCKED report remains historical; this is not a build, generated-dictionary, browser, microphone, deployment, or production acceptance verdict.

## Exact source reviewed

The 19-product aggregate is `b472f3259aeb32e17419745942c5653ffbbe82e1332914e385929300290dfb1a`. Fixed producer root: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/voice-retained-final-20261022T063922077599Z/frozen`. Independent copy: `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/genie-spec-b472-j4gy1836/`.

All 19 product and 22 test/helper SHA-256 values were independently checked against `source-files.json`, including a final post-execution check. The aggregate was independently recomputed over file rows sorted by repository path (`fileSHA + two spaces + path + LF`). The three auxiliary files (PO, Genie spec, e2e spec) were also read-only hashed and match; exact readback is in `auxiliary-readback.json`. No product, tracked test, auxiliary file, generated file, instance, browser, or build was changed. This report is the sole repository output; added fixtures and read-only support copies are confined to the reviewer-owned isolated directories.

Compared directly with fd04, only `shared/editingDraft.ts` (comment), `shared/ownedFailure.ts`, and `shared/useFailure.ts` change. App remains `e287fdd29f30ea2f97599cc3a477c0c197454c2d18eb7b547a3cd42e1ef5cbf8`; the other 16 product files are unchanged. The full exact map is copied as `review-source-files.json`. The changed implementations were read in full, together with their caller paths and the ordinary recovery/variant contract; previous green counts alone were not used to establish this verdict.

## Why the three reported failures are closed

1. **Stale Restore no longer overwrites the displaced newer revision.** `useFailure.exchangeFailure` checkpoints the mounted editor against its original `editingCursor` and complete accepted entry. An unchanged stale editor yields to the existing newer copy; additional accepted UI text is retained separately under the same real scope/attempt. It no longer reads the current revision merely to write an older composer snapshot over it.
2. **A failed durable write no longer overwrites the other actual memory copy.** `keepMemory` retains an occupied divergent memory entry, including its exact original counterpart, before writing the newly selected editor’s fallback. This keeps the original voice text and the selected durable edit explicitly reachable.
3. **Clearing a stale editor no longer deletes a later memory revision.** Ordinary save/clear/before-leave calls now carry the mounted cursor. A later same-copy record fails the exact checkpoint comparison; clearing the old field cannot acquire authority by looking up that later revision. The original owner is released where appropriate without consuming the newer text/files/missing-name list.

The previously added conservative rules remain: a different attempt may advance bucket bytes only while the target’s entire entry and revision stay exact; same-attempt newer bytes/revision still conflict. Send promotion also checks the mounted acknowledged entry before promoting it. Late asynchronous work cannot select an inactive retained copy: explicit selection retains the exact scope/copy gate, and default save/consume still rejects stale or inactive cursors.

## Retained-copy semantics and scope

The additional window records represent actual displaced bytes at a demonstrated conflict or failed write; they do not create an owner, attempt, marketing entry, or speculative keystroke history. Exact selected entries are updated in place. The original owner scope and attempt remain unchanged, as do native identity verification, Hero, inquiry handoff, model routes, price authority, and resource behavior.

An existing Restore control cycles through actual distinct copies with their text, prepared file chips, and named missing files. Only verified explicit exchange selects a copy. Consumption requires the selected exact entry and preserves updated other copies; an unchanged proven original counterpart may be removed as already defined by the recovery contract. Surviving copies are made reachable again rather than hidden behind an attempt-wide tombstone. Memory/retained records remain window-only and produce the existing unsaved warning; this is not a promise that failed persistent storage survives a browser reload.

No new customer-facing copy is introduced by this delta. Existing warning and Restore terms remain subject to the pending generated dictionary/readback gate. The implementation is within the authorized no-silent-input-loss repair and does not change native business flow.

## Independent actual-consumer execution

All commands ran only in isolated copies with the already installed dependency tree. The consumers mount actual App/Hero/controller code, use normal UI events, public journal operations for competing accepted callbacks, controlled native-identity responses, prepared PDF fixtures and native-recognition event boundaries. They do not assign private React state. These are execution tests, not browser-layout or physical speech-recognition proof.

| Evidence in independent b472 copy | Result and boundary |
| --- | --- |
| `original-three-results.json` | **3/3 PASS**: the reviewer’s exact two fd04 counterexamples plus Standards’ original stale-clear fixture, preserving their expectations. The other copied test cases are skipped only by this targeted filter. |
| `critical-results.json` | **169/169 PASS** across actual failure/voice ownership, authority, journal, caller, and prior independent CAS/different-attempt fixtures. Includes Stop/Close/Clear/thread cancellation, pending pagehide, original A1/A2, PDF/missing-file restoration, B isolation, missing-only editor exchange and omitted-only upstream automatic recovery. |
| `core-results.json` | **514 passing value assertions, one uncollected suite**, because the TS-only producer snapshot omits the existing generated JSON imported by StockBadge tests. This is explicitly not described as a successful full command. |
| `stock-support-results.json` | After copying only that existing JSON read-only, **4/4 StockBadge tests PASS**. Its source path/SHA/purpose are in `catalog-support-provenance.json`; no dictionary generator or source/test change was made. The existing PHP constants support file for preparation tests was likewise copied read-only with provenance. |
| `retained-controls-final-results.json` | **2/2 additional independent actual-App controls PASS**, described below. No implementation-detail flag is used as their acceptance criterion. |

The two additional controls deliberately extend the permanent tests:

- Settle a legitimate newer memory revision, accept additional text into the stale real textbox, dispatch pagehide, actually unmount, mount as B, then return to fresh verified A. B has an empty composer/no private previews/no send; A can explicitly restore all three accepted texts. This proves leave/remount consumption rather than merely seeing three records in a helper.
- Select the actual retained text in the real composer, explicitly empty it and remove its PDF, dispatch pagehide, unmount through B, then return to A. Only that selected copy is gone; the newer memory and durable copies remain explicitly restorable, and no turn was sent.

Final independent fixture: `src/genie/spec-retained-controls.test.tsx`, SHA-256 `15e425f7032b3d4d02f66bedd790ba42bad5aa662979eee00cec58fffc5452e6`. That identical final file was replayed against the unchanged reviewer-owned fd04 product copy: `b472-controls-final-on-fd04-results.json` gives **two actual failures** (lost restorable text, and inability to reach the selected retained text), while b472 gives two passes. Original fd04 fixture/source hashes are retained; expectations were not relaxed.

The wider core/target counts overlap and are not added together. Producer-reported full-JS counts are not substituted for this independent execution. The known not-yet-regenerated warning catalogue gate is still open and was not bypassed or reclassified as product runtime success.

## Remaining delivery gates

No further source defect was demonstrated in this candidate after reviewing the complete three-source delta and the relevant unchanged callers. Spec SOURCE PASS is limited to this exact 19-file aggregate and the above behavior. Standards remains a separate independent axis. Final build/dictionary generation, live-bundle source readback, EN/DE × desktop/mobile Computer Use including Restore/unsaved/error states, and production acceptance remain required on the final integrated release. A fresh mount in these fixtures preserves the same window runtime; it must not be reported as guaranteed persistence across a full reload when storage is unavailable.
