# Reproduce this fixed Spec review

This bundle preserves unique probes, full logs and a SHA-pinned source manifest. No dependency tree or running site is retained. Owner: `/root/geographic_spec_e138`; original temporary snapshot expired when this review was archived and verified.

For another run, copy this small evidence bundle to a new explicitly owned temporary folder, then execute there:

```sh
python3 rebuild_snapshot.py
(cd apps/planner && npm test)
python3 run_refusal_probe.py
python3 run_relocated_probe.py
```

`rebuild_snapshot.py` uses `git show` for every fixed source entry, verifies its SHA256 and links the existing dependency directory recorded in `archive_manifest.json`; it refuses to overwrite changed files. The retained 54 driver verifies unchanged probe hashes before composing its executable module. The additional driver runs only the seven `relocated` cases and uses the same retained sources. Source paths and relative imports are preserved.

Expected: two client groups with 54/54 passes each; retained composed 54/54; relocated 7/7. After recording full output, SHA-check and reclaim all generated source/module files and the dependency link. Do not clean the authoritative source checkout or prior review archives. The original review already completed this reclamation, as recorded in `cleanup.json`.

Native EN/DE layout, browser pixels and physical touch are outside this Node/JSDOM reproduction.
