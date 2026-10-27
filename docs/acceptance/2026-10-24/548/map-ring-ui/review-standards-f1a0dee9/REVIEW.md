# Independent Standards review

**Result: PASS for the reviewed increment; 0 documented-standard breaches and 0 actionable baseline heuristic concerns.** This is not whole-goal acceptance.

Compared the complete three-dot diff `252a022e41f8ca5426d6463206c8346eb89da5f1...f1a0dee90dd719ce5532724a9f6e9021f1555705`, including both implementation commits, tests, reviewed copy, WindPress changes and generated assets. Actual HEAD matched the final pin; all 15 changed non-test source files matched its Git blobs. Concurrent untracked acceptance evidence was left untouched.

Standards read: active user instructions and `/Users/chesterjohn/Documents/de-linker/AGENTS.md` (including storage amendment), owned `AGENTS.md`, `CONTEXT.md`, `README.md`, `.editorconfig`, and `docs/adr/0002-isolated-planner-runtime.md`. The explicit isolated-runtime ruling governs the older global-React wording.

The diff conforms to the relevant rules:

- AGENTS §4 / runtime decision: React remains isolated; no dependency manifest changes. Map, plan and 3D receive one domain document and grouped `GeometryCommand`, rather than separately persisted scenes.
- AGENTS §§4–5: existing IndexedDB/version, native scope admission, exact CAS/uncertain-write handling and server-confirmed retirement are shared. The v1 reader retains its contract; v2 separately validates target and metric/geographic pairs. Original plane, Source precision/permissions, other objects and edited-object identity survive.
- AGENTS §§2–5 / README build contract: customer strings use the existing i18n channel. All 29 reviewed final EN/DE pairs independently match the MO and runtime JSON. Scoped classes stay in the existing WindPress/token volume; no new CSS compiler, inline styling or PHP design channel appears. Build-source verification passes, including lazy chunks.
- AGENTS §5 legacy check: no `tv_b2b_`, `Linker_AI_` or `dlk-` matches in changed source. No server physical chain, identity implementation, translator or model route changes.

Fowler baseline: no actionable smell found. Shared parsing/journaling and feedback replace duplicated behavior; the operation union and target discriminator express current requirements. File length alone is not a violation.

Independent commands in `apps/planner`: `npm run build:check`; `node --test src/domain/mapRingDraft.test.ts`; `node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/map-roof-recovery.test.mjs tests/map-roof-workspace.test.mjs`. All exited 0: 1 build, 4 domain and 23 journal/workspace tests. Hashes/probe details are in `CHECKS.json`.

Limits: fixture projection and mocked review responses are not native GPU/touch, engineering or production evidence. The existing Node module-type warning did not fail the build test. No browser, instance, global setting, mail, dependency or runtime copy was modified or created.
