# CI fast feedback, fail-closed

2026-10-29. Inspected `origin/main` at `ee81930a3657699a5f2a67af55b08173b33fe33c`, the tree that ran the workflow that day. The local `main` checkout was behind that commit; the shorter workflow on the stale checkout is not what CI executed.

This note separates measured repository behavior and quoted primary sources from the design recommendation. It does not change the workflow.

## How the sources were read

External discovery used the Apify actor `apify/google-search-scraper` through the configured CLI. Three calls exited 0 on 2026-10-29. No other search tool was used.

The third call found [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks). `site:bazel.build hermeticity` returned no organic results, and `site:bazel.build/basics hermeticity` returned the basics index rather than the hermeticity page. That page was then read at its canonical URL, [Hermeticity](https://bazel.build/basics/hermeticity). Claims below come from the cited pages, from `git show` of the inspected tree, or from the GitHub Actions run metadata named in the cost section.

## 1. Practices that apply

### One workflow must always report a check

[Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) lets `push` and `pull_request` use `paths` or `paths-ignore`. If every changed path matches `paths-ignore`, the workflow does not run. The same page states the failure mode that matters here: a workflow skipped by path filtering, branch filtering, or a commit message leaves its checks Pending, and a pull request that requires those checks is blocked from merging. [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks) repeats that, and adds the opposite trap: a job skipped by a conditional reports Success and does not prevent merging, even if that job is a required check.

Those filters are also not a reliable file ledger. The syntax page says GitHub uses a three-dot diff for pull requests and a two-dot diff for pushes. It then limits that diff:

- a push of more than 1,000 commits always runs the workflow
- a diff that times out always runs the workflow
- a diff of more than 3,000 files does not run the workflow when the files the filter would match are not in the first 3,000 returned

The first two are fail-open toward running. The third is a silent skip. Neither is a proof that every unknown path was tested.

[Using conditions to control job execution](https://docs.github.com/en/actions/using-jobs/using-conditions-to-control-job-execution) is the mechanism that still reports a check: `jobs.<job_id>.if` skips a job without skipping the workflow. The required name has to be a job that fails when the selection is unrecognized. A skipped lane job cannot be that name.

### Cancellation must not use `always()`

[Concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency) says the default is concurrent runs of the same workflow. [Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) says `cancel-in-progress: true` cancels the running job or workflow in that group, and that the group and the flag may be expressions. `github.head_ref` exists only for `pull_request`; the documented fallback is `github.head_ref || github.run_id`, which cancels superseded PR runs and does not cancel an unrelated `main` push.

[Evaluate expressions in workflows and actions](https://docs.github.com/en/actions/reference/evaluate-expressions-in-workflows-and-actions) says `always()` returns true even when the run was canceled, and tells authors to use `!cancelled()` when a dependent job should not start after cancellation. A workflow that adopts `cancel-in-progress` and leaves `if: always()` on the heavy jobs fights the cancellation.

### Cache is a speed input, not a gate

[Dependency caching](https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching) says a job on a GitHub-hosted runner starts clean and must be able to re-download or regenerate cached files. [Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching) names `actions/setup-node` as the npm cache action, keys caches with `hashFiles` of the lockfile, and warns that cache contents are unsigned. A `pull_request` cache is stored on the merge ref and cannot be restored by the base branch. Low-trust triggers, including `pull_request_target`, are read-only on the default branch's cache unless a workflow opts into write and reintroduces cache poisoning.

The pinned `astral-sh/setup-uv` at `c18668ad3cf93ea998bef934396af7bb5c839dc7` (v10.2.0) already exposes `enable-cache` and `cache-dependency-glob` in its `action.yml`. [setup-uv caching](https://github.com/astral-sh/setup-uv/blob/main/docs/caching.md) says the cache key includes the hash of files matching that glob, plus OS and Python version. That page's examples are newer than the pin. The inputs exist on the pin; the key formula should be re-read at the pin before anyone treats a narrower glob as part of correctness. It is not a correctness mechanism either way: a miss must still install and test.

### The pull request under test is the merge commit

[Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) says `GITHUB_SHA` for `pull_request` is the last merge commit on `refs/pull/N/merge`, and that `actions/checkout` therefore tests the merged result, not the head branch alone. The same page says a `pull_request` workflow does not run while the pull request has a merge conflict. It also warns that `pull_request_target` runs even then, and that the trigger has security risks.

[Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) says to avoid `pull_request_target` unless the workflow needs the privileged context, and not to check out untrusted pull request code under that trigger. It also says the default `GITHUB_TOKEN` permission should be read access to contents, with increases made per job, and that third-party actions should be pinned to a full commit SHA. This workflow already does the token and the pin. A third-party path-filter action is an extra supply-chain dependency with no capability `git diff` lacks.

### Affected means a declared graph, which this repo does not have

[The Bazel Query Reference](https://bazel.build/query/language) defines `rdeps(u, x)` as the reverse dependencies of `x` inside the transitive closure of a universe `u`. The universe is an argument. There is no affected set without a declared graph. [Hermeticity](https://bazel.build/basics/hermeticity) says the same inputs must produce the same output, and that undeclared host tools and writes back into the source tree are non-hermetic. A cache hit is only meaningful for actions whose inputs were declared.

[Run Only Tasks Affected by a PR](https://nx.dev/docs/features/ci-features/affected) is the same rule at task granularity. Nx selects a task when a changed file is one of its declared inputs, then selects tasks that read that task's outputs. CI must pass an explicit base and head; without full git history there is no base to compare. A lockfile change affects every task unless a separate dependency-update setting narrows it. A change to an input shared by every task selects most of the workspace. Nx also says each later push is compared with the same base, so remote caching, not a second selector, is what avoids repeating unchanged tasks.

Importing Bazel or Nx would be a new build system. The rule that transfers is smaller: without a declared input graph, the safe unit is the package, and an unmatched path is not unaffected.

### Fast feedback is a small test, not a promise of a green run

[Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html) (Simon Stewart, Google Testing Blog, December 2010) defines Small, Medium, and Large by resources, not by a team's private meaning of "unit". A Small test has no network, no database, no filesystem, and a 60-second limit. A Large test may use external systems and is the end-to-end class. Tests must be isolated enough to run in any order, which is what makes parallel execution possible.

That source does not say a scoped suite never fails. It says the large suite is the wrong instrument for a failure that a small isolated test can already report.

### What a public standard runner costs

[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) says standard GitHub-hosted runners are free in public repositories. Larger runners are billed for public repositories. The Linux 2-core rate used in private billing examples is $0.006 per minute. Cache storage includes 10 GB per repository; usage above that is billed. A failed run is billed for the minutes it used, and a rerun is billed again.

`AssassinFlash/de-linker` is public. Dollar cost of the current `ubuntu-24.04` jobs is zero. The cost that matters is wall-clock time and runner occupancy. Adding a larger runner would create a bill and is not recommended.

## 2. What this repository already does

`.github/workflows/check.yml` on the inspected tree is one workflow with three jobs: `plan`, `check`, and `mu-smoke`. There is no `concurrency` key. `permissions` is `contents: read`, plus `actions: read` on `plan`. Actions are pinned to commit SHAs. `actions/setup-node` caches npm from the lockfiles of `linker-tools`, `linker-commerce`, and `apps/planner`. `astral-sh/setup-uv` has `enable-cache: true` and a glob over `services/*/uv.lock` and `tools/*/uv.lock`. Both caches are attached only to the jobs that reach those steps.

`plan` checks out `github.sha` and runs `git diff --name-status -z --no-renames` from `pull_request.base.sha` or `push`'s `before` to that SHA. [git-diff](https://git-scm.com/docs/git-diff) says `-z` keeps unusual pathnames from being quoted and terminates fields with NUL, `--name-status` prints status and path, and `--no-renames` turns rename detection off even when the local config would enable it. The classifier then allows only four narrow outcomes, and only when every path fits:

| Mode | When | What still runs |
| --- | --- | --- |
| `docs` | every path is a document or an acceptance record, and each blob passes the non-runtime check | plan only |
| `presentation` | pull request, proven base, only existing LiveCanvas or WindPress surfaces, status `M` | commerce presentation PHPUnit, plus catalog gates if a catalog changed |
| `commerce` | pull request, proven base, only the explicit commerce allowlist, regular files | `just commerce-check` and almost the whole `mu-smoke` job |
| `reuse` | push of a tree already proven by a successful pull-request run of this same workflow file | plan only |
| `full` | everything else, including an empty diff, a missing base, a rename, a symlink, or an exception | `just check`, `just test`, committed `build/` reproduction, and `mu-smoke` |

`tools/checks/test_ci_scope.py` executes that classifier and requires an unknown path, a rename, a missing base, and a workflow or lockfile change to stay `full`. It also requires the recovery-named `mu-smoke` steps to stay enabled for `commerce`. That last assertion is why a commerce allowlist hit is not a fast path: the measured instance job still runs.

`apps/planner`, `services/engine`, and `services/genie` are not in any allowlist. A planner-only change is `full`. `just check` and `just test` then walk every PHP, Node, and Python project in one job. `js_projects` includes the planner. `just test` runs PHPUnit, then all Node tests, then every uv project, including `tools/local` pytest, which builds real instances. `just build` rebuilds linker-tools, then the planner, then commerce, because wp-scripts cleans `build/` before the planner build. `plugins/linker-tools/bin/build-manifest.mjs` hashes every file under `build/` except `build/manifest.json` itself, and it reads `build/planner/source-manifest.json`. A real planner change that updates the committed bundle therefore also changes `build/manifest.json`. Pull request #778 did exactly that.

`check` and `mu-smoke` use `if: always()` and then fail if `plan` did not succeed or the mode is unrecognized. That is fail-closed for a crashed plan. It is also the pattern that will not observe cancellation.

`main` is not branch-protected. `GET /repos/AssassinFlash/de-linker/branches/main/protection` returned 404, and the rulesets list was empty. The Pending-check problem is not blocking merges today. It becomes a blocker the moment any of these job names is required. The design below assumes that will happen, because a gate that can be satisfied by absence is not a gate.

### Measured cost

Times are from the Actions API, not estimates.

Successful full pull request, run [40879009655](https://github.com/AssassinFlash/de-linker/actions/runs/40879009655) (#777, 2026-10-29):

| Job or step | Duration |
| --- | --- |
| `plan` | 9s |
| `check` | 21m 21s |
| of which `just check` | 7m 32s |
| of which `just test` | 12m 12s |
| of which committed build reproduction | 45s |
| `mu-smoke` | 9m 44s |
| wall clock | 21m 36s |
| billed runner time | 31.2 min |

`mu-smoke` on that run spent 241s on the business and notification capacity suite, 69s on inquiry assessment, 60s on administrator MFA, and 57s on inventory access. Those are the recovery and product gates. They ran in parallel with `check`, so they did not add wall-clock time. They did add the 9.7 minutes of occupancy.

Failed pull request, run [40893068663](https://github.com/AssassinFlash/de-linker/actions/runs/40893068663) (#778):

| Job | Duration | Result |
| --- | --- | --- |
| `plan` | 60s | success, mode `full` |
| `check` | 8m 54s | failure in `just test` |
| `mu-smoke` | 9m 19s | success |
| billed | 19.2 min | Genie unit assertions |

Inside that `just test`, PHPUnit started at 14:42:20Z and Genie pytest started at 14:44:03Z. Genie pytest then ran 112s and failed 12 tests in `services/genie/tests/test_prefill.py` and `test_campaign_339.py`. The assertion was a Small test. The developer heard it only after the preceding PHP and Node suites, while the instance job ran to completion beside it.

#778's diff is not a planner-only diff. It changes planner sources, the committed planner bundle, `build/manifest.json`, commerce PHP and LiveCanvas, engine planning modules, and Genie tests. `full` was the correct current classification. The waste is the serial package walk plus an instance job that cannot report a Genie assertion, repeated on each push.

Six completed red runs of #778 landed between 13:26Z and 14:46Z. Their wall times were about 10 to 12 minutes each, and they did not overlap. `cancel-in-progress` would not have saved those six, because each had finished before the next push. The runs that were cancelled that day, such as [40870209512](https://github.com/AssassinFlash/de-linker/actions/runs/40870209512), are not evidence of an automatic concurrency group: the workflow has none.

A docs or identical-tree push is already cheap. Run [40882384278](https://github.com/AssassinFlash/de-linker/actions/runs/40882384278) on `main` finished in 24s, with the heavy steps skipped after `reuse`. That path should stay.

## 3. Recommended job architecture

Recommendation, not a claim that GitHub or Nx requires these job names.

Keep one workflow. Do not add `on.pull_request.paths`. Do not add a path-filter action. Keep the native `git diff` against the merge commit.

Replace the single exclusive mode with a path ledger. Each changed path is either assigned to one or more package lanes or marks the run `full`. Lanes compose. `full` does not compose with them: if any path is unknown, shared, or unproven, every narrow job is skipped and the full set runs. That is what removes duplicate runs without leaving a gap.

### Lanes

A path enters a lane only when its git status is `A`, `M`, or `D`, the blob is a regular file on every revision that exists, and the path matches that lane's allowlist. Any other status, a submodule, a symlink, an odd `-z` record, a failed diff, or a missing base after one fetch sets `full`.

| Lane | Allowlist | Job, once | Instance |
| --- | --- | --- | --- |
| `docs` | current document and acceptance-record rule | none beyond `plan` | no |
| `presentation` | current LiveCanvas and WindPress rule | current presentation contract | no |
| `commerce` | current commerce allowlist, unchanged | current `just commerce-check` and the current `mu-smoke` steps | yes |
| `planner` | `apps/planner/**` | Node 22, `setup-node` cache on `apps/planner/package-lock.json`, `npm ci`, the planner lint and `npm test`, then `npm run build:check` in `apps/planner` only | no |
| `engine` | `services/engine/**` | pinned uv, `enable-cache`, glob `services/engine/uv.lock` and that project's `pyproject.toml`, then ruff, mypy, and pytest in that directory only | no |
| `genie` | `services/genie/**` | same shape, glob limited to `services/genie/**` | no |
| `full` | the default | the package jobs below, in parallel, plus `mu-smoke` | yes |

`commerce` stays on the instance job in this change. `test_ci_scope.py` currently requires that, and several allowlisted commerce files sit next to price, mail, and account behavior. Narrowing that link would be a second, separately tested map. Doing it now would weaken a gate to buy a speed claim this evidence does not support.

The planner lane has one content-aware exception, because the tools manifest is shared. `plugins/linker-tools/bin/build-manifest.mjs` hashes every file under `build/` except `build/manifest.json`. A planner commit that updates `plugins/linker-tools/build/planner/**` will also change `plugins/linker-tools/build/manifest.json`. Those two paths may stay in the planner lane only if the planner job proves every non-planner hash in that manifest is unchanged and the planner entries match a fresh planner build. If the manifest cannot be parsed, or any non-planner hash moved, the run is `full`. The planner job must not call `just build`: that recipe cleans `build/` and rebuilds the tools bundle.

`plugins/linker-tools/includes/Planner/**` is not the React app. Gateway, admission, and the claim outbox are PHP recovery surfaces. A change there stays `full` until a file-level map exists and an unknown file under that directory is tested to remain on the instance job. `PlannerApplicationTest` is different: it is a `WP_Mock` test of the committed vite manifest, not an instance test. The planner job runs that one PHPUnit file when `build/planner/**` changes. That preserves the source gate without starting MySQL.

Language catalogs are a source gate. If a planner diff also changes `plugins/linker-tools/languages/**`, the planner job runs the existing i18n coverage and validity commands. It does not skip them because the rest of the diff is TypeScript.

Shared denylist, even when every other path is allowlisted: `.github/**`, `justfile`, `tools/build.just`, `tools/checks/test_ci_scope.py`, the classifier module if it is extracted, any lockfile installed by more than one lane, and any new path that matches no allowlist. A lockfile owned by one package is that package's lane, because that lane's job installs from it and runs that package's tests. Nx's lockfile rule is the reason a shared lockfile is not given the same treatment.

Do not select individual tests by filename. This repo has no input graph. A test whose name did not change can import a module that did. The package is the smallest unit these sources support.

### Full lane, still parallel

`full` remains the safe result. It should stop being one serial `just check && just test`. Split it into the same package jobs, all selected, plus the Python projects that are not engine or Genie (`tools/local`, `tools/migrate`, `tools/faq`, campaign harnesses, pull, cutover), the content gates, the committed build reproduction, and `mu-smoke`.

That split is what shortens a mixed pull request such as #778. The Genie assertion would start with the other package jobs instead of after PHPUnit and the Node suites. `mu-smoke` would still run, because that diff contained commerce PHP and a shared manifest. The recommendation does not skip it.

Wall-clock time for a full run becomes the slowest job, not 7.5 plus 12 minutes inside `check`. Billed minutes can rise, because each job pays checkout and setup. On this public repository that is occupancy, not a new invoice. Do not claim a lower bill.

### Concurrency and the aggregator

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true
```

That is the documented PR-only cancellation pattern. It does not repay the six sequential #778 runs. It stops the overlapping case those cancelled runs already hint at.

`plan` always runs. Every other job uses `if: ${{ !cancelled() && needs.plan.outputs.lanes.<lane> == 'true' }}`, except the aggregator. The aggregator is the only job that should ever be a required check:

- `needs` every lane job and `plan`
- `if: ${{ !cancelled() }}`
- fail if `plan` failed, the ledger is missing, or the mode is not one of the known names
- fail if any selected job's result is not `success`
- fail if any non-selected job's result is not `skipped`
- fail if `full` and any narrow job both succeeded

[Using conditions to control job execution](https://docs.github.com/en/actions/using-jobs/using-conditions-to-control-job-execution) is why the required name cannot be `planner` or `mu-smoke`: a skipped required job is a green check.

Keep `workflow_dispatch` on `full`. It is the manual escape hatch, and the current script already refuses to narrow it.

Keep the identical-tree reuse on `main`. Run 40882384278 is the evidence that it already avoids a second full run. The comparison must stay on the tree SHA and the workflow blob, as `checked_run` does now, not on the commit message.

### Expected cost

| Change | Today | After this design | What is measured |
| --- | --- | --- | --- |
| docs, or an identical tree already proven | about 24s, heavy steps skipped | unchanged | run 40882384278 |
| planner sources only, proven base, manifest proof succeeds | 21.4 min `check` plus 9.7 min `mu-smoke`, 31.2 billed min | one Node job, plus PHPUnit of `PlannerApplicationTest` if `build/planner` changed | the 31.2 min is the measured work being replaced; this note does not have an isolated planner timing, so it does not invent one |
| engine or Genie only, proven base | same 31.2 min pair | one uv job | Genie pytest itself was 112s in run 40893068663, after 103s of unrelated PHP and Node in the same `just test`, beside a 9.3 min instance job |
| commerce allowlist only | `commerce-check` plus `mu-smoke` | unchanged | preserving the recovery gate |
| mixed planner, engine, Genie, and commerce PHP, as in #778 | serial `just test`, instance job in parallel, 19.2 billed min to hear a Genie failure | Genie job starts immediately; instance job still runs | failure location in run 40893068663 |
| unknown, rename, workflow, justfile, shared lockfile, unproven base | full | full, but package jobs parallel | selection rule is the existing classifier, generalized |

Public standard-runner dollars stay zero. No larger runner. No new cache action. The planner job reuses the npm cache path the full job already declares. Engine and Genie reuse `setup-uv`'s existing cache and narrow the glob to their own lockfile so an unrelated `uv.lock` does not force a miss. A miss still installs and tests.

## 4. What stays full, or on a real instance

These are not candidates for a fast lane:

- any path the allowlists do not name, including a new top-level file
- `.github/**`, `justfile`, `tools/build.just`, and the classifier test
- a lockfile or manifest installed or hashed by more than one package, unless the planner manifest proof above succeeds
- rename, copy, type change, submodule, symlink, unmerged path
- empty diff, missing base, fetch failure, classifier exception
- `workflow_dispatch`, and a `main` push whose tree was not already proven by this workflow
- `plugins/linker-tools/includes/Planner/**`, `mu-plugins/**`, and `tools/local` tests that build instances
- the `mu-smoke` body: must-use smoke, Genie conversation concurrency, SMTP and notification routing, business and notification capacity, public verification and admission, inquiry price gate, saved-solution reader, page cache, dynamic page cache, inventory credential scope, resource admission, Proforma price gate, Genie inquiry chain, assessment and customer evidence, administrator MFA
- pull and cutover tests, campaign harnesses, and the tools-plus-commerce committed build reproduction
- browser end-to-end tests against a running snapshot; they are already outside this workflow, and they stay outside it

A proven base is part of the condition, not a courtesy. The current `checked_base` rule requires a successful run of this same workflow file on the same tree, or a docs-only chain back to such a run. Keep it. A narrow lane is a delta on a tree that already passed the large suite. It is not a new proof of that suite.

## 5. Proving a silent skip is impossible

The proof is a ledger plus an aggregator, not a hope that the allowlist is complete.

1. Default is `full`. A path is narrow only by allowlist match. An unknown path clears the narrow lanes.
2. `git diff --name-status -z --no-renames` is the only file list. `-z` stops a newline in a path from splitting a record. `--no-renames` stops a rename of an allowlisted file from appearing as a modification. A status other than `A`, `M`, or `D` is `full`.
3. Diff the merge commit, `github.sha`, against `pull_request.base.sha`. That is the tree [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) says the job checks out. Do not switch to GitHub's three-dot path filter.
4. `plan` writes every changed path, its status, and its lane. A path with no lane is an error, not an omission. The existing exception handler that sets `full` stays; it must not become a success.
5. The aggregator checks out the same SHA and runs the same classifier again. It fails if the second ledger differs from `plan`'s output, if any path is absent, or if the selected and skipped jobs do not match the ledger.
6. It fails if a selected job was skipped or failed, and if `full` and a narrow job both succeeded. That is the duplicate-run proof. GitHub will not provide it: a skipped job reports Success.
7. `tools/checks/test_ci_scope.py` already executes the embedded classifier. Extend it, locally, with: planner-only stays `planner`; planner plus `justfile` is `full`; a rename of `apps/planner` is `full`; a symlink is `full`; engine plus Genie is both lanes and not `full`; an unmapped file under `includes/Planner/` is `full`; a `build/manifest.json` change without the planner proof is `full`; an empty diff is `full`. Those tests do not start Actions.
8. Do not use `on.paths`. A 3,000-file diff can skip the workflow, and a skipped workflow does not report the required check. The aggregator cannot prove a run that never started.

This does not prove the allowlist is the smallest safe set. It proves an unmatched or shared change cannot take a narrow result, and that a narrow result cannot be recorded by skipping the job that was supposed to run.

## 6. Migration that does not repeat full CI

1. Extract the classifier to a module imported by the workflow and by `test_ci_scope.py`, or keep the current string-exec test and extend it. Either way, the new cases run on a laptop with `python3 -m unittest`. No push.
2. One pull request changes the workflow. The existing rule classifies a workflow change as `full`. That is the one full run. It prints the ledger it would have used and does not skip any package job. Reviewers see the ledger on that run. They do not need a second full run to discover what the selector would have chosen.
3. Do not push allowlist edits onto that pull request. Each push of a workflow file is another full run. Fix the classifier with the unit tests, then update the pull request once.
4. Put the concurrency block and the `!cancelled()` conditions in that same pull request. A follow-up pull request would be another workflow change and another full run.
5. After merge, acceptance is two ordinary pull requests: one whose diff is only `apps/planner/**`, and one whose diff is only `services/engine/**`. Each should select its lane, skip `mu-smoke`, and finish the package job. A third pull request that touches `justfile` should select `full`. Those three runs are the production proof. They are not a matrix of repeated full runs.
6. Leave `just check` and `just test` in the justfile. Local work can still run the whole set. CI stops using that serial pair as the only way to hear a package failure.
7. Do not retune caches in a later pull request. The planner lockfile path and the per-project uv globs belong in the single workflow change.

If the one full run fails for a product defect, fix that defect in the same pull request only when the fix is required for the workflow change to be true. An unrelated red test is not a reason to re-push the selector.

## Tradeoffs

- Package lanes are coarser than Nx task-based affected. A one-line planner change still runs the whole planner package. That is the cost of having no input graph. Selecting tests by filename would be a guess.
- Parallel full jobs can increase billed minutes. On this public repository the dollar cost stays zero. The gain is wall clock, which is the feedback the #778 failures did not have.
- `commerce` remains slow. Leaving it there protects the recovery suite. A later map from each instance filter to the PHP files it covers is possible, but only with the same fail-closed test: an unmapped commerce file stays on the instance job. That map is not part of this recommendation.
- The planner manifest exception is the only content-aware rule. It is justified by `build-manifest.mjs` hashing all of `build/`. If the proof is hard to write, drop the exception and let a manifest change stay `full`. That is slower and still safe. Do not classify the manifest as planner-owned without the proof.
- `cancel-in-progress` does not fix sequential reruns. Scoped jobs do. Both are worth having; only the second one would have changed the six #778 runs.
- Reuse of a successful pull-request tree on `main` can skip `main`'s own run. That is already the behavior, and it is safe only while the tree SHA and the workflow blob are compared. Keep that comparison boring.
- This note does not claim a future scoped run will be green. It claims the run will be the packages the diff actually touched, that an unknown diff cannot take that shortcut, and that the shortcut and the full set cannot both report success.

## Sources

- [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), GitHub Docs. Paths, path-filter diff limits, Pending checks.
- [Troubleshooting required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks), GitHub Docs. Skipped workflow stays Pending; skipped job reports Success.
- [Using conditions to control job execution](https://docs.github.com/en/actions/using-jobs/using-conditions-to-control-job-execution), GitHub Docs.
- [Evaluate expressions in workflows and actions](https://docs.github.com/en/actions/reference/evaluate-expressions-in-workflows-and-actions), GitHub Docs. `always()` and `cancelled()`.
- [Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), GitHub Docs.
- [Concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency), GitHub Docs.
- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), GitHub Docs. Merge commit, `pull_request_target`.
- [Dependency caching](https://docs.github.com/en/actions/concepts/workflows-and-actions/dependency-caching) and [Dependency caching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching), GitHub Docs.
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions), GitHub Docs.
- [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use), GitHub Docs.
- [setup-uv caching](https://github.com/astral-sh/setup-uv/blob/main/docs/caching.md), astral-sh/setup-uv. Pin confirmed at `action.yml` of `c18668ad3cf93ea998bef934396af7bb5c839dc7`.
- [The Bazel Query Reference](https://bazel.build/query/language), Bazel. `rdeps`.
- [Hermeticity](https://bazel.build/basics/hermeticity), Bazel.
- [Run Only Tasks Affected by a PR](https://nx.dev/docs/features/ci-features/affected), Nx.
- [Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html), Simon Stewart, Google Testing Blog, December 2010.
- [git-diff](https://git-scm.com/docs/git-diff), git-scm. `--name-status`, `-z`, `--no-renames`.
