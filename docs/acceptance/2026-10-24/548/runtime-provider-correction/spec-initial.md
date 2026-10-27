# Spec review — initial provider correction

Reviewed `git diff eaacd408638e3db4609fbee68c9031e5aebe4ada...d734dee733c4e841e964992e582136c5391dfe83`, including `bcb9008d` and `d734dee7`, independently of Standards. Authority: current owner clarification, AGENTS, CONTEXT, ADR 0001/0002, the four named solar/weather specifications and saved-project/publication contracts.

**Result: changes required — one P2 finding.**

- **Overall download deadline does not bound a streaming read** (`services/engine/src/linker_engine/planning/pvgis_transport.py:113-117`). The specification requires: “Enforce connection/read/overall time” (`docs/specs/548-weather-acquisition.md:23-24`). `response.raw.read(65536)` can perform repeated socket reads before returning, while the socket timeout measures inactivity. Bytes arriving within that timeout keep the call blocked; the deadline, cancellation and lease checkpoints run only afterwards. An isolated real socketpair/urllib3 stream reproduced a **0.443 s** call against a **0.10 s** overall budget and **0.08 s** socket timeout, supplying one byte every **0.03 s**. A longer trickling response can occupy the heartbeat-renewed worker far beyond its frozen budget. Bound the blocking operation itself and retain a regression covering continuous slow streaming, rather than only checking expiry before/after a whole block.

No other missing or incorrectly implemented source behavior, or unrequested scope, was found in this diff. The fixed official request, credential exclusion, retained capture, explicit selection/save, ownership, publication fencing and launch protections match the corrected contract.

Independent verification: **39 engine tests and 37 local-launch tests passed**; the additional socketpair probe reproduced the finding. Commands, output and probe are in `spec-tests.txt`. No external endpoint, native project store, native service process or native configuration was used or changed.

This accepts only the reviewed source/isolated fixtures after the finding is closed. Actual official-source availability, paired native installation, full native weather→PV→energy, EN/DE desktop/mobile and production acceptance remain open, as required by weather-acquisition lines 35–40 and native-solar-install lines 55–75.
