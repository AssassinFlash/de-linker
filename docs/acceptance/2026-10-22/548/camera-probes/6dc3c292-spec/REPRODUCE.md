# Reproduce fixed 6dc3c292 Spec review

Target `6dc3c292079ec4f654113ecd3e11b631906e6c04`; base `eff8341d5a0eaf24999f42854da6339032c65c9c`. The manifest records 150 pinned source/build/fixture/style/catalogue files; existing dependencies are linked without installation. The original camera counterexample assertions remain byte-identical, with one explicitly documented host option adaptation. Real installed OrbitControls execute in both camera probe variants. Review the local-storage policy and retain at most one active reconstruction.

From this evidence directory, choose an absent absolute temporary directory:

```sh
python3 rebuild_snapshot.py --verify-git
python3 rebuild_snapshot.py /tmp/camera-spec-6dc3c292-rerun
python3 run_camera_probe.py /tmp/camera-spec-6dc3c292-rerun
python3 run_followups.py /tmp/camera-spec-6dc3c292-rerun
```

Expected: original 8/8; actual controls 2/2; actual IDB/focus 5/5. Commands append numbered logs without overwriting old runs. Attempt sources and the reasons for correcting the follow-up harness are retained in `harness-adaptation.md`; these setup/assumption errors are not product findings. There is no GPU drawing or native layout measurement.

Inside the reconstructed `apps/planner` directory:

```sh
npm test
npm run lint:types
npm run build:check
```

Expected: 64 domain/data + 87 DOM, strict types, source/build manifest and emitted graph 1/1. No rebuild is needed. When no process uses the reconstruction, reclaim it from this evidence directory:

```sh
python3 cleanup_snapshot.py /tmp/camera-spec-6dc3c292-rerun
```

Cleanup checks every source/probe hash, refuses unexpected files or active process references, unlinks only the dependency symlink, and verifies the previous f48228a8 archive hashes. Original completion is `cleanup.json`; preserve it before producing a deliberate rerun cleanup record. Native EN/DE × desktop/mobile and complete A–D acceptance remain separately owned by the main task.
