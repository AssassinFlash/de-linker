# Standards addendum: repeated successful application

2026-10-24. Independent Standards axis at `726e326b5c3ce322a2e1471008483a10e9e3c3b1`. Reviewed `git diff 786d0db9...726e326b`, in context of the [previous addendum](../review-standards-786d0db9/REVIEW.md) and the [full base review](../review-standards-02c87049/REVIEW.md). The same current owner rulebook, isolated-runtime exception and twelve Fowler judgment heuristics apply.

**Documented-standard findings: 0. Fowler heuristic findings: 0.**

The small source change replaces a one-time success boolean with a local count of successful applications. Functional increments occur only after an accepted project commit. Each success therefore changes the effect dependency and reveals the existing result target, including undo → resume → resubmit without editing a field. Starting or changing a drawing no longer needs an unrelated reset. This count remains disposable UI state: it neither enters persistence nor decides whether a roof is present. Status still derives from actual prepared/current project geometry equality; journal, source, ownership and command boundaries remain unchanged.

The extended actual-component fixture repeats the application, checks result-target focus and checks that the reapplied geometry equals the original accepted geometry. Independent execution passed **2/2** workspace component tests with no act warnings. `build:check` matched source/build hashes and passed its built-module identity fixture (**1/1**). No new wording, locale, CSS, dependency, PHP, service or global configuration change. Added-line scans found no prohibited legacy identifiers or credential patterns.

The full base-to-pin `git diff --check` still flags whitespace in bundled MapLibre shader text at generated `MapViewport-DEU-DlpF.js:62`. This is retained as a tooling-only diagnostic in `CHECKS.json`; no clean full-diff whitespace claim is made.

These are component/library and build checks, not native viewport, GPU, provider, touch, production or complete-goal acceptance. Reviewer writes are confined to this directory; no runtime or application file was changed.
