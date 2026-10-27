# Independent Spec closure — managed numerical worker

**PASS for the increment's implementation; zero open Spec findings.**
The [original P2 failure report](../review-spec-af4aa66e/report.md) is preserved
and its cache-availability finding is closed at this pin.

Base: `e96d6beaaf6c9ad24652bbb991f27f410b577009`.
Review pin: `b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3`.
Reviewed the complete three-commit, 28-file diff: 2,201 insertions, 47 deletions,
including unchanged worker/lifecycle hunks, both repairs, tests and deployment
boundaries. Commands:

```sh
git diff e96d6beaaf6c9ad24652bbb991f27f410b577009...b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3
git log e96d6beaaf6c9ad24652bbb991f27f410b577009..b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3 --oneline
git diff --check e96d6bea...b87aa3c9
```

## Closure and contract checks

- **Cache P2 closed.** Spec `548-managed-energy-worker.md:22–28` requires
  “a rotating bounded scan” including “present cache entries” and says a
  nonexistent worker key cannot strand valid tasks. `evaluation_routes.py:20–91`
  now reconciles those rows from verified immutable bytes and wraps its cursor;
  `jobs.py:41,59` preserves the scanner between claims. The independent
  [fixed-pin probe](probe_route_closure.py), using real in-memory SQLite and
  hash-checked memory blobs, repairs the unknown own route on poll 6 after five
  foreign rows at batch size 1. Foreign attempts and the manifest remain
  unchanged. Wraparound repair and named corrupt-request failure also pass.
  Exact command/output: [probe-output.txt](probe-output.txt).
- **Lifecycle preserved.** Spec `:50–55` requires restart draining and refusal
  without a matching worker. `services.py:147–165` drains/stops the worker before
  dependency sync when its environment exists, retaining the explicit first-start
  exception and refusal path. Execution identity, admission transaction,
  receipt replay, cancellation and publication fencing remain intact.
- **Native contract repaired.** Spec `:56–59` requires the stable browser view.
  `Gateway.php:204–205` projects exactly the runtime/limit keys accepted by
  `apps/planner/src/data/readProtocol.ts:60–72`. The native contract regression
  at `test_planner_native.py:203–209` verifies both key sets.

No missing increment implementation, scope creep or incorrectly implemented
requirement remains established. Runtime/site and broad-suite totals supplied
by the owner were not independently rerun. Native v14 reload proof remains
separate evidence (`:79–80`). Customer calculation/result UI, complete workbench,
retained production releases, workload performance and production readback
remain open by `:62–64,81–82`; this review does not accept them.
