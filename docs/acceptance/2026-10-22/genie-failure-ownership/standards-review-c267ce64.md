# Ordinary Genie ownership c267ce64 — final source Standards review

**PASS for this exact source candidate. No remaining actionable Standards blocker was established.** The original `c5cb` and intermediate `4033459a` BLOCKED reports and their failed logs remain historical evidence; this report neither overwrites them nor relabels their results. This source PASS does not approve an unreviewed rebase, generated bundle, browser state, CI result or production deployment.

Fixed originating base: `eb097915`. Current 17-product aggregate: `c267ce64e8b9f958914c69d65ea9530fdafcd09beb5b48f62c03b8c5ba711a41`, calculated independently from sorted `SHA256 + two spaces + relative path + LF`. All **17 product sources, 16 test/helper sources and 3 auxiliary PO/spec/e2e files** matched the current `source-files.json`. Against the preserved 403 snapshot, only `shared/ownedFailure.ts` and `hero/controller.tsx` change production bytes; the other 15 match exactly. Three test files change, and the PO, specification and planned browser spec remain identical to the complete replacement review.

The previous full reviews covered the complete original diff/new files and all nine replacement production changes. This final pass re-read both new production deltas and all three changed test diffs, their actual call sites and surrounding storage/dictation code. Hash equivalence, rather than a fresh unsupported assumption, retains the unchanged files' prior full-review coverage.

## Last two boundaries now closed

**Read failure versus durable absence.** `trustDurable()` records the exact serialized entry and revision only from a successful acknowledged durable write or a readable selected durable candidate. Those are known bytes, not an inference from a missing map entry. A later read-failure fallback can retain that prior evidence for its same owner/attempt. Memory consumption first verifies its exact current memory raw/revision, then either:

- Matches the known durable entry/revision, performs synchronous full-slot raw CAS and exact readback, and removes only that attempt while repairing the active pointer; or
- If there is no trusted counterpart, performs an actual durable read proving that this attempt is absent. An existing unknown counterpart or unreadable bucket refuses consumption and retains the memory state/warning.

Unrelated attempts and native principals remain outside the cleanup target. A newer durable revision or changed content at the same revision is not deleted merely because its owner matches. This closes the remaining independently reproduced 403 read-failure sequence; a new-window journal no longer recovers the original consumed disk text after storage becomes available. Storage failure remains explicit rather than being represented as durable success.

**Late dictation end versus current session.** Homepage controller's callback now holds the original native lease and exact returned `DictationSession`, and clears `recognition` only if both still match. It uses `owns` for cleanup through a same-owner auxiliary lookup, while transcripts still require ready/valid identity. An old principal/thread epoch or stopped session's late end/error cannot remove another session's current Stop handle. The synchronous-end flag also prevents installing an already-ended handle after native start refusal/completion. Existing `startDictation` stops accepting transcript bytes on stop/end/error; no speech provider or automatic microphone behavior changed.

Actual permanent `startHero` consumers cover same-owner stop/restart and principal turnover, late old end/error, current Stop, natural completion and teardown. The existing marketing outage fixture now waits for real PDF preparation and enabled Send before introducing the outage, preserving its prior security assertions rather than weakening them.

## Complete candidate conclusions retained

- Ordinary input, files, dictation, pending/failed turns and editing drafts use native scope plus an independent attempt. Native REST/cookie/conversation authority remains unchanged; marketing metadata is optional provenance, not ordinary identity. Cold dual-bundle coalescing remains separate from fresh post-thread Send/Retry verification. All required scope/epoch invalidation and surface quarantine paths from the original review remain present.
- Accepted A2 text/prepared PDF is checkpointed independently of pending A1, including Close/pagehide/identity transitions. A1 success/refusal/conflict/upstream does not take A2's field or files. Returned refusal/conflict preserves A1's attempt as editing without consuming/reusing it. Explicit clear targets its own editing attempt, including non-active A2, releases it after success and permits a new A3 owner.
- All journal writes validate readable records before touching durable or memory buckets. Missing-only editing gets a real filename-derived question. The narrowly owned upstream omitted-only empty-question compatibility remains non-editing, has no upload payload, and cannot form an empty Retry/automatic Send. Unknown ownerless v1 remains inactive and untouched; no arbitrary count cap, TTL or new storage surface was added.
- Late marketing accept/ask completion retains origin lease/handling generation and removes only the exact scope/entry/raw slot. It does not clean up through a foreign-owner reader or delete B's new source. Native owner alignment, source durability and absent/missing-file decisions remain the reviewed contract.
- The complete candidate introduces no PHP layout, snippet, CSS pipeline, business inquiry change, mail change, model route, knowledge source or product-data mutation. Shared modules keep authority, persistence and UI responsibilities distinct. No Fowler smell independently justifies a blocking redesign.
- Approved warning copy is unchanged in the PO. The generated-catalog failure remains a parent build/i18n gate, not a source failure silently hidden by skipping its test. Generated manifest/catalog matching must be inspected after build. The 18-case native browser spec is unchanged and remains unexecuted by this reviewer.

## Independent executions

All external probes are in `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/`, importing actual current production modules with the repository's Vitest/setup/package runtime. No source/instance/browser/build/dependency/rebase operation or real model/email call occurred. Test doubles explicitly control native identity/history/model responses; actual App, startHero, storage journal and file preparation consumers remain real.

| Execution on exact c267ce64 bytes | Result | Raw log SHA-256 |
|---|---|---|
| Unchanged original/intermediate independent probes plus codec controls | **15 passed**, 5 files | `5c613c466406c5161990ee2e1e800d09e6f75172ab259d3879063291232864f1` |
| Actual permanent ordinary App/Hero, journal and marketing consumers | **130 passed**, 3 files | `a1fe5cac50e4fbc99570f862e1c389a08415ed42aaa4f1576a74e11bf4db3b85` |
| Additional independent exact counterpart/absence controls | **6 passed**, 1 file | `2741bf64692688802b05919c1ba927d358ee1ec69cac32fadb77b1b8f88349fe` |

These runs overlap existing test coverage and are not claimed as 151 distinct new cases. The exact commands were:

```text
# Plugin cwd; external config includes only external real-module fixtures.
node_modules/.bin/vitest run --config /Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/vitest.config.mts -t 'standards accepted next draft|standards consuming a memory update|standards visibility-only resume|standards transient get failure|standards owned attachment-only|standards empty-question rejects'

node_modules/.bin/vitest run src/genie/failureOwnership.consumer.test.tsx src/genie/shared/ownedFailure.test.ts src/marketing/entries.test.tsx

node_modules/.bin/vitest run --config /Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/vitest.config.mts -t 'standards final counterpart|standards final verified candidate|standards final unknown counterpart'
```

Logs are respectively `replay-c267ce64.log`, `related-consumers-c267ce64.log` and `counterpart-controls-c267ce64.log`. Added external fixture `counterpart-final.test.ts` SHA-256: `ef86de5d287b2953a162424dda17658940f30bb8505a21cd5f9a3d1d88507068`. Its six cases independently establish: changed durable revision is refused; changed content at the same revision is refused; a fresh candidate read supplies trustworthy evidence before later read failure; known absence permits memory-only consume; unknown present counterpart is retained; unreadable unknown counterpart is retained. Each refusal leaves the exact disk bytes and current memory draft intact.

The producer reports 430/430 related and 553 complete tools tests passing, with one known old generated warning catalog failure, plus TypeScript/ESLint zero. Those are producer-run totals; the independent narrower executions above are this reviewer's evidence. Producer old-version red replay and source snapshots are provenance, not substitutes for these current executions.

## Exact changing-file identities and next gates

- `src/genie/shared/ownedFailure.ts`: `f900a73fd10a0a552cec60dd40098e7598477830b44fabe3ea9c31af75f02446`
- `src/hero/controller.tsx`: `b292667edb0ab609b18a909f9b725530a6950c1d6b7c96100a3c49c7dd1975e4`
- `src/genie/failureOwnership.consumer.test.tsx`: `c911b6e2b36edd2d7e7f4c56e1eae177fae10c10665f6d143841a8f538f80cf3`
- `src/genie/shared/ownedFailure.test.ts`: `70dda43a6484ac6376a60a2179ea3f8eb49e4018b5f31331ff020b90f7122e3e`
- `src/marketing/entries.test.tsx`: `83a1600b8907462b9fa91db9a3847b2af7d9a1dc9ca6c13670cd2791c840a987`

Paths above are relative to `plugins/linker-tools/`; the manifest contains the complete 36-file list and hashes. Source PASS permits the parent to proceed to its generated/i18n, presentation, native browser/CUA, CI and live-readback gates. A later current-main integration or any source hash change requires its own appropriately scoped review. The larger full-site work remains open; this review closes the ordinary failure/editing source blockers, not every visual or buyer-path defect.
