# Reproduce the fixed 3225 Spec findings

The original temporary snapshot was reclaimed after evidence readback. This
bundle retains unique probes, full logs, exact hashes and fixed Git references.
No dependency tree, running site or database instance is retained.

For another run, first copy this small evidence bundle to a new owned evidence
folder. Work there, preserving the original FAIL archive. Choose one absent
absolute temporary path and record your owner/expiry/reclaim condition.

```sh
review_snapshot=/absolute/owned/temporary/roof-import-spec
python3 rebuild_snapshot.py "$review_snapshot"
python3 run_independent.py "$review_snapshot"
```

The final main probe deliberately exits 1 on this fixed target: 14 passing
scenarios and four failing leaf variants across two parent groups. Node counts
20 tests, 14 passes, 6 failures because the parent groups also fail. The response
parse variants prove P1; the rejected-height→explicit-zero variants prove P2.

The independent revision probe can be run separately:

```sh
cd "$review_snapshot/apps/planner"
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/independent-revision-refusal.mjs
npm test
npm run lint:types
npm run build:check
```

Expected: revision 1/1; source 61 domain/data + 66 DOM passes; type and emitted graph
checks pass. The original raw GeoJSON and accepted asset wire are repository
fixtures, explicitly synthetic and not surveyed. The HTTP replies are controlled;
the client, hooks, components, Query, import journal and project draft store run
their real implementations with isolated IndexedDB transactions.

`rebuild_snapshot.py` restores only the 144 fixed app/build/fixture/spec files
required by these checks using `git show`, then verifies every SHA and links the
existing locked dependencies. No install or new Git worktree is needed. After
recording unique logs, verify/reclaim only those fixed entries, the two generated
probe copies, reconstruction manifest and dependency symlink. Preserve any file
whose SHA changed. Never delete the dependency target or another review archive.

`harness-notes.md` explains two initial probe-only failures and retains their
original bytes/logs. Native/browser, physical touch and production acceptance are
outside this reproduction.
