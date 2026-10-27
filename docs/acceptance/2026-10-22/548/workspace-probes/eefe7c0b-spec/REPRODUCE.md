# Fixed corrected-source reproduction

Run `python3 rebuild_snapshot.py` in this directory. The manifest reconstructs 121 SHA-pinned fixed application/spec/fixture files and links the already installed worktree dependencies. No worktree, dependency installation or native instance is created.

The original 563 probe is retained byte-for-byte at `apps/planner/tests/independent-journal-probe.mjs`; its SHA256 is `d0cf137f95dc530853ad9ac620afd30531e69250fb65b7631fd2294ce2fff9c8`. Then:

```sh
cd apps/planner
npm test
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/independent-journal-probe.mjs
cd ../..
python3 run_mobile_probe.py
```

At eefe, the target suite passes 54 domain/data and 54 DOM tests. The unchanged original probe passes 19 cases, including the prior Site-start counterexample. The mobile driver verifies the prefix SHA and appends `mobile-probe-additions.mjs` into a disposable test module in the same tests directory, preserving relative imports. This combined probe deliberately exits 1: 35 cases pass and the final stale-refusal semantic counterexample fails. Successful reproduction of the expected red case is not a product PASS.

The original components and React/Query execute in JSDOM. Transport, storage, numeric project inputs and file objects are explicit synthetic fixtures. No native WordPress or external SDK page is operated. DOM focus/order establish navigation semantics; they do not establish physical scrolling, viewport layout, hardware touch or a real calculation outcome.

Exact commands/statuses/logs and generated-module SHA are retained. The initial admission-withdrawal timing assumption and its deterministic correction are documented in `harness-correction.md`; the old failed-assumption log remains separate from the final product failure.

All fixed source files and disposable composed modules are reclaimed after SHA checks; unique evidence and reconstruction instructions remain. `cleanup.json` records the actual paths, counts and readback. The prior 563 FAIL evidence is never edited or relabelled.
