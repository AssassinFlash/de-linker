# Reproduce the fixed camera Spec review

Target: `f48228a87894c23f68d180675d05b902139d531e`; base: `eff8341d5a0eaf24999f42854da6339032c65c9c`.

The 147 tracked source/build/fixture files are reconstructed with `git show` and individually SHA-256 checked against `snapshot-manifest.json`. Existing planner dependencies are linked, never copied or installed. The three unique probe files are retained here. No browser, site, GPU or new Git worktree is required. Only one active reconstructed snapshot may be retained. Read the repository's local-storage policy, record the chosen absolute temporary directory and reclaim it after the run.

From this evidence directory, use an absent temporary path:

```sh
python3 rebuild_snapshot.py --verify-git
python3 rebuild_snapshot.py /tmp/camera-spec-f48228a8-rerun
python3 run_camera_probe.py /tmp/camera-spec-f48228a8-rerun
```

On this fixed target the independent command intentionally exits **1**: Node reports **8 tests, 6 pass, 2 fail**. It appends new numbered logs without replacing the original attempts. The two red cases are the selected actual panel pose's owning roof and resize after changing current geometry. All source assertions remain in `camera-probe.mjs`. Attempt 1 is a retained host setup error, described in `harness-notes.md`; attempt 2 is the valid result.

From the reconstructed `apps/planner` directory, rerun the locked checks:

```sh
npm test
npm run lint:types
npm run build:check
```

Expected: 64 domain/data tests, 87 DOM tests, strict TypeScript, source/build manifest and one emitted graph test all pass. No test run rebuilds the emitted assets. After the test processes exit, reclaim from this evidence directory:

```sh
python3 cleanup_snapshot.py /tmp/camera-spec-f48228a8-rerun
```

The cleanup refuses changed or unknown files, mismatched links, or active process references. It removes only SHA-matching reconstructible files and the dependency symlink, preserves its target, verifies the prior eff8341d evidence hashes, reads back absence and records free space. Original completion is in `cleanup.json`; a deliberate rerun should preserve that record before producing a fresh cleanup record.
