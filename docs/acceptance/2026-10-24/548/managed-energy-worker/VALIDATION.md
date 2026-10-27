# Managed energy executor: validation

Base `e96d6beaaf6c9ad24652bbb991f27f410b577009`; final implementation
`b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3`. This advances the active complete
workbench goal. It does not accept an unbuilt customer calculation/result UI,
equipment/country qualification, the complete application or production.

## What now executes

The existing numerical Worker is instantiated by an independent managed Python
process. The owned local runner starts it after authenticated HTTP readiness,
matches runtime/execution/storage identity, and resumes evaluation admission
only after the actual child publishes a live, generation-specific record.
Numerical execution receives no service/provider/model credentials. Existing
lease, heartbeat, cancellation and immutable publication remain the job authority.

New jobs route transactionally from their frozen context. A bounded rotating
verification also rebuilds absent or wrong cached routes, including a key with
no active worker. Other versions remain queued for their matching executable
without consuming attempts. A transactional drain rejects new intents, preserves
exact receipts and permits existing work/read/cancel. Dependency sync follows
the drain/stop of an existing local executor. Candidate production hosting is
documented and syntax-checked; no production unit was installed or started.

## Checks and actual results

Commands run from their own Python/PHP project directories unless stated.

| Check | Result |
| --- | --- |
| Engine `uv run --locked pytest tests -q` at final source | **612 passed**, 36.20 s; [exact output](engine-final.txt) |
| Engine `uv run --locked mypy src` | All **111** source files pass strict configured analysis |
| Engine Ruff source / changed tests and format | Pass; no dependency or mathematical model change |
| Routing/host/private HTTP after route repair | **106 passed**, 9.95 s |
| Actual independent worker subprocess cases | **8 pass** inside full suite: two numerical identities, three startup identity refusals, duplicate ready path, forced-loss recovery, cancellation and SIGTERM/in-flight fencing (parametrized count) |
| Strict worker policy | **13 pass** inside full suite; absent/coerced/nonfinite/incoherent settings refused |
| Local manager/process/CLI/services targeted check | **33 pass** before route repair; affected manager/services/CLI **25 pass** after dependency-order repair |
| Local non-stack suite | **88 pass / 25 opt-in native tests skipped**, before addition of the new explicit native contract assertion |
| Local Ruff / configured strict mypy | Pass; **17** source files |
| Native existing p548 bootstrap contract + guest save/replay/conflict/ownership | **2 pass**, 24 deselected, PHP 8.3 and explicit owned instance |
| Plugin PHPCS changed gateway + full configured PHPStan | Pass |
| Plugin complete unit suite | **290 tests / 2,365 assertions** pass; [exact output](php-unit-final.txt) |
| Existing planner `npm run --silent build:check` | Source/manifest match, lazy built-module guard **1 pass**; unchanged emitted entry |
| Candidate systemd unit on actual systemd 255 host | Exit **0**, no analyzer diagnostics; temporary unit removed; [record](systemd-verify.json) |
| Independent reviews | Final **Spec 0 open; Standards 0 violations / 0 actionable smells**; [review record](REVIEW.md) |
| Computer Use | EN/DE × 1440/390 actual page checks; v14 retained, zero horizontal overflow; [native record](NATIVE.md) |

The subprocess proofs use actual CAS/SQLite and EnergyKernel. SIGKILL/cancel
observation uses a genuine 5,000 one-minute interval replay; it does not sleep
inside a fixture handler. A killed attempt publishes no result and its lease
is recovered by a fresh matching process. The separate local-manager fixture
simulates only readiness/process ownership; it makes no energy assertion.

## Running-site proof

[host_probe.py](host_probe.py) used real HTTP on p548's existing composed engine,
private authentication held only in memory, real CSV/scenario asset intake,
revision save, queue and the runner-owned `local-p548` executor. No direct
Workspace enqueue or test handler substituted for that request path.

In the two-hour synthetic fixture, gross demand is **4 kWh**, PV directly
supplies **2 kWh**, 2 kWh AC enters the battery at 0.9 charge efficiency and
leaves it at 0.9 discharge efficiency, yielding **1.62 kWh** to load. Thus solar
load is **3.62 kWh** and grid import **0.38 kWh**. The actual managed result agrees
within the explicit replay tolerance, at attempt 1; equipment release remains
`not_assessed`. These are analytic test values, not measured site/weather/SKU
or manufacturer efficiency claims.

The live drain returned pending=0, replayed the original completed intent and
returned **503 `service_draining`** for a new intent. Engine-only restart produced
a fresh worker PID/generation with the same source/model/settings/store identity;
the completed run and result hash survived and the runner reopened admission.
The original **161 projects / 217 input revisions** retained exact revision,
title and input hashes. Genie and PHP process records and runtime policy bytes
remained unchanged. [Initial af4 proof](http-af4aa66e.json), [route-fixed proof](http.json),
[final readback](readback.json). The latter proof ran at `99de9d6e`; `b87aa3c9`
changes only native gateway/spec/test, so its numerical identity is unchanged.

## Failures found and corrected

1. Initial host-test collection used a nonrelative test helper import; it was
   corrected to the existing planning test package. Ruff's Callable/PEP 695
   corrections and a missing parent directory in the stale-ready test fixture
   were fixed before pinning. Those were harness issues, not energy results.
2. A root-cwd mypy invocation omitted the engine's Pydantic/pvlib configuration
   and produced two unrelated diagnostics. Running from the actual engine
   project exposed one redundant cast in new code; that cast was removed and
   all 111 configured source files pass. No analysis rule was weakened.
3. An overbroad local-suite invocation entered the existing stack fixture with
   PATH's PHP 8.5. Its 19 setup checks refused the required PHP 8.3 **before
   creating a stack**. Rather than allocate redundant instances, checks here use
   the non-stack suite and the actual existing p548 with explicit PHP 8.3.
   A full new-stack integration pass is not claimed.
4. Independent Spec review at `af4aa66e` reproduced a queued valid task stranded
   by an unknown cached key. `99de9d6e` repairs all pending cache entries through
   bounded rotation; the original failure and independent final closure remain
   separate evidence. No failed job was relabeled or frozen manifest rewritten.
5. Native browser reload found `invalid_session_reply`: private worker identity
   additions flowed unfiltered into the strict frontend runtime contract. The
   added native test first failed on exactly those two extra fields. `b87aa3c9`
   projects the existing runtime/limit allowlists at WordPress bootstrap. The
   test, original guest ownership path and native 4-way reload now pass. The
   frontend validator was not weakened and project data was not changed.

The existing Node built-module check emits its already known CommonJS/ESM
package classification warning while passing. No global/package setting was
changed to suppress it. No customer-facing wording was added in this backend
increment; the already reviewed system-level ToolIdentity was read back.
