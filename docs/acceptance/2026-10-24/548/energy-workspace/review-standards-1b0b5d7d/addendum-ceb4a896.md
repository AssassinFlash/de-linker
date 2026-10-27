Standards closure at `ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a`: **zero remaining findings.**

Reviewed the complete immutable `443eb71d7a9245942aa0d9a6e6de53acde9a867c...ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a` delta: eight files, including the hook, full new regression test, emitted asset changes and manifests. The original full 65-file review and previous repair closures remain separately identifiable. The same repository standards sources, canonical operational overrides and complete Fowler baseline apply. No hard documented violation or actionable heuristic smell was found.

`apps/planner/src/data/useEnergyRuns.ts:108–139` pins an automatic history selection only while active and admitted, with no explicit selection and a fully read/validated run whose ID matches the chosen run. It calls the existing `select` path, which rechecks current scope, validates the ID, verifies the URL's project and updates native navigation through the established helper. This keeps selection and URL ownership together; it adds no duplicate navigation implementation. Explicit selections remain unchanged. The effect becomes inert after selection and does not depend on a polling response object.

The complete `tests/energy-runs.test.mjs` uses the existing recorded managed result with a narrow read-only transport fixture. It asserts no reads while inactive, no URL pin from a summary alone, no navigation change after admission withdrawal and a URL pin after readmission. Its identity and URL assertions establish the intended behavior directly. No new copy, numerical rule, backend operation or dependency is introduced.

Fresh independent checks at the exact pin passed: source-manifest guard, one actual emitted lazy-module graph test and 19 React hook/workflow/lifecycle tests. Added handwritten lines contain no legacy markers. Commands and stdout are recorded in `evidence.md` and `closure-checks-ceb4a896.log`.

Only the assigned review directory was changed. This closes the Standards axis through this pin; mocked transports and jsdom do not establish native viewport, deployment or production acceptance.
