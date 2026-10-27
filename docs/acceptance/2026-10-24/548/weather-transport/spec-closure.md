# Spec closure — complete cumulative transport increment

Base: `79e56ea9011d5e241e7ee05d45018b2e6df8b253`. Corrected source: `0187cc9210baacf51764bec50da42405a40ac71b`.

Reviewed `git diff 79e56ea9011d5e241e7ee05d45018b2e6df8b253...0187cc9210baacf51764bec50da42405a40ac71b`, covering all 69 changed files across `a37c4c16`, `b9329c0e` and `0187cc92`: transport/client/orchestrator, journal and worker changes, dependencies, tests, specification, primary contracts and actual-trial evidence. Revalidated every file against the pin; 66 files are byte-identical to the independently reviewed prior pin, and all three corrections were inspected. The initial `spec-review.md` remains unchanged. No Standards report was read.

**Previous P2 closed.** The specification requires, “Cancelled tasks attempt a known run's abort,” and cleanup must “not mask the original failure” (`docs/specs/548-weather-acquisition.md:93–97`). `weather_acquisition.py:128–140,212–214` now inspects stop state when I/O bypasses the next checkpoint, attempts known-run cleanup after confirmed cancellation/deadline expiry, and rethrows the original operation error. Stop-state/cleanup failures remain best effort. Replacement lease loss does not abort its resumed provider operation. The actual SQLite/CAS/HTTP-adapter cases at `test_weather_acquisition.py:388–465` exercise concurrent cancellation, deadline expiry and replacement; the existing active-transient case (`:87–114`) still resumes the acknowledged run without another start.

**Missing/partial requirements within this component:** none found. **Unasked behavior/scope creep:** none found. **Remaining incorrect implementations:** none found.

Inspected final retained commands/stdout/JUnit: 776 tests pass, including 60 transport/client/acquisition cases; lint, format (146 files) and types (112 files) pass. Independently checked all 15 changed-engine fingerprints, 21 CAS references, 17 research-manifest entries and corrected 78,432-byte total. Trial evidence supports one rejected origin and one verified original capture, without claiming header causality or general availability. No test, external request, service or database action was executed by this review.

**Result: 0 remaining Spec findings for this component.** The same-goal managed kernel/registration, operator RPC/recovery controls, explicit source selection, native EN/DE 1440/390 acceptance and production delivery remain required (`548-weather-acquisition.md:58–67,101–104,117–120`). This closure does not accept those unexercised stages.
