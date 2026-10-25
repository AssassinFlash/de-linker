# Independent Spec review — candidate c267ce64

Verdict: **SOURCE PASS for the complete ordinary Genie failure/editing ownership candidate.** Both concrete P2 blockers retained against `4033459a` are closed on this replacement. This is not a generated-bundle, browser/visual, CI, production, physical speech-recognition or full-site acceptance result.

## Exact candidate and review continuity

Worktree: `/Users/chesterjohn/.codex/worktrees/privacy-visual-audit/de-linker`; branch `codex/genie-failure-ownership`; baseline `eb097915`. Independently verified every product, test/helper and auxiliary hash in [source-files.json](source-files.json). Recomputed the 17-product aggregate **`c267ce64e8b9f958914c69d65ea9530fdafcd09beb5b48f62c03b8c5ba711a41`**, using the manifest's sorted `SHA256 + two spaces + relative path + LF` algorithm.

The complete ownership chain, full baseline diff and all nine initial repair deltas were already independently reviewed against the fixed original `c5cb` snapshot and replacement `4033459a`. Their [original BLOCKED report](spec-review.md) and [403 BLOCKED report](spec-review-4033459a.md) remain valid historical records for those exact sources. This review does not relabel either old candidate PASS.

I compared all 17 current products with the immutable 403 source root recorded in the manifest. Exactly **two** products changed: `shared/ownedFailure.ts` and `hero/controller.tsx`; the other **15 are byte-identical**. I read the entire journal and controller paths affected by this delta, their native-scope/context and dictation seams, the new permanent tests, the exact current auxiliary changes, [the repair matrix](review-repairs.md), [producer/reader census](implementation.md), and [the approved design](../full-site/ordinary-failure-repair-design.md). The full unchanged source review therefore carries forward, with the two previous blockers independently re-evaluated below rather than assuming that a green producer run closes them.

## Two remaining blockers closed

### Denied-read memory fallback and durable resurrection

`FailureJournal` now retains exact durable entry/revision evidence after an acknowledged write or verified candidate read. A subsequent get failure can enter the same owner's memory journal without treating that failure as proof of disk absence. Consuming memory first verifies the exact memory cursor, then compares the known disk counterpart's serialized entry/revision and the complete raw disk bucket before mutation/readback. Other attempts and active-order repair remain intact.

If no trusted counterpart exists, consumption must successfully read the durable bucket and prove this attempt absent. An existing unknown revision, malformed bucket, or another get failure returns false and preserves the memory draft; it cannot acknowledge deletion merely because the counterpart cache is empty. The change does not infer an owner from durable text or claim another scope.

The original independent sequence—durable editing revision → denied get → newer same-owner memory editor → storage recovery → consume → fresh window—now passes without reviving the old durable question. The permanent exact-consumption test, unknown-unacknowledged-write negative control, existing stale-memory/foreign-owner/unavailable-store controls, and actual App answer/fresh-mount consumer also pass.

### Late native dictation end and current stop handle

The actual homepage controller now allows an end/error callback to clear `recognition` only when its immutable native lease still belongs to the current context **and** the stored handle is that exact session. Checking both matters: a stop/restart race can occur without a principal change. Physical cleanup may finish during a same-owner auxiliary verification, while a replacement principal/thread epoch remains protected. A synchronously ended/refused start cannot install an already-ended handle.

The original actual `startHero` counterexample now passes: start A, rotate to B, start B, deliver A's late end, then use current Stop; B's actual recognition instance is stopped and no third instance is created. The permanent same-owner-session variant, old error, natural current end and teardown consumers also pass. The existing helper continues to reject stopped-session transcripts. This proves controller ownership/cleanup, not microphone permissions, audio quality or a real speech provider.

## Complete contract result

| Required behavior | Spec result |
|---|---|
| Native identity before ordinary text/file/dictation bytes; quiet homepage prefetch; cold lookup shared across independently loaded modules; fresh Send/Retry after queued thread work | Preserved in the unchanged reviewed native-scope/context seams. Storage-denied bootstrap has a verified window-only identity and usable composer; a cached scope or thread ID is not server permission. |
| Unknown ownerless v1 | Inactive and byte-identical. No migration by matching text, empty history or 403; new ordinary records use the separate v2 owner/attempt journal and no fabricated marketing entry ID. |
| Scoped v1 vs v2 arbitration | One verified selector prefers the current scope's valid v2 candidate; exact scoped-v1 migration is subordinate and requires durable readback before exact old-byte removal. |
| A/B separation and mounted UI | Revalidation checkpoints A under its original owner and quarantines text, filenames, prepared bytes, history and live output until verified. Confirmed B cannot display or send A's bytes; returning through the original valid scope permits explicit recovery, while a rotated session cannot reclaim it. |
| Scope buckets / attempts / CAS | Inactive A records survive B writes. Multiple same-scope attempts retain explicit insertion order; consuming one repairs active in the same exact CAS. Late cleanup cannot consume another attempt or strand the surviving candidate. |
| Unsent editing, Close, pagehide, New/Select and reload | Accepted text and prepared files retain their original owner/attempt as editing; prepare-pending or withheld files are explicit reselection names. Recovery is editable and starts zero model turns. Emptying consumes only that editor, including a non-active attempt, and new text receives a new attempt. |
| Real 413 refusal / 409 conflict | Returned question/files convert the same pending attempt to editing, avoiding consume-then-resurrect. The real exported `TurnError` classes/codes are exercised; pagehide and original-owner return retain the returned editor. |
| A2 while A1 is pending | A2's own text/real PDF and owner survive A1 success/refusal/conflict/upstream and auxiliary outage. A1 settlement cannot clear A2; retained A1 remains explicitly exchangeable. |
| Missing-only restore/exchange | Missing names form a readable editing question and remain through both exchange directions; journal rejects invalid proposals before they can poison or shadow an existing bucket. |
| Attachment-only empty question | Only independently owned, non-editing upstream records with no uploads and nonempty omitted names get the narrow codec exception. Retry has no payload until explicit reselect/Remove; arbitrary empty turns and ownerless v1 remain invalid. |
| Async model / prepare / ENTRY exits | Captured native owner, context epoch, exact attempt/revision and input/files/busy boundaries remain in all reviewed settlement paths. Late A marketing completion compares the exact entry bytes and scope instead of consuming B's source; the original independent actual App + `rememberEntry` counterexample still passes. |
| Memory fallback and copy | No failed read/write/readback is called durable success. Warning states the refresh/leave risk; its formal German version retains that meaning. Source remains recoverable only by its verified owner in this window. No false marketing ACK or reload guarantee is added. |

No server authorization, model route, API endpoint, knowledge source, product fact, inquiry, notification or mail behavior changes in this product set. New recovery controls reuse existing reviewed copy and presentation classes; actual EN/DE geometry and keyboard appearance remain a separate browser gate.

## Independent execution

Isolated source/evidence root: `/private/tmp/genie-spec-c267-o9hwroix/`. Copied the previous isolated harness, overlaid the current exact 17 product and 16 test/helper files, verified those copied hashes, and retained the original reviewer assertions separately. Existing installed dependencies were reused. No dependency installation, build/i18n, shared browser/instance operation, production write or product/test edit in the development tree occurred.

- `independent-spec-replay.json`: **8 PASS / 0 FAIL**. These are the original six actual App/controller consumers plus the original denied-get journal and late-dictation controller assertions. Expectations were not weakened.
- `related-c267-results.json`: **38 files, 431 PASS / 0 FAIL**. This is the current producer's 430 relevant Genie/Hero/marketing tests plus the retained independent denied-get journal assertion. The appended independent consumer file was excluded from this second run to avoid counting its duplicated base cases.
- The first isolated replay accidentally retained absolute imports pointing at the old immutable 403 harness. Its seven-pass/one-old-dictation-fail output is preserved as `harness-old-absolute-import-results.json`. Only those isolated module paths were rebound to the current c267 copy; the assertions were unchanged. That first run is a harness provenance error and is not a new c267 product red.
- The marketing outage fixture now explicitly waits until its real PDF is prepared and Send enabled before the same click. Seeing a filename alone did not establish that precondition. Its privacy, file retention and zero unauthorized-turn assertions remain unchanged.

The producer's broader full-tools result, **553 PASS / one old generated-catalog FAIL**, remains separate and accurately incomplete before parent build/i18n. This review did not run that broader suite or convert its generated-warning failure to a skip. The approved EN/DE warning is present in the source PO; generated catalog/runtime proof remains parent-owned.

## Documentation correction and remaining release gates

One existing subordinate sentence in `docs/specs/13-genie.md` still says that success, 409 and file refusal all delete “this record.” It contradicts the new immediately preceding owner/attempt contract and actual 409/refusal-to-editing behavior. I reported the narrow correction to the parent and producer: successful completion consumes only the current attempt; 409/refusal preserve it as editing, with unrelated attempts untouched. This is a documentation consistency fix, not a remaining defect in the 17 product sources. It should be corrected before publishing the specification, and its auxiliary hash refreshed without changing the frozen product aggregate.

Source PASS permits the next same-hash build/i18n/presentation and actual native browser gates. The planned 18 browser cases and manual EN/DE1440/390 state review still need to prove initial pending/outage, storage exceptions, real cookie rotation/login/logout, restore/retry, file behavior, keyboard and visual states in the built consumers. CI and required backup/deployment/live readback are not complete in this report. The wider full-site goal and its unrelated pagination/Contact/marketing workflow gaps remain open.
