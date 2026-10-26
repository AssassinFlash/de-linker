# Ordinary Genie ownership: frozen source and consumer evidence

The source candidate is frozen at product aggregate `c267ce64e8b9f958914c69d65ea9530fdafcd09beb5b48f62c03b8c5ba711a41` on `codex/genie-failure-ownership`, relative to `eb097915`. The precise 17 product sources, 16 test/helper sources, PO, specification and browser spec are in `source-files.json`. The aggregate is SHA-256 over the sorted lines `file-SHA256 + two spaces + relative path + LF`. Individual auxiliary hashes also cover the PO, `13-genie.md` and the new browser consumer.

This replaces the independently rejected `c5cb` source candidate; its fixed original snapshot, actual-consumer red replay and the narrow repair matrix are recorded in `review-repairs.md`. This is a source candidate. The final full tools JavaScript run reports **553 passed, 1 failed, 56 files / 554 tests**. The sole failure is `configurator/i18n.test.ts`, which correctly detects that the approved storage warning has not yet been generated into the existing JSON catalog. Its full EN/DE pair is supplied in the PO. ESLint over `src`, tools TypeScript, e2e TypeScript and the limited `git diff --check` returned zero. Parent-owned build/i18n, same-hash independent reviews, actual browser screenshots, CI and production acceptance are separate gates. None has been represented here as complete.

No model request, email, inquiry, deployment, commit or production write was performed for these consumer tests. The local production-shaped instance has not been used with the new source, because its bundle is deliberately awaiting the parent build.

## Implementation boundary

The design is `../full-site/ordinary-failure-repair-design.md`, including its editing, bucket/attempt and dual-bundle bootstrap addenda. It follows the existing native Genie browser epoch and WordPress authentication session; it changes no server authorization, model channel, knowledge source, inquiry or saved-solution behavior.

| Module | Responsibility |
|---|---|
| `nativeScope` | Native private identity lookup, a window-shared tab fallback, cold pending lookup and bootstrap generation. Fresh Send/Retry requests do not reuse a pending cold request. A failed durable tab read/write cannot claim old persistent drafts. |
| `DraftContext` / `useDraftContext` | Owner before accepted input; loading quarantine; native identity and surface epoch; original-owner checkpoints; New/Select/Delete/unmount invalidation; late-result settlement; wait across a superseded cold lookup without accepting its old result as authority. |
| `FailureJournal` | Scope bucket, explicit insertion order, stable attempt/revision, synchronous raw bucket CAS, current candidate, precise consumption and active repair, scoped window fallback, and single-selector scoped-v1 migration. |
| `editingDraft` | Accepted unsent text, actual prepared files and explicit missing names, retained under the original owner/attempt before leaving. An editing draft restores to editable ask state and starts zero turns. |
| `verifiedEntryFailure` | The one fresh recovery selector for App, Hero and the homepage controller. Unknown v1 bytes stay inactive and byte-identical. The current scope's v2 candidate wins over a scoped v1 record. |
| `useFailure` | Reducer presentation and precise journal cursor; deliberate Retry may rebase an unchanged target revision over a different attempt's write. Async settlements cannot rebase. No-durable-write paths retain the current scoped memory copy and warn. |
| `MissingFiles` / `OwnedRecovery` | Reuse approved text and existing button primitives. Both editors expose actual Restore, reselect and Remove controls; ordinary drafts receive no fabricated marketing ID. The workspace can reselect a carried-over missing file through the existing hidden file input. |
| App / Hero / controller / session | Connect all actual producers and renderers to that owner. The homepage prefetch stays quiet. Initial file/voice intent resumes as an explicit Choose/Dictate action; no async microphone or picker call. Hero session caches cannot survive a native principal/thread epoch change. |
| `useEntryInbox` | Existing marketing claims remain separately durable and freshly verified. Their accepted or restored composer must also match the App's native owner/epoch. Principal changes detach mounted entry panes, parked filenames and ownership flags. A durable source retained across a competing check remains available as an explicit draft. |

The initial auxiliary identity budget remains the existing five-second metadata budget. Model transport still has its existing independent budget. Native authentication and conversation ownership are not inferred from a cached conversation ID, an empty history response, a 403, a language or an entry ID.

## Producer and reader census

| Actual producer or consumer | Ownership/persistence path | Permanent evidence |
|---|---|---|
| Ordinary App field, including edited recovered text | `acceptEditor()` precedes accepted input; actual Send uses its own native owner and journal attempt. | `failureOwnership.consumer.test.tsx`; `App.test.tsx` |
| Native home textarea, capsules, Send and supported dictation | Controller accepts bytes only after native ready; provided context is shared with `HeroConversation`. | Actual `startHero` consumers in `failureOwnership.consumer.test.tsx` and `controller.test.tsx` |
| File input / actual FileReader / PDF preparation | Capture owner/epoch before preparation; `whenVerified` permits only that original owner to paint a late result. | Actual PDF consumers, including held FileReader and cross-surface recovery |
| App and Hero pending/failed turns | `useFailure.commitFailure` → `FailureJournal`; actual callbacks retain the captured lease, not a newer scope. | Both surfaces' success/refusal/conflict/upstream/finally tests |
| File chip edits and Retry | Exact journal cursor; immutable scope; original retry attempt; model send after queued thread read and a fresh native check. | `useFailure.test.tsx`, ordinary consumers and existing App/Hero tests |
| Unsent editing before quarantine, Close, New/Select and real pagehide | `beforeLeave` / `checkpoint` → `preserveEditing`, including actual prepared bytes; prepare-pending files retain explicit missing names. | A→B→original-A editing, Close/PDF, New, pagehide and missing-file consumers |
| App history/refresh restore | `applyRecord` → fresh unified selector; current v2 first; verified conflicts use existing explicit Restore rather than overwriting a new editor. | App and marketing delayed-history consumers |
| Hero/controller initial restore, including outage | Controller checks native ownership before opening cached recovery; component uses the same selector. Private text is not the signal that opens a generic outage UI. | Actual controller outage/Retry consumers; no isolated-component substitute |
| Explicit two-way Restore | Fresh native check plus unchanged input, picks, missing names and busy/epoch guards; retain displaced owner before replacement. | Hero double swap/missing names, App retained-draft consumers and journal CAS tests |
| Marketing ENTRY initialization, accept, append, parked restore and normal edited Send | Existing durable ENTRY claim plus the App's native owner/epoch, with private panes quarantined by the same ready state. | `marketing/entries.test.tsx`, including mounted-B → fresh-A Attach → edit → B return |
| Legacy v1 | Unknown-owner bytes have no active production writer/restore path. The legacy codec/writer exports remaining in `failure.ts` are exercised by its compatibility unit tests; actual App/Hero persistence uses the journal. Scoped v1 migrates only inside the unified selector, after exact durable readback. | `ownedFailure.test.ts`, `entryFailure.test.ts`, unknown-v1 actual consumer |

The new journal does not use the old ownerless writer as a fallback. Its window memory store is shared by the two independently built bundles, scoped by the native owner, and is not durable acknowledgment.

## Async mutation and display boundaries

| Await or lifecycle boundary | Final behavior and evidence |
|---|---|
| Cold scope request shared by separate bundles | One window pending bootstrap/generation; after identity invalidation the old result cannot enable either editor. `nativeScope.test.ts` imports independent module instances. |
| Initial scope unavailable or still pending | No accepted ordinary text/file/dictation bytes; explicit interaction has existing loading/error/Retry. Auxiliary Retry makes zero model turns. |
| A revalidation begins with accepted text/files mounted | Checkpoint under A, immediately hide body/filenames/history/live content, then verify. Confirmed B gets a blank editor; A's retained bytes are never rebound to B. |
| Fresh display read completes after user input/history work | Raw selector cursor and context epoch must remain applicable. The current editor is retained; another verified candidate is offered explicitly. |
| Same-owner fresh check begins while an ENTRY consumer resumes | Keep immutable owner/epoch checks for retained data and let the mounted loading state quarantine its display. Automatic ENTRY consumption runs only when native ready. Actual transport still checks fresh authority and ready epoch after the ENTRY check. This closes a reproduced cold first-click rejection. |
| Prepare completes while scope verification is pending or unavailable | Wait for the original owner to become verified; an identity/thread invalidation releases it without painting old bytes. A preparing file retained across a departure is named for reselect, not asserted to be prepared. |
| Model result returns after A→B or New/Select/unmount | App and Hero reject stale success, refusal, conflict, upstream and finally effects. Completed Hero live announcements are also cleared and hidden while unverified. |
| Retry starts after another attempt changed the bucket | An explicit Retry may re-read only an unchanged target revision, then synchronously enter pending. A stale revision is not sent. Subsequent callbacks keep their exact cursor. |
| A2 succeeds or is abandoned with older A1 retained | Same bucket CAS repairs active to the last surviving insertion. Fresh mount/native verification can reach A1 through Restore. Late A2 cleanup cannot delete A1 or alter a newer active. |
| Storage get/set/precise readback fails | Do not treat the bucket as empty or consume old bytes. The original scope's window memory owner is editable/retryable with the reviewed warning. B cannot retrieve it. Exact readback mismatch is not a durable claim. |
| Ordinary editor becomes explicitly empty | Consume only that editor's own editing snapshot; no old text is silently restored after New. Older unrelated attempts are not the target of that cleanup. |
| Real document navigation/pagehide | Explicit checkpoint exists; React cleanup alone would not run on browser navigation. Both actual ordinary surfaces test the stored editing record before component teardown. |

## Red/green provenance

- `baseline-diagnostic-source.txt`, `baseline-risk-confirmed.log` and `consumers-red.log` preserve the original 12 independent ordinary-producer diagnoses and their conversion to security assertions. They use normal typing and real file preparation rather than a marketing binder or a fabricated entry ID.
- Permanent ordinary consumers now cover text A→B/guest with empty/403 history, actual prepared PDF cross-surface recovery, same-owner explicit recovery, A1/A2 selection, unknown v1, blocked get/set, in-place late results on both surfaces, actual held FileReader, initial pending/outage, auxiliary Retry, same-account rotated scope, unsent editing, Close/New/pagehide, memory-only and missing-file reselect/Remove. The current `failureOwnership.consumer.test.tsx` contains 76 passing cases.
- `entry-context-red.log` reproduces a mounted-B App accepting a fresh-A marketing draft but later retaining its edited bytes as B. The permanent real binder→App counterexample passes after entry/native-owner alignment. Its retryable state may require the existing explicit Open as draft when identity turnover races the initial history check; it does not lose or automatically send the durable source.
- `announcement-red.log` proves a completed home answer survived A→B through its screen-reader live region. The permanent actual-controller test now checks both visible and live text.
- Cold-entry diagnosis found that a same-owner fresh check was being confused with a changed owner between async continuations. The preserved debug log contains only explicit local fixture values. Final source has no debug logging. The final marketing suite retains all its behavioral assertions and native/turn fixture boundary.

`checks/records.json` is a byte-preserving base64 package of the local log copies, each with SHA-256 and byte count. Original `/tmp` logs and loose local copies are diagnostic artifacts; the JSON package avoids presenting raw log whitespace or ANSI output as source. The empty ESLint/type logs are paired with the recorded zero exit statuses. The final full tools JavaScript log still records the one generated-catalog failure; it has not been replaced with a partial-suite success.

## Browser handoff

`tests/e2e/specs/genie-failure-ownership.spec.ts` defines **18** cases. Eight cover home/workspace × EN/DE ×1440/390, starting with actual ordinary typing and home PDF preparation, a real native guest-cookie rotation, another guest's independent failure, original valid guest scope return and explicit restore/retry. Four cover an auxiliary scope outage, four cover get/set denial and usable memory-only retry, and two use actual local login/logout plus a new session for the same account. History/model responses and selected fault conditions are fixtures; guest scope, authentication cookies, nonce handling, real DOM consumers and PDF preparation remain native.

Run only after parent review/build/i18n/presentation. Use a new UTC `LINKER_FAILURE_RUN` per process and one browser runner for privacyviz. Preserve failed frames and case metadata; do not reuse a prior UTC directory. Screenshot geometry checks the reused decision/remove controls; manual review still needs to assess all states and languages. This source record is neither a browser PASS nor a full-page visual parity claim.


## Current-main source integration (2026-10-25)

The owner authorized Codex to continue this existing candidate after the Claude alias resolved to another model. No global configuration was changed. The existing `codex/genie-failure-ownership` worktree integrates `origin/main` at `7f0c8f7b38264210e67efc16d0d86ad33cec012b` with the two original candidate commits `811dad33` and `6bdb8869`; no other plugin tree was copied. The two pre-existing tracked full-site edits and all 2,786 untracked files were preserved. The full-site goal/state records remain owned by the parent.

The existing 19-product-path aggregate algorithm from retained-repair `source-files.json` now gives **`28b7e7915fbae4e3871ce4778b5b801dbdfd3096b6eed90657d249f6a2f08eb2`**. Fifteen of those sources remain byte-identical to the reviewed b472 candidate. Four source files differ:

| Source | Integrated SHA-256 | Integration responsibility |
| --- | --- | --- |
| `src/genie/App.tsx` | `71bad76f62fc896694fe30c994d41df80863eb3cf4f4473e9cd070a618a24f99` | Retain native leases and current-main operation witnesses; discard witnesses on identity changes; completed retry preserves/checkpoints the next accepted editor and PDF. |
| `src/genie/shared/failure.ts` | `e26afb75ef041258cb55b57c8545c20916e3f64ea3fd97bccff5a49b659c0e1b` | Keep editing recovery while preserving main's refusal to infer completion from historical matching words. |
| `src/genie/shared/useFailure.ts` | `e2c6300d3f5253b473d4c707c9243efcb3aa2a7e1559e245b0360712d2e1d672` | Retry owns the attachment snapshot accepted at its click, rather than files accepted by a new editor during asynchronous thread refresh. |
| `src/hero/session.ts` | `4f97117fd4eb5b467f6cc8b6a960fd43396340b37da6e0f30ed39ee3d15e979d` | Combine native generation/settlement with completed-request recovery; invalidation clears conversation/operation/witness and rejects late results. |

Current-main PHP product publication and resource authorization, Genie API clients, signed card-action protocol, `completedRequest` comparator and protected request transport are byte-identical to main. App's current product proofs and nonce-aware store client remain active. The specification retains the native 5-second identity budget, current 20-second product authorization budget and 90-second turn budget. Only the existing approved unsaved-warning stanza is appended to main's PO; no unrelated translation is replaced.

A single additional case extends the existing completed-request matrix: while Retry waits for the thread read, the actual composer accepts a new question and a real prepared `next.pdf`. It first failed with two sends instead of one. Diagnosis showed the old retry reading the new editor's shared uploads, which defeated its exact operation witness. After capturing the click snapshot, the same case passes with one send, the completed answer visible, and the new text/PDF preserved as an editing record. No previous assertion was removed or weakened. Main's newly added App/Hero cases now await the candidate's native identity initialization; the Hero alert assertion reads the currently mounted alert instead of a detached node returned across revalidation.

Final focused execution from `plugins/linker-tools`:

```sh
npm run lint:types
./node_modules/.bin/vitest run src/genie/App.test.tsx src/hero/Hero.test.tsx src/hero/session.test.ts src/genie/failureOwnership.consumer.test.tsx src/genie/voiceOwnership.consumer.test.tsx src/genie/resourceOwnership.consumer.test.tsx src/genie/shared/useFailure.test.tsx src/genie/shared/failure.test.ts src/protection/inquiryHandoff.ownership.test.ts src/protection/inquiryHandoff.consumer.test.tsx src/genie/api/turnProtection.test.ts src/genie/api/historyArtifacts.test.ts src/genie/shared/cardActions.test.tsx src/genie/PartsApp.test.tsx --maxWorkers=2
./node_modules/.bin/eslint src/genie/App.tsx src/genie/shared/failure.ts src/genie/shared/useFailure.ts src/hero/session.ts src/genie/App.test.tsx src/hero/Hero.test.tsx --max-warnings=0
./node_modules/.bin/prettier --check src/genie/App.tsx src/genie/shared/failure.ts src/genie/shared/useFailure.ts src/hero/session.ts src/genie/App.test.tsx src/hero/Hero.test.tsx
```

The focused 14-file run reports **300/300 passing**. TypeScript, changed-file ESLint and formatting pass. After a lint-only rearrangement of the new case's assertions, the existing completed-request matrix was replayed alone: **10 pass**, with 61 unrelated App cases excluded by that explicit filter. The earlier fixture/typing failures and this new red case are described above; historical blocked reports and original failure evidence remain unchanged. A repository-wide cached whitespace check also reports pre-existing main whitespace in `537/phpstan.txt` and the commerce contact asset; neither belongs to this Genie delta, whose scoped diff check passes.

At the source-only handoff, all tools `build/` and generated JSON/MO files equalled main and did not claim this source candidate. They required the current native build/i18n pipeline; the old branch's generated outputs were not used. Independent integrated-diff Spec/Standards review, generated manifest/catalog checks, affected-state Computer Use and release/deployed readback remained parent-owned delivery gates. No full suite, browser, local instance, product model/mail request or production operation ran in that batch. No worktree, backup, dependency installation or temporary report copy was created.


## Generated delivery from the integrated source (2026-10-25)

This completes the generated-output gate after source-only commit `a9fde6e3207f3d41a59c4b5d02e8d896d95888c7`. The source-only handoff's retained-main bundle state above is superseded by this section. The same worktree and installed dependencies were reused. Product sources, tests, build configuration, package files, PHP/API code and the entire approved PO remain byte-identical to that source commit. The 19-product source aggregate remains **`28b7e7915fbae4e3871ce4778b5b801dbdfd3096b6eed90657d249f6a2f08eb2`**.

Generation used only the repository's existing `npm run build` in `plugins/linker-tools` (`wp-scripts build` plus native manifest writer), then `just i18n-tools` (`wp i18n make-json --no-purge` and `msgfmt --check`). The broader build wrapper was unnecessary; Commerce was not rebuilt. Webpack completed successfully with three visible warnings: asset size, entrypoint size, and the configurator runtime-placement recommendation. These are retained warnings, not an assertion of performance acceptance.

The manifest binds **109 source/input paths** to **24 built paths**. Its plugin-relative source-row aggregate is `1bb862f614fd4dea354a63b097cc491e6121e5fd824232aa73b623fd01fa6d94`, using the same sorted `SHA + two spaces + path + LF` algorithm. Its own final SHA-256 appears below. No source/asset hash was substituted by hand.

Across the 33 observed build/language files, exactly **12 files change** from the source-only commit; the full generated delta and final SHA-256 are:

| File under `plugins/linker-tools` | Generated SHA-256 |
| --- | --- |
| `build/genie.asset.php` | `61e405b1fb0a5894b076f75786363a166781fb8de0eef44b99ca30165b6cad93` |
| `build/genie.js` | `171a8eae7d9afb38dd33037f106ac7799f98ea87e106010413ce62779a8634cc` |
| `build/hero.asset.php` | `5c09f8b3e07a0b841bced4384c1f61be5a0973c23746087ea13aca474b41de38` |
| `build/hero.js` | `8a3f5d2d784fd7846ce65b87a7dc52357208e9ed87285dcd54801f9113a4e495` |
| `build/inquiry-handoff.asset.php` | `6136874ae3d6c8c436afb6c957ea829fba16d4e1acf885b3dac735c2fe04fc93` |
| `build/inquiry-handoff.js` | `07df817b09007e2841e67e4d7cd5c1c355a5f3cc2821124977bf6b5349f812a3` |
| `build/manifest.json` | `7e6df6670c09ce8a4ba26d851742390e48c634fc8bb17cd826a28c8d14ede0ff` |
| `build/marketing.asset.php` | `beada248329b87fda668b70268fedd7f715d05d4e1f3c4265416ae9ee0ff0220` |
| `build/marketing.js` | `5f3f1ab71adcbf928e110f822bb2e29808c682636d8998e793179bb4ced7f71f` |
| `languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json` | `642bf2d27753f73b1ddb65fa1113a876a1ff852e215c21e16cb944c6ba969611` |
| `languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json` | `22e284487689764209c6267fa8e63d0bb8114c24c3a1f7516b468eade3920d8b` |
| `languages/linker-tools-de_DE_formal.mo` | `b7b8fb34aa983149442bfd73d5a6005c8fb0cbfc1ec5a53ecd3d62673defd867` |

The changing entry versions are `genie=61b140c3ab75fb3e28c4`, `hero=673f67141c4ded61bcba`, `marketing=68f18e68a7657f178d47`, and `inquiry-handoff=cc18f291a92e7234af8c`. Genie/Hero carry the reviewed recovery integration. The marketing entry changes through its existing `entryDraft → durableNativeScope` dependency, and inquiry handoff changes through its existing native-ownership bridge; no marketing source or customer copy was edited during generation. All six entry dependency arrays remain byte-identical before the version field, including WordPress/React external handles.

The other **21 observed files remain byte-identical**: `build/configurator.js`, `build/configurator.asset.php`, `build/preview.js`, `build/preview.asset.php`; `build/52.js` and `build/555.js`; all ten CSS/RTL files (`555`, configurator, genie, hero, preview); the configurator `ff47dbd6ce1b77b210b406f2367c7ea7` and preview `b465a58df1aa4e563112b65e45dffa1c` German JSON files; the entire German PO and both Chinese PO/MO files. Configurator and preview versions remain `ab3597bdbd34fea4385c` and `a53b0f4957ca4350342d`. The entire Commerce plugin also remains byte-identical to the source commit.

The approved warning is present in both generated `build/genie.js` and `build/hero.js` German catalogs with the exact unchanged translation: “Ihre Frage konnte nicht gespeichert werden. Wenn Sie diese Seite neu laden oder verlassen, kann sie verloren gehen.” The PO was not re-extracted, reordered, retranslated or edited in this generation step.

Generated verification, bounded to this plugin and its delivery artifacts:

- `npm run build:check`: PASS; manifest matches the actual sources and built files.
- `vitest run src/configurator/i18n.test.ts --maxWorkers=2` from the plugin cwd: **7/7 PASS**, covering native generated dictionary completeness, retained terms and formal address.
- Existing `i18n-coverage.py` functions invoked for linker-tools only: zero runtime-source gaps, zero native make-json byte differences, zero live obsolete terms, zero untranslated terms, zero stale exemptions. The helper's temporary native JSON comparison directory was automatically removed.
- Exact dictionary readback for the warning in Hero/Genie: PASS. Exact dependency-prefix comparison for all six generated asset PHP files: PASS. Source/input/PO and Commerce unchanged checks: PASS. Generated scoped `git diff --check`: PASS.

The first ad-hoc dependency-display read assumed a one-line `array(...)` and failed on the native multiline PHP representation. The corrected comparison reads the complete bytes before the `version` field and passed all six entries; no build/source/config change or second generation was needed for that diagnostic. The 300 passing source cases were not rerun. No full-site checks, browser, local instance, port/symlink change, product model/mail request, production write, worktree, backup or dependency installation occurred. Incremental integrated-source/generated Spec/Standards review, CI as appropriate, affected-state Computer Use and deployment/readback remain open with the parent.


## Final integrated Spec (2026-10-26)

**Bounded integrated Spec SOURCE PASS at `06cb7abbca1377f348dbf5d8ccefe4729ac8bb0e`; no new source blocker found.** Reuse [the b472 source review](inquiry-caller-voice/spec-review-b472f325.md) and its unchanged-source conclusions. Its aggregate identifies source bytes, not a Git revision: all 19 original hashes match commit `6bdb8869`. Independently recomputed the current 19-path aggregate as `28b7e7915fbae4e3871ce4778b5b801dbdfd3096b6eed90657d249f6a2f08eb2`: fifteen paths are identical; only `App.tsx`, `shared/failure.ts`, `shared/useFailure.ts` and `hero/session.ts` differ. Read their entire 14,086-byte integration diff (SHA-256 `c25280f2a3b7529d8e7480cbff3c31ade6e8cce846867dba2a8aa8a9061dea5c`) and necessary Send/Retry, native-context, journal and Hero consumers. The FAQ-only merge after `7cbbe894` leaves Tools unchanged.

The integration preserves these contracts:

- App captures the native lease before queued work, authorizes freshly after the thread read, and guards settlement/finally by the original owner/epoch. Identity cleanup discards its witness. Hero invalidation clears conversation/operation/witness, and generation checks reject late refresh/send results.
- Completion is witnessed by the actual protected operation and native conversation, exact message prefix/question, attachments, locale and page context. App also requires the current history epoch. The comparator and API/operation transport remain byte-identical to integrated main. Historical matching words cannot consume a failure; editing records retain their separate restoration path.
- Retry snapshots accepted uploads at the click and later payloads use that snapshot. The completed-result branch checkpoints an accepted A2 editor before consuming A1 and clears chips only without a newer editor. The existing real-composer `completed-with-next-draft` case asserts one send, the stored answer and retained A2 text/prepared PDF. Card proofs and nonce-aware store calls remain connected to current-main consumers.

Reuse the recorded 300/300 focused, 10/10 completed-request, type/lint/build/i18n results; none was rerun. The earlier [generated review](inquiry-caller-voice/spec-review-generated-b472.md) remains historical for its exact artifacts; the current integrated generated-output review belongs to the separate Standards axis. This source PASS does not accept browser/microphone behavior, local runtime, deployment, production or the full-site goal. Only this section was appended; the three pre-existing tracked edits and all untracked evidence were left untouched.

### CI 40211348204: busy Hero file completion (2026-10-26)

PR #654 at `25c79fee197e7e70fdb38e38bfddd1fd8da1997f` failed the actual 69-file/713-case CI run: `review repair: home A1 refusal preserves the accepted A2 text and actually prepared PDF` read an empty field instead of `A2 newly accepted question`. The earlier local 300-case result does not supersede this failure. The original isolated case passed locally under Node 24.22.0 and Node 22.23.3; that only established that the original schedule was not deterministic, not that CI was incorrect.

Diagnosis isolated a real product race. The native homepage picker calls `bridgeAsk('', files)`. While A1 was pending, the Hero accepted A2's file but still created `pendingSend`. If the preceding turn's refusal/finally completed before the file-ready passive effect ran, that effect observed an idle sender and automatically sent the next file-only turn, clearing A2's field. This was unrelated to principal changes, auxiliary identity outage or a test that merely needed a blind delay.

The same existing home/refusal case now holds the real FileReader `readAsArrayBuffer` through its existing public wrapper, settles A1's refusal, then releases actual PDF preparation. No private React state or fabricated prepared upload is installed. Before the source fix this exact controlled schedule failed with the original CI symptom (`expected '' to be 'A2 newly accepted question'`); a separate diagnostic assertion also measured two `sendTurn` calls. All original text, filename, prepared-byte, pagehide and Restore-exchange assertions remain. One added assertion requires exactly one model turn; the other nine A1 outcome combinations keep their existing schedule. No new matrix, skipped case, softened expectation, retry loop or sleep was introduced.

The only product edit is in `src/hero/Hero.tsx`: file picks accepted while `sending.current` is true are still prepared under the current editing owner, but do not create an automatic `pendingSend`. Ordinary idle photo/PDF picks retain their existing prepare-and-send behavior. Session, journal, inquiry ownership, model channels, product publication, customer copy and other tool sources are unchanged.

Bounded verification after this repair:

- Exact failed case under Node 24: **1 PASS**; existing A1 outcome group (dock/home, five outcomes): **10 PASS**; existing Hero and controller files: **41 PASS**, including ordinary idle file sending. Counts overlap and are not added.
- Exact controlled case under local Node 22.23.3, the CI major version: **1 PASS**.
- `npm run lint:types`, changed-file ESLint and Prettier: PASS.
- One existing `npm run build`, then `just i18n-tools` and `npm run build:check`: PASS. The same three pre-existing webpack performance warnings remain visible.
- Generated hash comparison: only `build/hero.js`, `build/hero.asset.php` and `build/manifest.json` change; all other **30** observed build/language files remain byte-identical to the pre-repair candidate, including Genie, marketing, inquiry-handoff, configurator, preview, shared chunks, all CSS, PO/JSON/MO and their approved translations. Commerce is unchanged. Scoped diff whitespace check passes.

Final 19-product-path aggregate is **`6d125345e1536570d143c0554bee21e94f5164d9593bb34f2dd7c336d029bf05`**. The native manifest's 109-source/input aggregate is `d3fc6f89c89f044362c041879ed4f251c01fe7c435fab58967103d294bdbdfe2`, using the previously documented sorted row algorithm.

| Changed file | Final SHA-256 |
| --- | --- |
| `src/hero/Hero.tsx` | `b35c508e5e09ffc09dd55f33712a829b168e6f493120328e68dcce84f9df0d04` |
| `src/genie/failureOwnership.consumer.test.tsx` | `302b003742194b2cf7924adf144eee0f67ff26f66dd9ee20f7215724b9fbf11f` |
| `build/hero.js` | `eb08bc668a6189a5987e6886d9ffa65fc2a93dccfb621c3cec5732167d60288c` |
| `build/hero.asset.php` | `3b6a387ff813580cd89b73c843eeb4276706d3dd1eb7c58cff0a1ccaeb49e16c` |
| `build/manifest.json` | `887ed114828253cf54d7dce3e26f9873af1e9e94abdb16cc27c5eb1ea0ba12ff` |

The failed CI run is preserved as failed; a new CI result remains required after the parent takes this commit. This batch did not rerun the full suite, deploy, send mail, call a real model/CAPTCHA, start an instance or change ports/symlinks/configuration. The pre-existing AGENTS and full-site tracked edits plus all untracked goal/evidence files are preserved. Incremental source/generated review and the affected Hero busy-file browser readback remain parent-owned delivery gates.

### CI 40213689343: Storybook native-identity fixture (2026-10-26)

At source HEAD `163cc97dfd3bbcefe36ba19d1787f8d092364723`, the new CI run passed all **69 Tools files / 713 unit cases**, including the formerly failing busy-Hero case, and passed mu-smoke. Its sole failed step was later in `just test`: the four existing `tests/e2e/failure.spec.ts` cases each timed out at 30 seconds, while the other 14 Playwright cases passed. This is a different failure from CI 40211348204; the new failure remains preserved in run 40213689343, job 121230145809.

The common Storybook proxy returned 404 for every unhandled Genie endpoint, including the required `POST /entry-context`. The current App therefore could not obtain its native comparison identity or enable its editor. This was a missing browser fixture contract, not evidence that the preceding Hero repair regressed. The same fixture still injected quota failure into the retired v1 record key, and reload steps assumed automatic recovery rather than the current explicit Restore action.

Only that existing Playwright fixture changes: return one explicit 64-hex Storybook principal for `/entry-context`; target the current v2 bucket's pending/failed-turn file write for the existing quota fault (accepted editing snapshots remain a separate contract); and click the existing `Restore unsent draft` after each relevant reload. Every original error, field, message, omitted-file, attachment-removal, payload, timeout-window and exact two-turn assertion remains unchanged. No production source, Storybook story, native authorization, build, dictionary, model route or Commerce code changes.

One bounded existing Playwright invocation completed: `playwright test tests/e2e/failure.spec.ts --workers=1 --output=artifacts/test-results/genie-ci-40213689343 --timeout=15000` reported **4/4 PASS in 20.3 seconds**. The diagnostic per-case ceiling was lower than the unchanged repository default; assertions were not loosened. Its existing 6006 Storybook server and browser workers ended with the runner; no service remained on 6006. The output contained only a passing `.last-run.json`, which was checked and removed along with its task-owned empty output directory; previous artifact directories were untouched. No additional local browser run will be used as a substitute for the parent's next required CI.

Changed-file ESLint/Prettier and the plugin's `tsc --noEmit` (which includes `tests/`) pass. The existing CI 713-unit PASS is reused; no unit suite or full Playwright matrix was rerun. Product/build/language files are byte-identical to `163cc97d`, so build and i18n were correctly not rerun. The 19-product source aggregate remains `6d125345e1536570d143c0554bee21e94f5164d9593bb34f2dd7c336d029bf05`. The repaired fixture SHA-256 is `b22cdad4ed556cdd92dce7d48403d3ba63c5672165990d562540073bc8d0269b`. Actual WordPress/Cua acceptance remains with the parent on the existing 8888 instance; no WordPress instance, persistent browser, endpoint, global configuration, backup or worktree was created or changed.


## Workspace attachment entry and picked files (2026-10-26)

This batch starts from the accepted recovery candidate `bb5089ac` on `codex/genie-workspace-controls`; it does not replay or change the prior deployed recovery work. The confirmed standalone workspace defect was two App render exclusions: `!workspace` hid both the existing attach button and the existing AttachmentChips while the hidden input and owner-aware preparation/send logic still existed. Spec 13's attachment capability and ordinary workspace editing contract already cover these inputs. The approved prototype A remains the layout baseline (`proto/genie-r1` prototype README/CSS); the existing `2026-10-12-genie-openai-design/DOSSIER.md` A5 supplies the mature left-attachment composer pattern. This is restoration of an existing control, with the current approved EN/DE labels.

Only the two workspace exclusions are removed. History-view hiding, fresh native-owner checks, preparation, removal, send gating, failure/Restore and busy A2 editing are unchanged. The existing attachment-container CSS selector now includes the workspace; every property value remains unchanged and the already shared 44px attach-button rule is reused. No global tokens, marketing/body copy, model/API route or other module is edited.

The CSS delivery path is the existing tools-app pipeline: `App.tsx` imports `./genie.css`; the `genie` entry in the native WP-scripts webpack build emits `build/genie.css` and its RTL twin. `Linker\Tools\Assets` registers that CSS under `linker-tools-genie` with the native asset version. `Genie\Entries::dock_assets()` enqueues the style on frontend requests, including the standalone workspace whose shortcode mounts the same app. This file is tool application CSS, not the site-wide WindPress volume; no additional stylesheet channel is introduced.

The existing full upload/remove/payload case now mounts the workspace and verifies its real attach-button click, visible filename/remove control, attachment-only send gating, prepared PDF payload and chip clearing after send. Before the source repair it failed because no accessible `Attach a file` button existed. The existing `completed-with-next-draft` case also mounts the workspace and verifies visible controls plus A2 text/PDF preservation during Retry; its other helper variants remain unchanged. No cases or matrix were added. A bounded existing App selection reports **14 PASS**, covering those paths, cut-stream attachment retention and conversation navigation. TypeScript, changed-file ESLint and Prettier pass.

One `npm run build` and `npm run build:check` pass. The same three webpack performance recommendations remain visible. Of the 33 observed build/language files, only **five** change: Genie JS, CSS, RTL CSS, asset PHP and manifest. The other **28** files are byte-identical, including Hero, marketing, inquiry-handoff, configurator, preview, shared chunks, all their CSS and every PO/JSON/MO. The PHP layer and entire Commerce plugin are unchanged. No i18n regeneration was needed: the strings and existing catalog bytes did not change.

The native manifest's full 109-source/input aggregate is **`e8e2bb180e36c538f314b23eeb4bb16620fded903542bdda61b63064635aff85`**, using sorted `SHA + two spaces + plugin-relative path + LF` rows. Exact source/test/generated hashes are:

| File under `plugins/linker-tools` | SHA-256 |
| --- | --- |
| `src/genie/App.tsx` | `1b5750f976fbb82032f5d740987503b98604602a0ee13aa69df8330aec50fe5d` |
| `src/genie/App.test.tsx` | `3309955311ee53b04a99660d7e9a8b3c79dd0927d3a3c413179ba619ab5bccb2` |
| `src/genie/genie.css` | `7792b76492fe7237c9536c4c31bc245be09eaca11a4a24f8ccd3c23c6c817363` |
| `build/genie.js` | `d56ff0471c2cb0a880bafb1f39bede08631b6850ddf430db2e97aacfc0ecd9cb` |
| `build/genie.css` | `551029eb4cff40ab01fe7990ea2a9e3c71f4d6a0fb5b98afc2f70c184d2f639c` |
| `build/genie-rtl.css` | `a6f9306f55454740a197ed56b8596b6d92376527d8ed154b8fe28f359df6a934` |
| `build/genie.asset.php` | `5168161d085d3d32077de5d5ff13da77ca11f82bc846975d6b43ca3d5834a04b` |
| `build/manifest.json` | `7f3cb7426912ca7b20d4373166505ff9feba664df8f465c901655735d64ee974` |

AGENTS, the two existing full-site tracked edits and all untracked evidence are preserved. No WordPress instance, Storybook/browser, production/mail/model operation, backup or extra worktree was started or created. The parent owns complementary source/generated review, CI, real WP/Cua EN/DE and affected-width acceptance, publication and deployed readback. Component/source success is not claimed as visual or production acceptance.

Startup attachment-state follow-up (2026-10-26, after `6d08b83f`): the parent's actual WP/Cua run found the attach button still enabled while native identity was loading and the editor displayed `Opening Genie`. App now disables that existing button solely when `draftContext.phase !== 'ready'`. Model waiting and file preparation are not added to its gate, so a ready editor still accepts the next A2 draft. The existing send-disabled background `#ededed`, color `#afafaf` and `cursor: default` also style the attach-disabled state. The generic button-hover selector excludes disabled buttons inside `:where`, retaining its original specificity and the enabled controls' styles. CSS continues through the same tool-app import/build/enqueue path described above; no global WindPress, labels or catalog changes are involved.

Only the existing `native lookup pending accepts no ordinary input, outage Retry makes a usable editor with zero automatic turn` case is extended: attach is disabled during pending lookup and outage, then enabled after successful Retry. Its original ownership, no-automatic-turn and explicit-send assertions remain. This one case passes (**1 PASS, 77 skipped**); TypeScript, both changed TS files' ESLint and all three changed source files' Prettier checks pass. The prior 14-case App result and the parent's completed DE390 recovery/PDF/Restore and DE1440 ready-control Cua paths are reused, not rerun. The parent will supplement only actual delayed-native-identity disabled/ready visual acceptance.

Exactly one further native `npm run build` and `npm run build:check` pass, with the same three webpack performance recommendations. Five of the 33 observed build/language files change (Genie JS, CSS, RTL CSS, asset PHP and manifest); the other 28 remain byte-identical, including every other entry, shared chunk and language file. There is no i18n regeneration because no string or catalog changes. The updated 109-input native source aggregate is `d88b2c3725dbf54eb62f0eef6014a366ac92b5fee004a48c3821a179127a5ca4`. Updated hashes for this increment are:

| File under `plugins/linker-tools` | SHA-256 |
| --- | --- |
| `src/genie/App.tsx` | `1ec7d99a9037962e1c6532f65a9e0f526ac7aa372c8d74b9c182e9c452427aad` |
| `src/genie/failureOwnership.consumer.test.tsx` | `d421c040cfc68eaf81d9494a4fbede1c3f6b49fdffd0f95aad670391291201c5` |
| `src/genie/genie.css` | `ebc33557450e3e268d479ab9a4d1d9d8728599973c2e142be318bd67647f3335` |
| `build/genie.js` | `9aed2a80b4dcc72a48e0775982c429c27fd0d187b3f2d2dcb67df35fff041b26` |
| `build/genie.css` | `c05fe49e608bcdad1060f960c17b3b54b63c787e617bd5f0aa249321c4367a77` |
| `build/genie-rtl.css` | `a75365a9a11397671009c24a3c592852f37a58d278902bee9f883ac5144a2c12` |
| `build/genie.asset.php` | `a8634e576fd0c7c815536093a895840ba87fe2bb65c7815e89a7f19ec67dea06` |
| `build/manifest.json` | `20ddcb85adcd57b97470295405dbf07528a8eef5c45491b04e4aa39a43cc2a38` |

The pre-existing AGENTS and two tracked full-site evidence edits retain their exact starting hashes. This increment creates no runtime copy, instance, browser run or backup; all existing untracked evidence is preserved. No full App/713/e2e run, push, merge or production action is performed here. Incremental review, the new-head CI decision and the narrow startup visual/readback gate remain with the parent.

## Normal loading feedback and German script catalogs (2026-10-26)

This independent batch starts at accepted source/generated head `0fa64fc4` on `codex/genie-loading-feedback`. The parent supplied actual DE390 production evidence `Q/genie-workspace-live-de390.png`: normal native revalidation displayed English `Opening Genie…` with error styling. The preceding attachment-disabled and complete ready/retry/PDF/Restore paths remain accepted evidence; they are not rerun or changed here.

There are two concrete causes. App and Hero use the error class for the ordinary loading phase (Hero also announces it as an alert and offers Retry). The PO already translates `Opening Genie…`, but its sole build reference is Configurator, so neither actual Genie nor Hero JSON contains it. A bounded source-import and emitted-bundle audit also finds other Hero static UI terms whose existing German translations are assigned only to Genie. The complete before-fix missing list is:

| Actual consumer | Missing static msgids | Repair |
| --- | --- | --- |
| Genie and Hero | `Opening Genie…` | Replace these two normal-loading uses with `One moment…` / `Einen Moment …`, referenced to both scripts. Configurator's original opening text/translation remains unchanged. |
| Hero | `Choose a file` | Add its actual Hero consumer reference; keep `Datei auswählen`. |
| Hero parts-list UI | `In our range: %s`; `Not in our range.`; `Skipped.`; `Which model does this line mean?`; `This line needs your confirmation.`; `Add the product to the solution draft`; `Add %d products to the solution draft`; `Your parts list`; `%d ×`; `Row %1$d: %2$s`; `Row %d: skip`; `Skip this line` | Add the missing Hero build references for these 12 existing static wrappers. Reuse their existing German translations and placeholders. |
| Hero product UI | `Currently unavailable` | Add its Hero build reference; retain the existing `Derzeit nicht verfügbar` translation and the Woo stock predicate. |

These are 15 distinct old msgids (16 consumer/msgid pairs). Model replies, file names, row text, option labels, model/product names, quantities, prices and stock facts are left as supplied. EntryInbox's page-question labels are Genie-only consumers, so their absence from Hero is not a defect. Three imported Configurator publication messages (`This solution needs a new calculation before the next step.`, `The current product data could not be checked. Your entries are still here.`, `New calculation required.`) are removed by tree shaking from both scripts and are excluded. Native load failures, failure/retry, conflict, saved-draft warning, thinking/history states, explicit Restore/reselection, file preparation and refusal messages already have their actual consumer translations; they are preserved. In the authoritative PO, all 510 previous entries retain their exact msgid/plural/msgstr values, none is removed, one new waiting entry is added, and 14 existing entries only gain the missing Hero reference.

The initial and final waiting draft is EN `One moment…`, DE `Einen Moment …`. Self-review: it reports only a temporary wait, fits both initial open and normal revalidation, names no internal identity/lease mechanism, and promises no upload, deadline or successful outcome. Existing natural Sie-form failures and recovery instructions remain verbatim. The parent copy counter-review accepted the pair and explicitly rejected more specific checking/upload/completion claims. Applying the copy skill here adds only the tool's transient feedback dimension, with no new industry/category term or marketing claim:

- [x] Encyclopedia loaded (non-PDP): one new dimension; category words attested or absent.
- [x] Hard Stops 1–9 hold on every changed visible line.
- [x] Actor: no second-person imperative assigning the reader a task.
- [x] Future: no invented customer trajectory or motive.
- [x] Weight: no small service slice presented as the whole offer.
- [x] Duration: no unsupported continuing-action or time claim.
- [x] No slogan formulas.
- [x] No banned brand on this surface.
- [x] Quotes: no invented customer quote or testimonial.

App and Hero now select `linker-genie-app__status` only during existing native loading. This class shares the existing photo-prompt layout and muted text values, through the same imported `genie.css` / native build / `linker-tools-genie` enqueue path. No numeric style value, global WindPress channel or state transition is added. Hero uses role status while loading and retains role alert, the error class, original failure text and Retry for actual failure. App retains its existing status role and failure Retry behavior. Normal Hero loading no longer offers a failure Retry button. Unknown-owner content gating, native verification, permissions, retained recovery, file preparation and sending code are untouched.

Only four existing cases run: the App pending/outage/Retry case, the Hero initial scoped failure case extended with one controlled initial-lookup gate, and the two existing script-local German catalog cases. They report **4 PASS, 99 skipped**. Both UI cases distinguish neutral loading from the original failure feedback, retain the original hidden-owner/no-automatic-send assertions, and finish through fresh verification. The two JSON cases exercise `@wordpress/i18n` with each real native catalog and preserve their previous publication/confirmation assertions. No test case or matrix is added. TypeScript, the five changed TS files' ESLint, all six changed frontend files' Prettier and diff whitespace checks pass. The prior full recovery, 14-case App and ready native Cua evidence are reused.

After freezing source and copy, exactly one `just i18n-tools` and one `npm run build` run successfully; `msgfmt --check` and `npm run build:check` pass. The same three webpack performance recommendations remain visible. The post-generation source/emitted-bundle/catalog audit finds **200 Genie** and **152 Hero** emitted static msgids with **zero missing German entries** in each script's own JSON. No generated JSON is hand edited. Of 31 tracked generated build/JSON/MO files, **10 change**: Genie JS/CSS/RTL CSS/asset, Hero JS/asset, manifest, the two corresponding DE JSON catalogs and DE MO. The other **21 generated files remain byte-identical**, including Hero CSS/RTL CSS, Configurator, marketing, inquiry handoff, preview, shared chunks, the other two DE JSON catalogs and Chinese MO. Both PO files are source rather than generated outputs; only the targeted German PO changes. PHP, Commerce, site content and global CSS are untouched.

The native manifest's 109-input source aggregate is `53809b97d47b3a3223f7e5233012071ebc11bac16ebbd2120b8931d40cf1f973`. Source and generated SHA-256 values for the changed delivery files are:

| File under `plugins/linker-tools` | SHA-256 |
| --- | --- |
| `src/genie/App.tsx` | `44f96ebc09a80e72a9c32c18269479ec04175ac932619b6e84da7a99c2597f77` |
| `src/hero/Hero.tsx` | `f0077b8fbf0e11a602b4604e79605bfc9c2d3ef6c77f3a0e633ba3339abb4b20` |
| `src/genie/genie.css` | `66750bab0446faa2b6901c74b1aec9113fb9e24165617fc815f96c0cc1eb2fa4` |
| `languages/linker-tools-de_DE_formal.po` | `f4ba84d85cf02f549727480c9882309b518e04be0b62bca0457766cb63387790` |
| `build/genie.js` | `a895d4bbc3deb14ac805f11b3a7e90b8d65171e20e34ec90e1fa39bee92b6c75` |
| `build/hero.js` | `3b5b5285ce44ade91bdd26c950101455ccefc3daf76f7570f92d55ff6b25193d` |
| `build/genie.css` | `0c341edfc004ac5420b2b9d41136b8a7a10ac7ca1cf217b549616a063b2a73c8` |
| `build/genie-rtl.css` | `70d681da51581014728d7ee094ba99775c91255b4f83a2ca2090b31e0a9d42ca` |
| `build/genie.asset.php` | `b4af1acfe31f241616cec2358b3e1e67bf25432bc89c169f6a378864123e4889` |
| `build/hero.asset.php` | `cb19da4bccea122d5e6bd63f3e8ff37ec2229d15efc70b6167682e720e3bdb0d` |
| `build/manifest.json` | `636d3eac2744d06e46633286deb73afddf5ed64bae7b035d879de5406a162f7f` |
| `languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json` | `245a2bdb4fdae3ebd88633eede3a016fd90c90805102eb559dbe76c43ea351ad` |
| `languages/linker-tools-de_DE_formal-6796211aef57736d0923df38ef696ad2.json` | `89cb249d0cd2a684b73e87adb31aa5ac5dffcb34e917f27a861a27abfa3f23c5` |
| `languages/linker-tools-de_DE_formal.mo` | `121c9e9388cd8c05c24efa167207508372715724e2fb935e8faa4ed9854b94b0` |

The three pre-existing tracked edits retain their starting hashes and all untracked evidence is preserved. No runtime copy, service, browser, model/mail operation, backup or extra worktree is created. Incremental Spec/Standards review, new-head CI and actual neutral-loading EN/DE visual/deployed readback remain parent delivery gates; the already accepted ready/recovery chain is not reopened by this batch. No push, merge or production action is performed here.
