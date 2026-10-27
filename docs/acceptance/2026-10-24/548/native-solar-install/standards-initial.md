# Standards review — native launch protection

Initial report, immutable. Reviewed the complete 12-file diff
`git diff eaacd408638e3db4609fbee68c9031e5aebe4ada...bcb9008da711a95b6a548ac69a3c177a059407d0`;
commit `bcb9008da711a95b6a548ac69a3c177a059407d0`, “Guard paired planner launches
and scope weather credentials.”

**Verdict: changes requested — one documented-standard breach.**

- **[P2] Verify the complete paired executable before lifecycle changes.**
  `tools/local/src/linker_local/services.py:160–170` accepts a running HTTP
  process when its `runtime_sha256` matches the target probe, then drains and
  stops the pair. That probe is `RuntimeSnapshot.capture()`, whose inventory
  covers `planning/*.py`, `pyproject.toml` and `uv.lock`; it excludes
  `src/linker_engine/application.py` and other imported engine modules. With
  the ordinary unselected-checkout path, changing the HTTP entry therefore
  leaves this identity unchanged. An isolated fixture changed that entry,
  captured identical real snapshot hashes, and exercised actual
  `services.serve()` until a sentinel intercepted `drain()`; no process or
  persistent DB was touched. Authoritative main `AGENTS.md` §0 requires
  verification of the current process version, disk executable, launch
  definition and data compatibility before restarting; ADR 0001 requires the
  matching retained executable. The new guard cannot establish that contract
  from this partial identity. Bind and compare the complete relevant
  HTTP/worker executable and launch identity before drain/stop/sync, retaining
  the old pair on mismatch. Reproducer and results are in `standards-tests.txt`.

**Heuristic smells:** none material identified. The source-selection and
provider-environment modules concentrate their policies behind small interfaces;
the Fowler baseline remains judgment, not an additional hard rule.

Current AGENTS, CONTEXT, domain guidance, accepted ADRs 0001/0002 and the named
native-install/hosting/managed-worker contracts were read. No Spec report was
read. Independent checks passed: 53 local release/provider/launch/lifecycle
tests, the real release-probe subprocess test and strict mypy on four changed
local modules. Added-line legacy/model-channel checks were clean.

The actual schema-2 native store and existing pair remain untouched. This
review neither installs the new pair nor claims native/production acceptance.
