# Standards review — initial pinned increment

Base: `79e56ea9011d5e241e7ee05d45018b2e6df8b253`. Source pin: `a37c4c16a0f0659214ea24791a2bcfd2747bd121`.

Reviewed every hunk of all 68 changed files: transport/client/orchestration, tests, dependencies, spec, primary research and retained trial evidence. Applied current owner AGENTS §§0/6, applicable isolated-planner rules, engine conventions and the weather-acquisition checkpoint. Inspection and hash readbacks only; no tests, network or runtime actions. Subsequent working-tree corrections are excluded.

- **P2 — cleanup can replace the original failure.** `services/engine/src/linker_engine/planning/weather_acquisition.py:87` catches only `PlanningError`; the `LeaseLost` handler at line 181 also performs an unguarded SQLite cancellation read through line 57. A database or unexpected abort/journal exception therefore replaces the original lease/deadline/polling error. This violates `docs/specs/548-weather-acquisition.md:96–97`, requiring cleanup failures not to mask the original failure. Make cancellation inspection and abort cleanup best effort, retain the known provider ID without inventing confirmation, and test unexpected/database failures through the public acquisition seam.

- **P3 — unsupported causal comment.** `services/engine/src/linker_engine/planning/weather_submission.py:26` says omitting the client identity “produced” the rejection. Separate trials establish one rejection without that header and one success with it; they do not establish causality. Owner AGENTS §6 requires evidence-backed source claims. State the observations and explicitly leave the cause unproven.

- **P3 — stale provenance digest.** `docs/research/2026-10-24-weather-transport/raw/manifest.json:10` records FINDINGS as 10,814 bytes/hash `9c405fd7…`; the committed file is 13,478 bytes/hash `7d571571…`. This breaks the claimed evidence readback (owner AGENTS §§0/6). Regenerate its final digest and distinguish original research-agent counters from subsequent owner trials. The other research entries and all 21 retained CAS references match their hashes.

- **P3 — historical driver has misleading execution location.** `docs/acceptance/2026-10-24/548/weather-transport/component-trial-repair-driver.py:22` derives a repository root from its former scratch location. Here it resolves beneath `docs/acceptance`, creates a nested output directory before the guard, and cannot find its inputs. Under owner AGENTS §§0/6, preserve the historical bytes as text and document their original location/prerequisites.

No additional actionable Fowler smell. Worst finding: P2. Trial evidence supports a bounded component checkpoint only; managed executor/RPC/native and full-goal/production acceptance remain outside this review.
