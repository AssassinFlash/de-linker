# Standards recheck: 6c6680ad

Fixed `6c6680ad4e2eb890b08c58b5a9bffd95ecb48957`; complete base `8a4a80b1`, targeted fix after `37f2acd3`. **FAIL: one remaining P2 cancellation-lifecycle defect.** Original two findings are closed; no heuristic smell finding worth raising.

## Closed original findings

The original unmodified lazy/staged probe now observes retained raw rows=2.5, 18 input/button nodes and an outer ChunkBoundary fallback. Its old assertion expecting editor removal is obsolete. A separate corrected-behaviour adapter preserves the original module failure, verifies raw input after retry, and returns to a working plan view without losing it.

The original AST factory fixture needs only a fixture adaptation for new imported release helpers. Keeping it unchanged demonstrates the missing binding, not a product failure. An adapted AST extraction executes the original callback with the actual release helpers across initial failure, fallback failure, successful fallback, late generation and throwing cleanup. Each path releases the appropriate unowned resources, successful fallback releases the replaced backend, and original init errors survive cleanup errors. This remains a lifecycle-boundary test, not actual GPU proof.

## Remaining P2

`SceneControls.tsx` ArrayTransform effect cleanup removes listeners, detaches/disposes controls and dispatches the orbit-end signal, but does not cancel/reset an active gesture or invoke its cancel callback. The product mounts this adapter only while selected and not disabled. A keyboard/second-pointer property action or selection change can therefore remove the handles while the containing Panels group remains mounted.

Independent actual Three TransformControls + React 19/StrictMode probe, with only useThree replaced by a no-GPU host: a group whose project position is [1,2,3] is dragged in preview to [7,2,3]; unmounting only ArrayTransform leaves its position [7,2,3], cancelled=0, finished=0. The visible preview is neither committed nor restored. This breaches the interactive-design single-document/preview-cancellation contract and resource-lifetime cleanup semantics. Cleanup must cancel active manipulation before detaching so the caller restores the current authoritative origin. Retained probe: apps/planner/tests/standards-unmount-transform-probe.mjs.

## Independent evidence and boundaries

45 official domain/data tests and 51 official React/DOM tests passed. Signed-zero JSON equality follows the wire while retaining local source values. New source legacy identifier hits: 0. Existing scoped WindPress and isolated React boundaries remain intact. The first editor increment is still incomplete; actual GPU, pointer/native, restored pending save and EN/DE visual acceptance belong to the parent line. No p548, production or WIP access occurred.

## Final copy

259 final messages match both the checked-in PO and the actual app-script JSON: 35 previous PO values unchanged, 224 new translations, every printf placeholder intact. All original substantive copy concerns were applied: open draft vs saved, source attestation vs north verification, footprint diagnostic scope, diagnostic counts, pitch<90 and non-engineering projection limits. No new wording blocker found. This is source/catalogue approval only, not proof of native rendering. See copy-recheck-results.json.

Reproduction: restore fixed paths listed in archive-manifest.json and symlink the installed app dependencies. results.json contains exact probe commands. After review, source was SHA-verified and reclaimed; only unique probes/results/manifests/review remain.
