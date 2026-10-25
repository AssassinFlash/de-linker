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

All tools `build/` and generated JSON/MO files currently equal main and intentionally do not claim this source candidate. They require the current native build/i18n pipeline after integrated-source review; the old branch's generated outputs were not used. Independent integrated-diff Spec/Standards review, generated manifest/catalog checks, affected-state Computer Use and release/deployed readback remain parent-owned delivery gates. No full suite, browser, local instance, product model/mail request or production operation ran in this batch. No worktree, backup, dependency installation or temporary report copy was created.
