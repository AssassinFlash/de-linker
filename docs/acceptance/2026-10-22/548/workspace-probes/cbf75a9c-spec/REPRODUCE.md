# Fixed source reproduction

Run `python3 rebuild_snapshot.py` in this directory. It reconstructs 121 SHA-pinned application/spec/fixture files and links the existing worktree's Node dependencies. No install, worktree, native instance or external SDK fixture is created.

Then:

```sh
cd apps/planner
npm test
cd ../..
python3 run_mobile_probe.py
python3 run_refusal_probe.py
```

The target suite should pass 54 domain/data and 54 DOM tests. The unmodified prior driver composes the unchanged 563 probe with the unchanged eefe additions; it passes 36 cases at cbf, including both original counterexamples. `prior_review_files` in the archive manifest pins the exact three retained file hashes and their authoritative archive paths.

The new refusal driver verifies those hashes, appends `refusal-probe-additions.mjs` and creates a disposable test module in the actual tests directory so relative imports stay unchanged. At this fixed target it deliberately exits 1: 53 cases pass, and the final persistent-feedback-region assertion fails. Reproducing that red case does not mean the product passes.

The new tests render actual fixed React/Query components. Storage failure, delayed/unknown save replies, source files and geometry are explicit synthetic fixtures. The stateful save fixture exercises the real client draft hook, immutable request body and acknowledgement behavior; it does not claim a native server write or fresh engineering calculation. JSDOM proves the feedback's DOM placement and retained input, not viewport pixels. The physical DE390 observation is attributed to the parent task.

Fixed files are reclaimed only after SHA checks; generated composed modules and the exact dependency link are removed. Unique probes, full logs, run metadata and reconstruction manifests remain. `cleanup.json` records actual cleanup and confirms previous FAIL archives were not modified.
