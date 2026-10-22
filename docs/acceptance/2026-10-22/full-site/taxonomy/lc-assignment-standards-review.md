# Native LC product-taxonomy assignments — Spec and Standards review

**Verdict: final six-file Spec + Standards SOURCE PASS; the reproduced P2 is closed.** The native metadata mechanism, ownership scope and recovery/backup paths match the proposed repair. The original failing source and evidence remain retained below; final-source and permanent-counterexample verification are recorded separately. This is source/isolated-fixture review; the reviewer has not run `present`, rollback, HTTP or a browser against any instance.

## Exact scope

Worktree `/Users/chesterjohn/.codex/worktrees/shared-archive-routes/de-linker`, branch `codex/shared-archive-routes`; actual HEAD at review is `d27f3dc35126cd037db8f98f53da137cacbc52df`. The complete uncommitted diff of the six PHP source/test files below was read, including both untracked `ArchiveAssignments` files. The concurrent empty-state wording/HTML/WindPress/catalog changes and earlier i18n changes are separate scopes.

| File | Reviewed SHA-256 |
| --- | --- |
| `includes/Presentation/ArchiveAssignments.php` | `7c6e982e781efb469bdec33089c846774316e94e4c8019e86928f0dfb7fd6b14` |
| `includes/Presentation/Templates.php` | `e61ef26a53124651e9e6cf48792c27b327572c24843e491ad7b4695e7e7fab56` |
| `includes/Cli/PresentCommand.php` | `68d95821f2b15f34317bdf46b2d65c68bd98ec6813a406cdcc6d83cd6b9b89a7` |
| `tests/php/Unit/Presentation/ArchiveAssignmentsTest.php` | `5e81e7dd67a98410892d8d3ec7dc1550a24ff4be654c610427d4f12d04e763cd` |
| `tests/php/Unit/Presentation/TemplatesTest.php` | `484502cce1ac71cc89948e6fbaf2e483eac6ab747a4bc50ec1fe3c02c4084b78` |
| `tests/php/Unit/Cli/PresentCommandTest.php` | `634c00cce8d73f1a207da87dbde5d5744d8311a44fe90bc7c16edc26021200c2` |

Paths in the table are relative to `plugins/linker-commerce/`. Standards basis is the repository's `AGENTS.md`, the existing `present`/rollback contract, the native LC matcher and the approved empty-archive design. Smell heuristics are judgement tools, not additional hard rules. Only this review document and temporary fixtures outside the repository were written by this reviewer.

## Original blocking finding — CLOSED

The following describes original `ArchiveAssignments.php` SHA-256 `e3e251d060d0e92c78109065eb28efc1a715e0538c47f6fb91884eac483891c7`, not the final source in the table. All six original file bytes are preserved under the temporary `before-tree/` directory alongside `before-six-hashes.json`.

**[P2] Catch all native-write throwables before abandoning a partially changed assignment batch.** `ArchiveAssignments.php:87` catches only `RuntimeException`; the nested recovery handler at line 90 has the same restriction. `update_post_meta()` invokes WordPress metadata hooks, which can throw a plain `Exception` or an `Error` after the write. Those throwables bypass the new batch-local restoration entirely. A previously completed key and the just-written failing key remain changed even though the batch aborts. The outer `present` backup is not consumed, so this is not a claim of lost backup; it is a failure of the new helper's promised local recovery and creates an avoidable partially applied assignment state.

An independent temporary fixture loads the exact actual `ArchiveAssignments` and `Templates` classes with small, explicitly declared native function doubles. Two public product-taxonomy keys target the existing template ID 231. The first has preexisting values `['0', "literal\\n and quote's"]`; the second is absent. The second native update persists its value and then throws a plain `Exception`, modelling an `updated_post_meta` hook failure. Observed result:

- Original error escapes as `Exception`.
- First key remains `['1']` and the originally absent second key remains `['1']`.
- Exact metadata restoration is false.
- The same fixture's control returns a wrong persisted value instead, causing the source's own `RuntimeException`: both original value list and absence are then restored exactly.

Fixture directory: `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/lc-assignment-standards-w_g502ob/`. `exception-probe.php` SHA-256 `552b06a4a7545eba1650b36f4a1faba98456796eeb71f8d19f7180970a9dcd3c`; `exception-probe.json` SHA-256 `116d8d1af957a386d1b897564c64483da21e59c4580ef76d5477c519324c7742`. The JSON binds the actual source SHA and records before/after metadata for both paths. Command: `php <temporary-fixture> <absolute-linker-commerce-directory>`. This runs no WordPress instance and writes no database.

The requested narrow repair was to handle `Throwable` for the write batch and its attempted local restoration, preserve/rethrow the original error after successful restoration, and explicitly report a restoration throwable without claiming success. The requested permanent coverage was write-after-persist `Exception` and `Error` consumers that assert the complete original values, absence, unrelated/per-term keys and retained outer backup as applicable. Do not broaden the repair into a new transaction layer, visual renderer or unrelated `present` cleanup.

## Final closure and independent regression verification

The frozen final source changes both catches in `sync()` to `Throwable`. After successful local restoration it rethrows the **same** original object. A recovery throwable produces an explicit `RuntimeException` containing both failure messages with the original write failure as its previous cause; it does not claim restoration or consume the parent backup. The final WPCS-compatible docblock/prose adjustment changes no behavior. No other production source changed from the originally reviewed three-file hashes except this small `ArchiveAssignments` fix.

The existing independent fixture was extended in a separately retained `throwable-probe.php` to include `Error`, without modifying the original red fixture/output. Fixture SHA-256 `3f3e1abc747e31316b0190f78af4d2ca5cc41a7ff0e749d1e7c9241cb8627116`. Against copied original source, readback failure restores, while ordinary `Exception` and `Error` do not (`throwable-before.json`, SHA-256 `549988ef7348e5c2a819bb1ad6abaff8043e196e1f00ad22b82b8927221f5fd2`). Against the exact final source `7c6e982e…`, **all three modes restore the original value list, literal backslashes/quote and original absence** (`throwable-final.json`, SHA-256 `42354d9d7202de550ed858fe95ebc2820346710ff3b9434557e0b3ffd3603a04`). The output records the source hash for each observation. An intermediate green result is retained separately and is not relabelled as the final-source run.

Four new helper cases (two methods × `Exception`/`Error`) actually persist the second key before throwing, require exact original values and absence/per-term/unrelated scope, and check identical original-object rethrow or explicit recovery-failure cause. Two new actual `PresentCommand::present()` cases traverse the real dispatcher, observe the same hook failures, require the original assignment snapshot to remain in the existing backup, require exact restored metadata and no success announcement. They do not substitute a fake `present` or parallel recovery algorithm.

To prove these permanent tests discriminate the original defect, the reviewer preloaded only the copied original `ArchiveAssignments` class through an external PHPUnit bootstrap, then ran the **unchanged current six tests**. Result: **6 failures / 14 assertions, exit 1**, each an expected failed restoration/cause assertion rather than a bootstrap failure. `permanent-before-red.log` SHA-256 `3f9d3c09d45c7a92b85dc623615c673e57bcd711cfa80e30b8a133c284a046af`. With the exact final class and normal bootstrap: **6 tests / 28 assertions PASS**, exit 0; `permanent-final-green.log` SHA-256 `92fa5ba74ef809f1e81b04ebce2b740d3af1de94234a04f32428f8d3807ed802`. All these files are in the same temporary evidence directory named above; no repository/instance class was replaced.

The reviewer also independently ran the complete three relevant suites after the behavioral fix: **102 tests / 632 assertions PASS**. The only subsequent product change was the re-read throws/prose comment adjustment; the final six dedicated tests and three-mode actual-class probe bind to the exact frozen hash. The implementer reports final six-file WPCS, complete commerce PHPStan with 1G memory and the same relevant suite green. Final six hashes match the table, and `git diff --check` passes. No actionable source/spec/Standards issue remains in this six-file scope.

## Checks that passed

- The new module installs generic **native LC metadata** rather than taking over rendering or building PHP layout. Its keys come from registered public/publicly-queryable taxonomies attached to products, covering valid filter-empty category/attribute archives as well as raw zero-count shared brands. The current registry fixture includes all eleven public product taxonomies and excludes private/nonqueryable/unrelated taxonomies.
- The actual LC matcher selects a published template by **meta existence**. The competitor scan respects that: value lists containing `''` or `'0'` still establish ownership. It checks one primed published-template query across languages instead of constructing a large taxonomy meta-query join graph. Same-language and unclassified owners refuse the batch. Other-language owners and per-term keys remain intact; no other template's metadata is deleted or reassigned.
- `Templates` resolves the existing product-archive anchor and its native Polylang German twin; the producer test proves unchanged HTML still installs 22 assignments on that pair without inserting new templates. Initial preflight precedes its template writes, and `sync()` checks the whole assignment set again before its own writes. Missing/conflicting assignment state joins the existing drift report rather than being reported as clean.
- Snapshot scope is the intended template IDs and discovered generic keys only, with absent keys represented as `[]` and existing keys retaining their complete native value lists. Rollback uses the **saved keys**, not a later taxonomy registry. It rejects per-term/non-generic scope, restores absence versus empty/multiple values and uses `wp_slash()` on metadata re-adds. Exact readback, rather than the API's boolean response, determines success.
- `PresentCommand` includes this snapshot in the existing backup before template/assignment changes and verifies the backup option reads back exactly. The new rollback step occurs before the backup is deleted. A declared readback failure stops rollback and retains the backup for retry. Ordinary later-write failure and local-recovery failure have permanent tests; literal backslash/quote preservation is exercised in the new module's native-escaping simulation.
- Existing test defaults explicitly opt out of taxonomy discovery; the new actual `Templates` producer and actual `present` consumers opt into it. The added tests do not replace the implementation with a parallel assignment algorithm or imply a browser result.

Independent `vendor/bin/phpunit --filter 'ArchiveAssignmentsTest|TemplatesTest|PresentCommandTest'` passed **96 tests / 604 assertions** against the original candidate before the P2 fix. The final verification is separately recorded above. `git diff --check` passed. The parent/implementer separately reports the full PHP suite, six-file WPCS and PHPStan with the repository's 1G memory setting green; those full checks are not this reviewer's execution. The original exception probe explains why that earlier passing targeted suite alone did not warrant PASS; the final dedicated tests and independent rerun now close that gap.

## Acceptance boundary

The parent's reported native before matrix has eight empty requests with no LC template among ten probes. That is discovery evidence, not a post-repair PASS. With the source P2 closed, the parent still needs to execute official `present`, inspect exact metadata/owner/readback and chosen native LC template, exercise empty root/filter/search and nonempty controls in EN/DE, perform rollback with before/after scope equality, and repeat the requested visual and onward-navigation states. The separate code, Woo brand-base option, metadata and translation/CSS changes retain their own backup/version boundaries. Source review must not relabel the earlier route/cache matrix or a normal nonempty archive as proof of the new empty-loop consumer.
