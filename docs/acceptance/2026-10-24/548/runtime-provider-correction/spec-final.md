# Spec review — final provider correction

Reviewed cumulative `eaacd408638e3db4609fbee68c9031e5aebe4ada..079f1d186bb9378b215fbeb5a7bab16ad8be0291` against the owner’s Apify clarification, applicable AGENTS instructions, `548-weather-acquisition.md` and `548-native-solar-install.md`. Production source is unchanged from `911839a6`; the final commit only prunes duplicate tests and adjusts a test assertion. Standards findings were not read.

**Verdict: PASS within this source/isolated-fixture scope. No actionable Spec findings. The initial P2 is closed.**

`pvgis_transport.py:78–153` supervises the owned HTTP child against the original wall-clock deadline and a monotonic bound, checks task authority while waiting, and kills/reaps the child on deadline, cancellation or lease loss. `weather_http_host.py:18–59` adds the child’s independent exit timer. Blocking DNS/TLS/header/body work therefore cannot extend the worker’s transfer budget through continuous trickling. The child receives only the frozen typed plan and permitted transport environment; no workspace or research/service credentials are forwarded.

The cumulative change matches the corrected contract: official-origin GET only, explicit response rejection and limits, trusted complete TMY validation, retained original/capture hashes, bounded idempotent retry, completed-capture reuse, lease-fenced atomic publication and explicit later selection/save. Launch preflight protects existing storage and running executable identities; immutable release selection binds the complete engine source and project/lock bytes.

Retained evidence inspected: **743 engine tests**, **36 focused tests** before duplicate-only pruning, and **34 local-launch tests**, plus the bounded official-source probe and unchanged native-store readback. The implementation session additionally reports **18 changed transport tests passed** at `079f1d18`; that terminal result awaits its consolidated checkpoint. This review reran no tests.

This verdict does not accept native installation, the native browser weather→PV→energy chain, engineering accuracy, EN/DE desktop/mobile completion, reports/site consumers or production delivery. Those remain open under the installation contract.
