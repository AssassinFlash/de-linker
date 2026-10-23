# Reproduce the corrected fixed source review

Target `eff8341d5a0eaf24999f42854da6339032c65c9c`; full increment base
`367e454c23f542632258e1440387c4c9e7825e17`. The old 3225 FAIL is preserved.
The original temporary source/build snapshot has been reclaimed.

Copy this small evidence bundle to a newly owned evidence folder before another
run. Choose an absent absolute temporary path with a recorded owner, expiry and
cleanup condition, then run from that copied bundle:

```sh
review_snapshot=/absolute/owned/temporary/eff-import-review
python3 rebuild_snapshot.py "$review_snapshot"
python3 run_followups.py "$review_snapshot"
```

The rebuild script uses `git show` and checks every fixed SHA. It restores only
145 app/build/fixture/spec/catalog files, links existing dependencies and copies
the two retained 3225 probes directly from their verified authoritative archive.
The follow-up runner verifies those same probe hashes, composes the original
main harness with the unique suffix, and derives the real revision-parser case.
Expected follow-up counts: 20/20 plus 1/1, with no failures.

Execute the retained probes byte-for-byte unchanged and the locked checks:

```sh
cd "$review_snapshot/apps/planner"
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/independent-roof-import.mjs
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/independent-revision-refusal.mjs
npm test
npm run lint:types
npm run build:check
```

Expected: retained main 20/20 and revision 1/1; locked 62 domain/data + 87 DOM;
TypeScript pass; emitted/source-manifest check and emitted graph 1/1 pass.
The four previously failing leaf variants must all pass unchanged.

Transport replies and original geometry fixtures are synthetic. The client,
components, Query and both IndexedDB stores execute their real implementations.
German DOM tests feed the fixed WordPress JSON catalog into the fixture's i18n
adapter; they do not establish native WordPress language, OS-picker rendering or
viewport behavior. Native camera framing and full A–D acceptance remain separate.

After capturing unique full logs, SHA-check/reclaim every listed fixed file,
generated probe copy, reconstruction manifest and dependency link. Preserve
changed files and unique evidence. Do not remove the shared dependency target,
old FAIL archive or implementation checkout. No new worktree, site, runtime or
dependency installation is needed.
