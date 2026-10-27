# Spec review — weather recovery

Review range: `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664...7be28fef8f60f1c8c9960f3764ca20bb6894c377`. Both refs resolve. Read the full cumulative diff across all 28 files and all four commits: `704c4fdd`, `dc613c36`, `0969e006`, `7be28fef`. Independently verified the final `0969e006...7be28fef` delta: only the installation paragraph in `548-weather-acquisition.md` changed; source/tests are identical.

Authority: current main `AGENTS.md`, `CONTEXT.md`, weather-acquisition and managed-energy-worker specs, and relevant project/PV/private-hosting contracts. Source-only review; no tests, runtime/database operations, external requests or Standards reports were used.

**Result: one missing scoped requirement (P2).**

- **Retain the INPUT evidence used by recovery acknowledgement.** `services/engine/src/linker_engine/planning/weather_reconciliation.py:75` discards the exact bytes returned by `verified_input`; lines 89–108 retain only the plan, manifest, run observations and any subsequent capture. The spec requires “Retain the exact submitted/effective inputs” (`548-weather-acquisition.md:43`) and “Recovery outputs retain their exact evidence dependencies under that job” (line 222). An acknowledgement can succeed without any capture, including for an aborted/failed run that cannot later supply one. Its successful durable output and backup then contain no received INPUT evidence proving the nonce correlation. Retain the verified safe INPUT bytes as a dependency of that acknowledgement output; do not rely on a later capture to preserve them.

No unrequested scope creep or additional incorrectly implemented scoped behavior identified. Admission/replay, original budgets, inactive-producer restrictions, separate recovery publication, runtime-bound resume, schema-4 migration and remote-aware drain behavior otherwise match the scoped contract. The constructor and abort-entry fences address their specified boundaries.

This is a backend increment review, not full-goal acceptance. Native customer source/model/selection/recovery controls, APIFY credential wiring for installation, EN/DE 1440/390 proof and paired schema-4 installation/rollback remain required. The corrected paragraph distinguishes the uninstalled new runtime from restoration of the absent old schema-2 worker using retained source/lock, interpreter and policies; that restoration changed process identity. This review did not independently inspect that live restoration.
