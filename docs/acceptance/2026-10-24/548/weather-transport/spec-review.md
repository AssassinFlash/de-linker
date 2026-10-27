# Spec review — pinned weather transport component

Base: `79e56ea9011d5e241e7ee05d45018b2e6df8b253`. Source: `b9329c0e31db8ff42511ac66224e6ce0a00108f0`.

Reviewed `git diff 79e56ea9011d5e241e7ee05d45018b2e6df8b253...b9329c0e31db8ff42511ac66224e6ce0a00108f0`: all 69 changed files, including both commits (`a37c4c16`, `b9329c0e`), source/tests, dependency changes, specification, primary-contract excerpts, historical driver, trial receipts and CAS objects. This axis did not read the Standards report.

**Requirements missing or partial:** managed executor/registration, operator RPC/recovery controls, explicit source selection and native EN/DE 1440/390 acceptance remain required by `docs/specs/548-weather-acquisition.md:117–120` and `548-pv-preparation.md:53–69`. The checkpoint expressly excludes those stages; they remain full-goal work, not additional current-component findings.

**Unasked behavior/scope creep:** none found.

**Implemented incorrectly — one P2:** cancellation can skip remote cleanup when it coincides with failed I/O. The specification says, “Cancelled tasks attempt a known run's abort” (`548-weather-acquisition.md:93`), with confirmed cancellation/shared deadline governing cleanup (`:94–97`). After a valid start acknowledgement, a poll can cancel the local task and then raise a connection/read error. `apify_transport.py:185–189` converts that directly to `WeatherProviderUnavailable`; the post-read guard never executes. `weather_acquisition.py:190–197` only cleans up checkpoint-specific exceptions, so the known active provider run receives no abort attempt. A timeout crossing the shared deadline has the same escape. The worker cannot repair this after publication fencing. Preserve the original operation error while inspecting confirmed cancellation/deadline on other exceptional exits; preserve a replacement lease's remote operation. Existing tests cover transient reads and cancellation separately (`test_weather_acquisition.py:87–114,169–192`), not their coincidence.

**Evidence:** inspected retained output: 773 passing tests, including 57 transport/client/acquisition cases; lint/format/types pass. Independently verified all 21 CAS references and 17 research-manifest entries. The rejected HTML trial and successful 1,268,118-byte original support the stated component claim; they establish neither header causality nor full workflow acceptance. No tests, external requests or services were run by this review.

**Result:** 1 Spec finding (P2); full-goal acceptance remains open.
