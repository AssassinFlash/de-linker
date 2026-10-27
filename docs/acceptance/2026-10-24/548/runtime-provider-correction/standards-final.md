# Standards review — runtime provider correction

Reviewed cumulative diff
`eaacd408638e3db4609fbee68c9031e5aebe4ada..079f1d186bb9378b215fbeb5a7bab16ad8be0291`
(71 files). Authority: main-checkout `AGENTS.md` §§0, 4–5; local owner
clarification §6; `CONTEXT.md`, domain guidance, accepted ADRs 0001/0002 and
the native-launch, hosting and managed-worker contracts. No Spec report was
read.

**Verdict: PASS for this diff — no outstanding documented-standard breach.**

**Mandatory standards:** The historical P2 is closed. `RuntimeSnapshot.capture`
now binds all engine Python modules, including `application.py`, project/lock
bytes and tracked installed dependency versions. The HTTP-entry mutation
regression checks that changing that entry changes the runtime identity.
`compatible_release` checks the existing schema without opening `Workspace`;
`services._serve` compares the live worker and HTTP runtime before drain, stop,
existing-environment synchronization or WordPress updates. Installed selections
verify complete source inventories, hashes, ownership and the retained
environment, refusing mismatches rather than selecting checkout source.

The runtime implements the owner's Apify separation: official typed JRC GETs,
no research credential lookup or provider account dependency, explicit failures,
and a supervised child bounded by cancellation, lease ownership and the
original deadline. Retained originals and publication fencing remain separate.
Added-line legacy/model-channel checks found no prohibited implementation.
The two changed customer messages have EN/DE catalogues and a recorded
draft/opposition/final copy review; planner build manifests were updated.

**Heuristic smells:** None material. The transport, acquisition journal and
release-selection boundaries have distinct responsibilities. Fowler smells
remain judgment calls, not additional mandatory architecture requirements.

**Evidence and limits:** Read retained engine results (743 passing tests,
149-file successful mypy), launch/provider boundary regressions and copy
evidence. No suite was rerun or test added. This review performs no native
installation, process/database change or production action, and does not
accept those separate runtime/browser delivery gates. No additional copies or
instances were created.
