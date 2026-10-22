# Ordinary Genie b472f325 — independent Standards review

2026-10-22. **Bounded SOURCE PASS: the three reproduced fd04 preservation defects are closed; no new actionable Standards blocker found.** This is not a generated-bundle, browser, physical-voice, CI, production or whole-site acceptance claim. Historical BLOCKED reports and red logs remain unchanged.

The frozen producer tree was copied to an isolated directory with the existing dependencies linked, without installation or generation. All 19 source and 22 test/helper SHA-256 values were independently checked before and after execution. Three auxiliary files (PO/spec/e2e) were checked against the manifest in the current worktree, not claimed as part of the isolated test execution. Aggregate 19: `b472f3259aeb32e17419745942c5653ffbbe82e1332914e385929300290dfb1a`. The independent original-17 aggregate is `4116014e7585474d39e96a4fe0f861d5af2e18ce77689fd1203bf816b70515b9`. My earlier two handoff source files and two tests are excluded from self-approval; their separate independent review remains the authority.

Exactly three sources differ from fd04; `editingDraft.ts` changes only its cursor comment. App remains `e287fdd29f30ea2f97599cc3a477c0c197454c2d18eb7b547a3cd42e1ef5cbf8`; the other 15 product sources are also identical.

| Changed source | SHA-256 |
| --- | --- |
| `src/genie/shared/editingDraft.ts` | `cd51e791ee2177ee795f50d3646d5fa8e2c29af4fdbb97298c9d938962b49dc3` |
| `src/genie/shared/ownedFailure.ts` | `b77fa2274da4735490fd940b4c790cdbe33b13f6f70e284dc9b94e424aeebb17` |
| `src/genie/shared/useFailure.ts` | `50d3d6e25862be5ff61e706b267cee3c21546663bf4f1ab3a9e0548951c87bb3` |

## Source conclusions

Mounted preservation now uses its acknowledged editing cursor for beforeLeave/pagehide, empty clear, exchange and promotion. An unchanged target may advance over unrelated bucket changes; a changed same-copy entry/revision cannot become write/delete authority merely by being reread. Unchanged stale UI yields to recoverable data, while distinct accepted UI bytes are retained at a demonstrated conflict. No observed path uses that recovery read to overwrite or consume the newer entry. First writes for genuinely new owners retain the existing allocation path.

The retained store holds actual displaced window-only entries, scoped by original scope/attempt and exact entry/revision. It neither invents an identity/storage key nor assigns old bytes to a new principal. Retained writes and async rebase require the selected exact copy; explicit verified Restore can inspect/select inactive copies. Successful consume checks that exact retained entry, removes a durable counterpart only when its complete original entry/revision still match, and repairs selection so remaining actual copies are not hidden by an attempt-wide consumed marker. Existing default consume remains conservative. Storage failure remains unsaved and does not manufacture a durable acknowledgement.

The extra retained-copy mechanism adds complexity, but the actual three-copy quota/conflict consumer supplies a concrete need. It is confined to the existing journal/hook boundary and does not become per-keystroke history or impose a speculative eviction cap. No Fowler heuristic warrants a separate blocker here. There is no new copy, PHP design, model route, native authority or presentation pipeline; selected-source old-marker search (`tv_b2b_`, `Linker_AI_`, `dlk-`) found no matches. The original voice test file is a byte-identical prefix of the new file; seven permanent cases were appended without weakening earlier controls.

## Independently executed evidence

| Run | Actual result | Log SHA-256 |
| --- | --- | --- |
| Original fd04 three red fixtures, unchanged, plus original different-attempt control | 4 PASS | `5f1e6722f3349c061f556390111e9bd8e30ce0eb8cc03a9b972f75e9a55ae83f` |
| Seven related files: voice, authority, default journal, ordinary App/Hero, resource, caller and hook | 150 PASS | `c3bc95eb02e6b55de322050c358644fada61d42298eaf6412cd5a5e24c4c2325` |
| Additional independent actual App controls: exact retained clear with fresh A/B recovery, and unavailable storage consume | 2 PASS | `5c627fa9d420e466df6c98748791e114b5a83e69f18c545c165bbfa87f326e03` |

The runs cover original stale Restore/clear and quota overwrite, three-copy traversal with PDF/reselection data, retained success and newer retained revision, unrelated-attempt progress, same-copy conflict, missing-only upstream/no empty Send, A1/A2, B blank/no transport, original authority and read-failure guards. The extra clear control explicitly removes selected retained text/file, confirms B sees neither data nor a transport, then fresh A reaches both surviving versions without restoring the consumed one. The extra storage control proves failed reads refuse consume, retain selected bytes, expose the existing unsaved warning and send nothing.

Isolated root: `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/ordinary-standards-b472-0k77ow11`. Stable provenance, full post-run source/test maps, three logs and external fixtures: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/ordinary-standards-klyk754x/b472-fixed-review-20261022T064539971688Z/`. Added temporary consumer SHA: `01ca7b070ab059dfe3d2d23caa42926153c046e830252b3665bd726d21c1f4f9`.

No product/test source, dependencies, build, browser, local instance or production state was changed. This new report is the sole repository edit. The producer's full-JS/catalog status remains producer evidence; this report claims only the independently listed executions.
