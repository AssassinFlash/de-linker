# Spec review — managed weather checkpoint

Reviewed the complete 31-file cumulative diff
`4140663f950999b55fe3c3b5bd0dfff0ebf9049b...cf310435d60749b89dd0de182c3bfe8189ef47a6`
and both commits (`a2dc8b42`, `cf310435`). Sources: the owner-supplied current
AGENTS.md, CONTEXT.md, weather-acquisition contract, underlying managed-worker,
energy-job, PV-preparation and PVGIS contracts, and the retained #548 map
readback. This axis was independent and serial; no Standards report was read.

**No findings.** No missing/partial requirement invalidates this backend
checkpoint, no scope creep was identified, and no implemented behavior was
found to contradict its contract.

Source tracing covered schema-1/2 queue migration and rollback, preservation of
child routes/leases/receipts, shared HTTP/worker/operator registry identity,
ownership and receipt replay, exact frozen inputs/plan/runtime, original-TMY
and metadata reuse, atomic owned-source publication, explicit saved selection,
stale-source rejection, cancellation with an inactive producer, bounded cleanup
and retries, and the single consumed Actor-start permit. The subprocess fixture
resumes a retained capture without an Apify credential and then executes energy
and PV tasks; provider responses used to establish the capture are explicitly
simulated.

Recorded verification was read after completion: `commands.json` identifies
`cf310435d60749b89dd0de182c3bfe8189ef47a6` and records successful lint, format,
types and the full engine suite; stdout/JUnit record **798 passing tests, zero
failures/errors**. The independent worker-host case is included. This reviewer
did not rerun tests, contact a provider, alter the live runtime, or change code.

The remaining native/operator controls, EN/DE 1440/390 acceptance, paired
code/database installation and downstream engineering/production delivery
remain requirements of the same complete goal. This matches the explicit
boundary: “this is not completion of the customer workflow”
(`docs/specs/548-weather-acquisition.md:188–192`). The paired rollback requirement
is retained at lines 175–180; the passing isolated fixtures do not authorize or
prove a live migration. Existing external-capture evidence establishes only
the previously recorded provider trials.
