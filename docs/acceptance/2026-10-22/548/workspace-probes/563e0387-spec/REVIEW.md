# Spec review — 563e0387 FAIL

Target `563e038786330ba17aea339e96e9f54e961e4195`; base `7e96b88dd902ea64fd27250494d3129783d7f307`. One P2 implemented-wrong finding in this Journal workspace presentation increment; no separate scope-creep or missing-capability finding is counted against the explicitly incomplete full A–D goal.

**P2: Site workspace navigation starts after its first project inputs.**

`WORKSPACE-VISUAL-CORRECTION.md:27–31,37–39` requires separate active workspaces and says “explicit switches reveal/focus its content beneath the measured site and project bars.” Fixed `ProjectEditor.tsx:41–45,97–119` uses `workspaceHash.site="lp-site"` for the reveal target. However, `BriefForm.tsx:61–137` renders the preceding `#lp-brief-use` section with Site use and Planned system, before `#lp-site` at lines138–147. Clicking Site and project therefore focuses/scrolls to the second section, past the first inputs belonging to that workspace. The parent's separate native 390 observation confirms those inputs land above the viewport. The independent DOM counterexample asserts visible section order and fails with actual focus `lp-site`, expected `lp-brief-use`. Preserve legacy initial `#lp-site` mapping while making an explicit workspace switch reveal the workspace's beginning.

Other challenged requirements pass: all seven legacy initial fragments choose the intended workspace; absent layout remains unknown while an explicitly excluded layout can show zero; multi-roof quantities count included objects and declared watts across the real document; the preview names and draws its actual first roof, exposes no editor controls and creates no edits. Raw decimal input, CSV file/delimiter, DOM node identity, source metadata, unrelated inputs and shared undo/redo survive switching. Unapplied geometry and invalid brief inputs block navigation. Geometry application adds one history step, and scope withdrawal prevents navigation.

Execution: the complete fixed client suite passes 54 domain/data and54 DOM tests. Independent tests pass 18 cases with one intentionally red product counterexample. The initial German test wrongly treated valid `1,` as invalid; its retained harness log and correction explain the change to genuinely invalid `1,,` without product changes.

This is source/React DOM evidence. Native EN/DE×1440/390, physical layout, sticky navigation, provider/map, engineering and full site acceptance remain separate. The parent's subsequent destination/selector implementation is outside this fixed review.
