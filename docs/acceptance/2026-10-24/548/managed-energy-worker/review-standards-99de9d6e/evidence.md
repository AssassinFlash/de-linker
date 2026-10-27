# Scope and reproducible read-only checks

Review ownership: only this directory. Existing checkout and parent-run acceptance artifacts were reused; no source/configuration/runtime/database/process/git changes were made. Available space before writing these small reports was 822 GiB; no backup, snapshot, instance, worktree or dependency copy was created.

```sh
git rev-parse HEAD
# 99de9d6e5bcdb9417edbbfadbb694342e5a2234f
git log --oneline e96d6beaaf6c9ad24652bbb991f27f410b577009..99de9d6e5bcdb9417edbbfadbb694342e5a2234f
# 99de9d6e fix(planner): rebuild stranded routes and drain before dependency sync
# af4aa66e feat(planner): manage version-matched numerical workers and transactional draining
git diff --stat e96d6beaaf6c9ad24652bbb991f27f410b577009...99de9d6e5bcdb9417edbbfadbb694342e5a2234f
# 26 files changed, 2184 insertions(+), 47 deletions(-)
git diff e96d6beaaf6c9ad24652bbb991f27f410b577009...99de9d6e5bcdb9417edbbfadbb694342e5a2234f | rg -n '^\+.*(tv_b2b_|Linker_AI_|dlk-|TODO|FIXME)'
# No matches; rg exit 1.
```

Every changed hunk was read in these groups:

- Research/spec/operations: `HOSTING.md`, `548-managed-energy-worker.md`, `justfile`, candidate unit, `planner-worker.md`.
- Engine implementation: `energy_kernel.py`, `errors.py`, `evaluation_routes.py`, `execution_control.py`, `execution_identity.py`, `http_app.py`, `jobs.py`, `schema.py`, `worker.py`, `worker_host.py`, `worker_policy.py`, `workspace.py`.
- Engine tests: `test_execution_routes.py`, `test_private_http.py`, `test_worker_host.py`, `test_worker_policy.py`.
- Local implementation/tests: `cli.py`, `planner_worker.py`, `private_config.py`, `services.py`, `test_planner_worker.py`.

Additional surrounding code read: planning `canonical.py`, `energy_inputs.py`, `storage.py`, `runtime_config.py`, `runtime_snapshot.py`, full `jobs.py`/`worker.py`, and local `processes.py`/service tests. These resolve strict JSON validation, immutable hash verification, transaction and publication fencing, runtime capture, and PID birth ownership rather than inferring those properties from names.

Applicable non-tooling rule locations: canonical AGENTS lines 8–12 (retention and service maintenance), 78 (modularity and sourced thresholds), 85 (separate acceptance gates), 89 (model routing), 93–94 (legacy-code absence and protected production writes); owned AGENTS lines 64–71 (planner exception, Python and thresholds); README lines 22 and 87 (project structure and locked dependency use); CONTEXT lines 35–53 (architecture and authority). Managed-worker spec lines 10–58 defines the increment boundaries and lines 60–78 distinguishes development choices from final-goal acceptance.

No runtime tests were repeated: the assignment prohibits process/database mutations and the enclosing task already owns test execution. Reviewed tests explicitly cover two identities, bounded route rotation, exact receipt replay, admission/drain ordering, duplicate readiness ownership, SIGKILL lease recovery, SIGTERM completion, cancellation fencing and credential exclusion. Their implementation was assessed as evidence of intended coverage, not as fresh execution proof.
