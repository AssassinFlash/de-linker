# Independent Spec review — managed numerical worker

Verdict: **changes required at the reviewed pin**. One P2 finding.

Base: `e96d6beaaf6c9ad24652bbb991f27f410b577009`.
Pin: `af4aa66e9f4994efcbe2159f428a93cc9007c71a`.
Commit: `af4aa66e feat(planner): manage version-matched numerical workers and transactional draining`.

Reviewed all hunks in the full 26-file diff (2,112 insertions, 47 deletions),
including tests, local lifecycle, candidate unit and hosting evidence. Full
comparison (read in path groups), commit inventory and whitespace check:

```sh
git diff e96d6beaaf6c9ad24652bbb991f27f410b577009...af4aa66e9f4994efcbe2159f428a93cc9007c71a
git log e96d6beaaf6c9ad24652bbb991f27f410b577009..af4aa66e9f4994efcbe2159f428a93cc9007c71a --oneline
git diff --check e96d6bea...af4aa66e
```

Standards context: current root `AGENTS.md`, worktree `AGENTS.md`, and current
`docs/agents/local-storage.md`; no stack was created. Contract sources:
`548-managed-energy-worker.md`, `548-energy-job.md`, `548-service-hosting.md`,
and `548-energy-replay.md` under `docs/specs/`.

## Finding

**[P2] Reconcile cached routes that point to an inactive execution key.**
`services/engine/src/linker_engine/planning/evaluation_routes.py:24` considers
only jobs with no cache entry. `jobs.py:70–72` selects only the cached key;
the authoritative correction at `jobs.py:105–115` occurs after that selection.
Thus a valid A job cached as B is invisible to A indefinitely if B has no
live worker. The cache controls availability despite intact immutable bytes.
It can also prevent a safe drain from completing.

Spec, `docs/specs/548-managed-energy-worker.md:22–26`:
“A derived routing index is an additive, rebuildable cache in the existing
database, not another project authority” and “a wrong cached route is repaired
before leasing.” This behavior partially implements that requirement.

The bounded [probe](probe_route_cache.py) imports planning-module bytes from the
immutable review pin in memory and uses real in-memory SQLite and hash-checked
memory blobs. Five A polls produced no
lease; the valid job remained queued, attempt 0, wrong route unchanged. Removing
only the cache row immediately leased the same request on attempt 1. Exact
command/output: [probe.log](probe.log). Reconciliation must eventually inspect
present wrong routes independently of a worker for their cached key.

## Remaining scope and verification

No additional increment requirement or scope-creep finding was established.
Routing exclusions, transactional admission/receipt ordering, process identity,
real-kernel registration and production boundaries otherwise align with the
reviewed contracts. Existing suite totals supplied by the owner were not rerun.
Owned-site HTTP/result and v14 reload verification are separate evidence.
This review accepts neither the customer calculation/result UI nor the full
workbench, retained production releases, workload capacity or deployment.
