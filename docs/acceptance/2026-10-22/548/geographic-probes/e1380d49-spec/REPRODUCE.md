# Reproduction and retention

`archive_manifest.json` pins the fixed e138 source files and three a0 legacy source blobs, with exact Git blob SHA256s. It links the existing worktree's venv and Node dependencies; no dependency installation, new worktree or native instance was made.

Run `python3 rebuild_snapshot.py` in this directory. Then:

```sh
PYTHONPATH=services/engine/src services/engine/.venv/bin/python -m pytest -q --basetemp=./runtime-test-data test_independent_spec.py
node --test independent-browser.test.mjs
```

The independent pytest module executes the actual a0 GeographicBridge/GeometryImport/Options source blobs under isolated module aliases to create the old receipt. The HTTP app under examination remains fixed e138. The failing-conversion injection proves replay does not execute a fresh conversion; it is not an installed PROJ-version migration test.

The target suite commands and exact completed outputs are in `target-check-runs.json` and its named logs. Those target tests were run once; outputs were retained from their completed tool results, not fabricated by a second invocation. Independent probes capture their subprocess logs directly and record run commands/status/hash separately. `probe_environment.json` records actual fixed-source import paths and installed numerical library versions.

At completion, fixed source/test/fixture files and dependency links are removed after SHA checks. Unique probes, logs, reports and reconstruction manifests remain. No parent source, production/native state, user prototype, credentials or runtime services were edited. The resource owner/expiry/reclaim conditions are in `archive_manifest.json`; `cleanup.json` records actual reclamation.
