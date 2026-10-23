# Standards review — fixed e1380d49 geographic intake correction

**PASS for the scoped source increment.** No documented-rule breach and no actionable heuristic smell found. This does not approve the missing import UI/map/provider lifecycle, Computer Use acceptance, engineering qualification, site consumers or the full A–D goal.

Fixed source: `e1380d49d267f4ea6ef3083d2c7460432b8e2b22`; base `787728224cd3b20aec63ca7c5a36471a3e9ea22f`; exact diff command `git diff 78772822...e1380d49d267f4ea6ef3083d2c7460432b8e2b22`. Commit set: `a0d12a9f feat(planner): retain geographic originals and prepare owned metric roof imports`; `e1380d49 fix(planner): preserve geodetic roof positions and bound source identity`.

## Authority and boundary

Read the user-supplied replacement AGENTS instructions, worktree AGENTS/CONTEXT, `docs/agents/domain.md`, `docs/agents/issue-tracker.md`, current main-tree `docs/agents/local-storage.md`, `docs/adr/0002-isolated-planner-runtime.md` and `docs/specs/548-geographic-intake.md`. No CONTRIBUTING or CODING_STANDARDS file exists in the checked standards inventory. The user-supplied storage/runtime rules override the older checked-in startup wording. A minimal git-show snapshot pinned all exercised source, contracts, fixtures, tests and emitted modules; existing dependency installations were linked/reused. No site instance, database snapshot, worktree, dependency install, native browser, mail or production access was created.

Only the geographic/import delta was reviewed. The earlier accepted UV/pose arithmetic and editor were not broadly re-audited. The narrow PlaneFrame signature changes preserve their exact expressions. The report examines the fixed source even while the parent edits unrelated WIP.

## Previous finding resolved

The previous Standards P3 polar result skipped computed-output validation. `apps/planner/src/domain/geographic.ts:113–121` now sends the polar result through `geodetic(result)`. Independent browser probes cover north and south poles, origin height0 and MAX_SAFE_INTEGER, supported input Up=MAX_SAFE_INTEGER and valid derived height-100. Unsupported computed heights now throw `geographic_numeric_support`; negative supported heights remain valid. This meets the scoped numerical-refusal contract without inventing a physical roof-height limit.

## Source rules checked

- `geometry_import.py:35–48,84–104`: explicit method is retained in logical options and therefore command/stable-ID identity; missing fields are preserved with exclude_unset. Lookup of the original permanent receipt precedes method refusal and any new conversion. Both missing and null methods fail fresh preparation; missing-field legacy HTTP requests exactly replay an existing asset, while null or explicit new method under its old key conflict. A conversion trap proves replay does not recalculate its geometry.
- `geometry_import_selections.py:26–58`: current source hash equals its owned original, immutable candidate/source/hash association and original-byte existence are checked. Independent real ASGI tests prove a bad current hash returns422 without a new revision, source-note editing still saves, cross-project/source reads fail and missing raw content refuses attachment. SourceForm's readonly field also pins its submitted value; the fixed actual DOM test attempts an altered field submission and retains the original hash.
- Both private import and replay check write ownership before decoding. Decoder traps prove FOREIGN and readonly TEAM get404 for both paths with no blob publication. No browser-selected owner, provider fetch, rights inference or automatic licence upgrade was added.
- Generated options/command/selection schemas match the actual Pydantic models; policy and ellipsoid fixtures match server constants. Ajv does not coerce or insert the optional method default. The client rejects unsupported legacy prepared candidates and applies reference/source/roof/attachment through one guarded domain command/history step.
- Source JSON ambiguity, unsupported positions/CRS, invalid feature IDs, topology and resource policy are validated before publication. Raw byte hash and metadata hash remain separate. Precision stays unknown unless declared; source rights are attestation and engineering status remains not_evaluated.
- The new local/geodetic operations remain distinct. The geodetic operation retains full curvature Up, positive facing and independent branch checks plus explicit arithmetic-granularity support. The installed PROJ operation/runtime and declared plane/source are recorded rather than presented as measurement accuracy. Independent browser large-Up and antipodal/horizon challenges pass; numerical efficacy beyond this scope remains for the separate Spec axis.
- Native change is limited to the existing private RPC allowlist and upload admission lane. No new PHP layout, global React/runtime, CSS compiler, model channel, external data search or customer-facing wording was introduced. Delta-only legacy identifier scan found zero matches in29 changed source/contract/test files. Existing high-risk physics/runtime/model paths are structurally unchanged apart from the narrow plane interface and explicit import integration.

## Independent execution

| Check | Result | Evidence |
| --- | --- | --- |
| Fixed geography/import/private-HTTP suites |115 passed | backend-fixed.log |
| New real ASGI/storage/receipt probes |9 passed | independent-import.log + probe_import_boundary.py |
| Fixed geographic/attachment domain tests |8 passed | frontend-fixed.log |
| New browser polar/local/legacy probes |3 passed | independent-browser.log + probe_browser_boundary.mjs |
| Actual fixed editor DOM tests |6 passed | editor-fixed.log |
| Actual source/build hash and versioned emitted ESM graph |1 passed | build-fixed.log |

The first minimal snapshot omitted the shared planning conftest, producing42 passing checks and73 missing-fixture setup errors. The same-SHA conftest was added and the complete115-check run then passed. This was a review reconstruction error, not a product defect. Logs, exact command arguments, snapshot file hashes and scripts remain in this directory. No native/GPU/touch/EN-DE visual evidence is inferred from DOM or ASGI tests.

## Heuristic smell baseline

No actionable Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man or Refused Bequest found. This is a judgement, not a hard rule or proof of ideal design. The browser's narrow explicit math and server PROJ adapter intentionally cross different runtime boundaries; generated contracts and independently checked parity are the documented architecture, so cross-language representations are not flagged as avoidable duplication. Local E/N and geodetic vertical projection are distinct operations, not redundant switches. The structural read-only PlaneFrame represents an actual not-yet-built import plane. Tooling-enforced formatting/type checks are not restated as review findings.

## Reproduction and retention

`rebuild_snapshot.py` reconstructs only the files listed in snapshot-manifest.json from the fixed Git object, checks their hashes and links the existing node dependency directory. Then execute `run_review_checks.py` in this directory. The runner copies the retained Python/browser probes into that fixed graph, runs all listed checks and removes the temporary browser probe before source-manifest verification. It never invokes native endpoints.

All generated source/cache/runtime files are disposable and reclaimed at review completion after hash verification and preserving these unique probes/logs. `cleanup.json` records exact removal, free-space observation and unchanged files. The parent remains responsible for staging/preserving this proof directory and the complete ongoing goal.
