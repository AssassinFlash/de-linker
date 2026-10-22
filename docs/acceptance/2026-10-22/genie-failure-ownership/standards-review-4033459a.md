# Ordinary ownership replacement 4033459a — Standards review

**Status: BLOCKED by one remaining same-attempt durable-consumption defect.** The three original independent findings now pass their unchanged probes, but that does not approve this replacement. The `standards-review.md` report remains the rejected original candidate record and has not been overwritten.

This review binds all 17 production files to aggregate `4033459a57bf17cb89fd9d9187cde4d84120ae1dfe097a9d89b39a34a209b561`, relative to the original fixed base `eb097915`. Every source was independently hashed against the updated `source-files.json`; all 17 matched. Comparison with the byte-preserved `c5cb` tree established exactly nine changed production files: App, Hero, controller, editingDraft, entryDraft, failure, ownedFailure, useEntryInbox and useFailure. The other eight, including nativeScope, DraftContext, the hook, session and shared components, are unchanged bytes and retain their original full-review scope. The replacement's permanent tests and updated specification were also reviewed rather than checking only the original three defects.

The producer preserved the replacement's complete 36 manifest files at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-before-4033459a-20261022T000607370392Z` before starting another repair. Subsequent working-tree changes must not be represented as this candidate's result.

## Remaining blocker

**P2 — a transient durable read failure still makes a consumed older editing record revive after refresh.** In `src/genie/shared/ownedFailure.ts:373`, `begin()` falls back to `keepMemory(state, owner)` after `getItem` throws, without a known durable counterpart. The new cleanup at line 608 checks the durable entry only when `runtime().counterparts` contains one. No counterpart information is therefore treated as permission to consume memory successfully even though the old durable entry exists.

Actual `FailureJournal` reproduction:

1. Persist a valid editing record for A/attempt X.
2. Make the storage adapter's `getItem` throw temporarily.
3. Preserve newer valid editing bytes under the same A/X; the real journal returns a scoped memory cursor.
4. Restore the storage reader. The current candidate correctly shows the new memory text.
5. `consume(memoryCursor)` returns **true**.
6. Rebuild only `window.__linkerGenieFailureJournal`, retaining persistent storage as a fresh window would. The original A/X durable editing record is recovered again.

The new set/quota failure test passes because that path supplies an exact durable cursor. It does not cover the `begin` read-failure fallback. The storage contract explicitly distinguishes unreadability from absence. A fix must retain trustworthy old durable revision/entry evidence when available, and otherwise verify absence or refuse consumption while keeping memory/warning. It must not delete an unknown or newer same-attempt durable revision merely because its owner matches. No cross-principal disclosure was demonstrated by this finding.

The parent and producer received the actual red immediately. The new fixture is an external direct consumer of the production class, with normal durable data preserved; it is not a static inference or mocked replacement implementation.

## Original closures and wider replacement review

- **Original A1/A2 preservation:** the unchanged actual App probe now passes. Both surfaces remove the blanket sending checkpoint guard, retain a separate accepted A2 owner/files, and guard success/refusal/conflict/upstream settlement from taking its field. `returnToEditing` keeps refusal/conflict on the original pending attempt; `parkFailure` exposes an occupied older result through existing explicit Restore. Actual permanent consumers cover prepared PDF bytes and both directions of the editing exchange.
- **Original Hero visibility:** the unchanged actual startHero/workspace control passes. Controller now handles hidden checkpoint, visible fresh check and symmetric listener cleanup; its provided-context hook does not create a competing lifecycle handler.
- **Original set/quota memory→durable cleanup:** the unchanged direct journal probe passes. The implementation validates the precise current memory raw/revision before touching disk, compares the known durable revision and serialized entry, retains unrelated attempts, and fails closed when the known counterpart cannot be removed. Its remaining unknown/read-failure branch is the blocker above.
- **Invalid proposal protection:** journal begin/save validate a readable record before writing or creating a shadow memory record. Missing-file-only editing displacement uses its explicit filenames as fallback question. The permanent invalid-proposal and unreadable-store tests retain the original valid bucket. No arbitrary empty editing state was made readable to solve this case.
- **Empty-question codec:** the exception is limited to native-shaped owner, nonempty attempt, non-editing upstream, no actual uploads and at least one nonempty omitted filename. Independent codec probes passed the valid retained state and eight rejecting controls: editing, ownerless, invalid scope shape, no omitted filename, empty filename, pending kind, truncated kind and actual uploads. The valid record's empty Retry returns no payload. Actual App/Home consumers additionally test the existing reselection notice, zero automatic/model turn and B filename isolation. The exception does not bypass native scope authorization.
- **Explicit empty editor:** exact own-attempt lookup includes non-active A2. Successful consume releases the editing owner so A3 gets a new attempt, avoiding the window consumed-tombstone exclusion. Failed lookup is distinct from absence and warns. Permanent actual App/Home consumers exercise returned A1, clear non-active A2, preserve A1 and recover A3. This correction remains subject to the read-failure consume blocker when a memory version shadows disk.
- **Late marketing settlement:** `accept` captures origin lease and handling generation before await, rechecks native context after ask, and guards obsolete catch/finally. `finishEntry` does not invoke a foreign-scope reader; it compares the current scope plus entry ID/text/mode/source path and performs synchronous raw-slot/readback checks. A failed exact completion retains the source and avoids settled ACK. The actual App/rememberEntry permanent case keeps B's exact durable slot after late A completion. No new marketing protocol, arbitrary cache owner or server authority is introduced.
- The full revised source preserves fresh Send/Retry checks after queued thread reads, native model/conversation authority, unknown v1 inactivity, independent scope/attempt buckets, missing-file decisions, memory-only warning and quiet initial Hero appearance. It adds no unsupported quota/TTL, CSS pipeline, PHP layout, business inquiry, mail, model-channel or knowledge-source change. No additional Fowler smell merits a blocking refactor.

The permanent consumer additions use actual exported `TurnError` and production attachment/conflict codes; they now exercise those branches rather than plain-object upstream classification. The 73 App/controller consumers and 15 journal tests cover substantially more than the original green total, but the new real read-failure counterexample shows why counts alone do not establish closure. The PO and browser spec are unchanged from the reviewed original; the specification adds the intended repaired contracts without claiming a browser/deployed result.

## Independent execution and provenance

All fixtures remain outside the checkout at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/`. Their real-module imports were not replaced by a second journal or UI implementation. Identity/history/model HTTP are explicit doubles; no browser, instance, build, dependency installation, production action or real model/email call was used.

| Run against this candidate | Result | Raw log SHA-256 |
|---|---|---|
| Original pending-editor, memory-update and visibility probes, unchanged | **4 passed** (visibility includes a workspace control) | `5b1a956a3267f35fc629fc954dc3fa4a90a5eb0886b00b5a5d96080e69f3b191` |
| New same-attempt transient get failure → memory → consume → fresh runtime | **1 failed** | `4ab936ca7ec68d94bc6a1cb7844ebdbade4c864fbac932f9d752a424953099e8` |
| Owned attachment-only codec + rejecting boundary controls | **9 passed** | `adb7a9b5e199e8e34cceafc2bd25095a3269263936bbb033b59e5e667efe6e22` |

Original replay log: `replay-4033459a.log`. New red fixture: `journal-get.test.ts`, SHA-256 `6d784cc65792ef811b469125cf4d2b515f5182a36f86b2f825da0e70c51501af`; raw log `get-fallback-4033459a-red.log`. Codec fixture: `codec.test.ts`, SHA-256 `08a3f8808e0bb70cfc91fc485a8e384efba7475ce95dd03652965b23609d38b6`; raw log `codec-4033459a-green.log`. Replay with the external `vitest.config.mts` and the documented test-name filters; preserve these original outputs when a new candidate is tested.

The producer reports 425/425 related tests and 548 complete tools tests passing, with one old generated-catalog failure. Those are producer executions and the catalog is deliberately awaiting parent build/i18n. This review did not run a competing broad suite or treat a stale bundle as a new source defect. Generated source matching, translated catalogs, official presentation, the 18 planned native browser cases, CUA, CI and live readback remain distinct gates after the next repaired freeze.

This 4033459a source candidate remains **not approved for release**. Re-review the next exact source hash and replay both the original passing controls and the remaining get-failure counterexample before changing that status.
