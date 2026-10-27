# Final Spec review — weather recovery

**PASS for the scoped backend increment. The original P2 finding is closed; no new scoped Spec findings.**

Both refs resolve. Reviewed the complete 28-file cumulative diff `cfe5a5f98a3c9f89d6643c04fa9f9383022ac664...c1ddef08c34075f1667972a62a95e3a0d2f55a6d` and all five commits: `704c4fdd`, `dc613c36`, `0969e006`, `7be28fef`, `c1ddef08`. Applied current main `AGENTS.md`, `CONTEXT.md`, weather-acquisition/managed-energy-worker specifications and relevant project/PV/private-hosting contracts. The original `spec-review.md` remains unchanged.

The requirement “Recovery outputs retain their exact evidence dependencies under that job” (`548-weather-acquisition.md:222`), clarified at lines 227–230 for acknowledgement INPUT, is now satisfied. `weather_reconciliation.py:77–85` retains the exact bytes returned by the validated `verified_input` call and the canonical server-owned submission; line 102 places both hashes directly in the successful job output's dependencies. The effective response is checked against the pinned safe full INPUT before retention, preserving its original whitespace without accepting arbitrary provider fields. Archive verification already checks job-output dependencies, so this evidence participates in backup validation and restoration without requiring a weather capture.

The new parametrized FAILED/ABORTED regression source exercises actual queued maintenance with simulated provider responses, exact whitespace-preserved INPUT, no capture or owned assets, retained original failure, archive restoration and rejection of a backup missing referenced INPUT bytes. This review inspected those tests; it did not execute them or independently certify the separately reported test counts.

No remaining missing/partial scoped requirement, unrequested scope creep or incorrectly implemented scoped behavior identified. Rechecked private admission/replay, finite budgets, producer-state restrictions, lease fences, separate evidence publication, matching-runtime resume, schema migration and remote-aware draining.

Native customer controls, actual-installation APIFY credential wiring, EN/DE 1440/390 proof, paired schema-4 installation/rollback and the full 548 goal remain open. The documentation correctly distinguishes the uninstalled new runtime from restoration of the absent old schema-2 worker, whose process identity changed. No Standards reports, external requests, Actors or live runtime/database actions were used in this review.
