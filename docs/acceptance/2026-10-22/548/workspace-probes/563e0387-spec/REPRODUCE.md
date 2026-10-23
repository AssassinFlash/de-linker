# Fixed review reproduction

Run `python3 rebuild_snapshot.py` in this directory. It reconstructs only 121 SHA-pinned application/spec/fixture files through Git and links the existing worktree's Node dependencies. No install or new native instance is required.

Then run:

```sh
cd apps/planner
npm test
node --no-warnings=ExperimentalWarning --loader ./tests/tsx-loader.mjs --test tests/independent-journal-probe.mjs
```

The target client suite should pass 54 domain/data and54 DOM tests at563e0387. The independent probe deliberately exits 1: 18 cases pass, and its final Site workspace destination counterexample fails. A successful reproduction of the red case does not mean the product passes.

The independent tests render the actual fixed ProjectEditor, BriefForm, ProjectOverview, DesignEditor and PlanViewport with real React/Query in JSDOM. Private transport and browser storage are explicit in-memory fixtures; no geometry calculation response is fabricated. The multi-roof geometry and 50,667 kWh annual input are declared synthetic test props, not a real project calculation. JSDOM cannot establish pixel layout or physical scroll position; the focused destination and section order are directly asserted. No Computer Use, native WordPress or another chat's SDK fixture is operated here.

All commands/statuses and full captured logs are retained. An initial probe assumption used valid `1,` under de-DE; its failure and the correction to invalid `1,,` are documented separately. The final source still has the intended single product failure.

After completion, fixed files are removed only when their SHA matches `archive_manifest.json`; generated files and the exact dependency link are reclaimed. Unique probes/logs/reconstruction manifests remain, with actual cleanup recorded in `cleanup.json`.
