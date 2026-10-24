Standards closure at exact pin **`94d4b31c169a4e04197b9b33d6dcadd70d54e3a1`**, combining the original full review from `b5b89ee387fb55d85ad57ae7b4a0b9f8de65ea03` through `cbadc619` with inspection of every hunk in the four-file correction.

- **Dependency-parser duplication — CLOSED.** `pv_profile.py:130` now owns the exact dependency-key/type checks in `_model_dependencies`. Both admission and frozen reconstruction consume it. Their separate project-binding and reproducibility checks remain intact.
- **Execution/witness convention duplication — CLOSED.** `pv_conventions.py:14` provides one frozen value object containing primitive immutable fields. Physics calls and witness serialization consume that same instance. Extracted numerical arguments retain their previous values. Witness metadata intentionally changes: `solar_position` now records the actual API method `nrel_numpy`, and previously omitted explicit settings are included.

**Open findings: zero. New findings: zero.** I found no new documented breach or actionable Fowler concern. The correction preserves ownership checks, receipt behavior, resource limits and frozen reconstruction validation.

This closure is based on read-only inspection; I made no edits and ran no tests. It does not claim an outcome for the parent’s pending regression/lint/type checks, or provide native, production or complete-goal acceptance.
