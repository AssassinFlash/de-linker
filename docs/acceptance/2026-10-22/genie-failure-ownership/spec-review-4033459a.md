# Independent Spec review — candidate 4033459a

**SOURCE BLOCKED.** The original five Spec findings close for this candidate, but the complete review retains two concrete async/storage defects. This is not a browser, bundle, CI or online acceptance result.

## Exact candidate

Development worktree: `/Users/chesterjohn/.codex/worktrees/privacy-visual-audit/de-linker`, branch `codex/genie-failure-ownership`, full baseline `eb097915`. I independently read `source-files.json`, verified all 17 product SHA-256 values, and recomputed aggregate **`4033459a57bf17cb89fd9d9187cde4d84120ae1dfe097a9d89b39a34a209b561`**. The original fixed c5cb source remains unchanged at `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-before-c5cb-20261021T233523194452Z/`, and its BLOCKED report is preserved as `spec-review.md`.

Reviewed the complete product ownership chain and its consumers, including all nine source deltas from c5cb: App, Hero, homepage controller, editing draft, entry draft, failure codec, journal, entry inbox and shared failure hook. The other eight source hashes are unchanged. This review includes permanent replacement consumers and the source-level browser plan; it does not equate their existence with runtime/browser completion. The contract remains `../full-site/ordinary-failure-repair-design.md`.

## Remaining blockers

### P2 — denied-read fallback can acknowledge consumption then revive old durable text

`shared/ownedFailure.ts:365–367` falls back from a failed `begin()` storage read without recording or conservatively handling an unknown durable counterpart. `consume()` checks disk only when `runtime.counterparts` already has an entry (lines 618–661). A read-denied fallback has none, so it successfully consumes only memory while an old durable revision of the same attempt remains.

Independently executed actual journal sequence: durable editing revision → deny `getItem` → update the same editor into memory → restore storage → consume memory → discard only window journal → read same native owner. Consumption returns true, but the old durable text reappears. The consumer assertion explicitly allows a safe failed consumption that retains the current memory draft; it fails only when successful consumption permits revival. This matches the parallel Standards finding already delivered to the implementer.

Required closure: the read-failure path must not treat “counterpart unknown” as “none exists.” Before acknowledging consumption, verify and precisely handle any durable same-attempt candidate, or fail closed while retaining the memory revision and warning. Preserve other scopes/attempts, and reject stale cursors. The writer must not guess an unseen old revision or delete a newer one.

### P2 — obsolete homepage dictation end clears the current session's handle

`src/hero/controller.tsx:393–395` passes an unguarded `() => { recognition = null; }` to `startDictation`. Native identity change stops A and clears its handle, but its asynchronous native `onend` can arrive after B starts another session. The old callback then clears B's handle. A subsequent Voice action starts a third session rather than stopping B, and Close no longer reliably owns B's active recognition.

Independently executed actual `startHero` plus production `startDictation`, with only the native SpeechRecognition constructor/events controlled: start A → fresh native B focus → start B → deliver A's delayed onend → click Voice to stop B. **B.stop is called zero times and another session is created.** No physical microphone or browser speech service was used.

Required closure: only the still-current recognition operation may clear its handle. Guard both owner/epoch and the exact session/operation, because stop/error/end followed by a new session can also race within one unchanged owner. Natural end must still clear its own session; Close/identity invalidation must stop the actual current one. Preserve the existing no-late-transcript guarantee.

Both blockers were reported to the parent and implementer before further edits. No speculative extra implementation scope is requested.

## Original findings and added boundary review

| Original finding / new repair boundary | Source and independent result |
|---|---|
| Real 413 attachment refusal / 409 conflict return to editing | Same pending attempt is converted to editing without consume-and-resurrect. Real exported `TurnError` codes replace the prior plain-object fixtures. Original two actual App pagehide counterexamples pass; permanent App/Home consumers also cover valid-A return and zero automatic turns. |
| Missing-only exchange | Both callers use the missing-name fallback; journal validates a readable proposal before durable/memory writes. Original actual App two-way exchange counterexample passes; the valid earlier attempt remains readable. Invalid empty editing proposals remain rejected. |
| Home visibility lifecycle | The controller now checkpoints hidden, revalidates visible, and cleans up the listener. Actual controller counterexample passes while still requiring private A text to clear and a new native lookup. |
| Empty → retype attempt | Exact editing lookup includes a non-active record. Successful explicit-empty consumption releases that editor, allowing a new attempt; failed reads remain distinguishable. Original A→B→valid-A retype counterexample passes. Permanent non-active A2 coverage is relevant and retained. |
| Late ENTRY completion | Origin lease/handling generation are checked after awaits; `finishEntry` compares exact scope/ID/text/mode/source path and raw slot, avoiding foreign-scope cleanup reads. Original actual App + `rememberEntry` B-byte-preservation counterexample passes. |
| A2 accepted while A1 sends | Removing blanket sending checkpoint guards preserves the new editor; A1 success does not clear A2 files, and failed/returned A1 is offered for explicit restoration. Actual PDF consumers exercise success/refusal/conflict/upstream, unavailable authority and Retry. Source retains A2's own owner rather than rebinding its text. |
| Known durable→memory fallback | Exact prior entry/revision plus complete raw/readback checks address the known-write-failure path and preserve other records. The denied-read variation above remains open; the known-counterpart green does not close it. |
| Attachment-only empty-question codec | The exception requires an independently owned upstream failure, no editing flag or prepared uploads, and nonempty omitted names. Unknown ownerless v1 and empty editing drafts stay rejected. Restored empty retry payloads cannot send; the existing reselection notice remains. Relevant actual App/Home consumers passed. This is narrow codec compatibility, not permission for arbitrary empty turns. |

Unknown ownerless v1 is still inactive and byte-identical, native scope/attempt remains independent from marketing provenance, and fresh transport authority still follows queued thread reads. No model, server authorization, API route, knowledge, inquiry or mail change is introduced by the nine repair deltas.

## Independent execution and precision

Isolated source/evidence root: `/private/tmp/genie-spec-4033459a-f14_4wzx/`. Product source was copied read-only from the frozen development tree and its 17 hashes match the candidate. Existing installed dependencies were reused; no dependency installation, build/i18n, product/test edit, e2e/browser or instance operation occurred.

- `original-six-final-results.json`: **6/6 original independent consumer assertions PASS**. In the visibility case, an inaccurate secondary fixture expectation that an already mounted nonce-A config must become nonce-B was replaced with the actual required fresh native request-count increase. The private-text-clears expectation is unchanged. The original c5cb case remains red at that primary privacy assertion.
- `related-complete-results.json`: **425 relevant Genie/Hero/marketing tests PASS**. The isolated copy includes the existing PHP attachment limit and generated translation fixtures that those suites read. An existing outage test initially clicked Send after seeing the filename, while the real FileReader could still be preparing and the button disabled. Only in the isolated test copy, I awaited the existing Preparing-file state to end before the same click/assertions. This establishes the claimed Send precondition; no product assertion was removed. The frozen working-tree tests are unchanged. The implementer was notified to make that permanent fixture deterministic.
- `memory-read-counterpart-results.json`: **1 independent denied-read consume counterexample FAIL**.
- `dictation-epoch-results.json`: **1 independent actual-controller delayed-dictation counterexample FAIL**.
- `src/genie/spec-independent-counterexamples.test.tsx` retains the original six plus the new actual controller assertion. The additional journal assertion is appended only in the isolated copy's `src/genie/shared/ownedFailure.test.ts`.

The producer's reported full tools 548 PASS / 1 existing generated-warning failure is a separate, broader run. Its deferred catalog generation is acknowledged and is not a substitute for parent-owned build/i18n. This review does not close screenshots, keyboard/geometry, native auth/storage browser cases, CI, production readback, or the wider whole-site goal.
