# Synchronous fixed-bar measurement Spec closure

**Zero additional Spec findings at `0836c245de92ebe8c6348ebfa322fd4fe632becb`.** Independently reviewed the actual 15-file delta from `3853a9ebd2a7848e03958c03a08c2531efc0a71f`; generated assets were checked through the source/build manifest and lazy-entry guard.

The enclosing implementer's native reload found that the earlier focus-target
repair could still scroll using stale bar heights before React effects and
ResizeObserver delivery. The reported intermediate result top was 105 px while
the sticky-bar bottom was 162 px. The prior source/fixture closure did not prove
native clearance; that failed intermediate remains evidence requiring repair.

The new shared `measurePlannerChrome` reads the actual current LC header and
project-bar `offsetHeight` and updates both established root properties. Both
existing measurement hooks use it. `revealActionResult` also calls it synchronously
after the connected-target/native-admission check and before focus/scroll,
addressing the reported ordering failure without waiting for an observer.
The selected result target is now its semantic `h3`, rather than the full content
container. Existing active-view/selected-ID/scope guards and same-run polling
dependencies remain intact. No calculation, stored input, copy, backend or CSS
source changed. This supports the energy spec's result presentation (lines
63–72) and application keyboard/runtime contract.

Focused independent checks passed at the exact pin:

- `energy-workspace.test.mjs` plus `workspace-lifecycle.test.mjs`: **18/18** tests.
  These cover the precise result-heading focus and preparation-error focus,
  save/request/cancel/late-response paths and native identity fences. The new
  delayed-observer probe changes its fixture bar height and clears the cached
  header property, then verifies both fresh fixture heights at `scrollIntoView`.
- Actual source/build hashes match; lazy-entry execution guard **1/1**.

Raw logs: `closure-0836-focused.txt` and `closure-0836-build.txt`. The offset heights
in JSDOM are explicitly mocked, not measured native geometry. Fresh native reload
and screenshot/keyboard clearance are still the enclosing implementer's required
gate. The full goal and production remain separate and open. HEAD was read back
as the exact final pin; only the assigned review directory was written, with no
source/build/browser/database/service changes by this reviewer.
