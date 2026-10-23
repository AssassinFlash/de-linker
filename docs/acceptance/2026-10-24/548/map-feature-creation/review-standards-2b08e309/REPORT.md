# Standards review at 2b08e309

Reviewed the full 31-file diff `81524ca90795f4f26e80c59e5a63c63e23bd80c9...2b08e309282034e6c2ab77a6f580706d2c713d8d`, including generated modules, manifests, catalogues and evidence. Sources: current main and owned `AGENTS.md`, `CONTEXT.md`, `README.md`, `.editorconfig`, runtime ADR, feature/drawing/recovery specifications, and the supplied Fowler baseline. The planner runtime exception governs this isolated app; newer main storage rules govern resource handling. Tooling-enforced formatting matters are excluded.

## Findings

1. **[P3, documented standard] Trace the new text bound.** `apps/planner/src/domain/mapFeatureDraft.ts:113` introduces `length > 4096`; `MapFeatureProperties.tsx:70`, `:104` and `:155` repeat `maxLength={4096}` without source comments. `AGENTS.md` §4 explicitly requires “每个数字与阈值必须有来源注释.” The engine's `planning/geometry_documents.py:15` already defines a 4096-character `Text` contract, and the existing raw roof reader uses the same bound, so the value itself is not shown wrong. Record the shared raw-input policy and distinguish it from physical limits, preferably through one named, sourced constant consumed by validation and controls.

2. **[P3, heuristic: possible Duplicated Code] Share selector admission.** `MapDrawingWorkspace.tsx:455–470` copies `mapProps.disabled || journal.checking || journal.storageFailed || !geographicReady` for both entry selectors. A later admission change could enable one entry while blocking the other. Compute one named eligibility value and pass it to both. This is a maintainability judgement, not a demonstrated behavioural defect or documented-rule breach.

No other supported documented violations or baseline smells were found in the reviewed diff.

## Verification and limits

Focused checks passed: 15 domain, 46 React/journal/workspace and one built-module identity test. All 125 source and seven build hashes matched. All 27 reviewed EN/DE pairs matched compiled MO, JSON and built JS; 14 pairs are new, with no existing MO translation changed. Planner source grep found no prohibited old identifiers. Identity and command evidence are in `identity.json` and the two logs.

Map projection/report fixtures do not establish native/browser, HTTP/server, provider, engineering or full-goal acceptance. No browser, external request, source/build edit, instance, dependency, worktree or backup was used or created. Review ownership is released for the root's corrections.
