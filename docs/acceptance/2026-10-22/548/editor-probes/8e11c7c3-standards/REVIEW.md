# Standards recheck — 8e11c7c3

Fixed source `8e11c7c3dfbcf658765b53b5f7fa4074e03ed560`. Full review diff `8a4a80b132f692062125807e509a57926fb0f518...8e11c7c3dfbcf658765b53b5f7fa4074e03ed560`; focused repair `b0080ec1...8e11c7c3`. Commits:37f2acd3,6c6680ad,b0080ec1,8e11c7c3.

**Standards PASS.** No new documented coding-standard violation or actionable heuristic smell found. Prior b008 Standards/copy PASS is retained. Fowler smells are judgements, not hard rules. Authoritative standards are AGENTS, CONTEXT, docs/agents/domain, current main local-storage discipline, accepted isolated-runtime ADR and interactive/workbench/geometry contracts. No additional CONTRIBUTING.md/CODING_STANDARDS.md exists in the fixed tree.

## Reviewed boundaries

- `plugins/linker-tools/includes/Planner/Application.php:60` reads the actual fixed Vite scene entry and accepts only an anchored `assets/SceneViewport-hash.js` path. It publishes public escaped data (`:83`), not project-supplied executable content. PHP remains a native mount/data adapter, with no design/style decision.
- `apps/planner/src/main.tsx` passes its own actual import.meta.url. `data/config.ts:32–46` checks asset origin/directory against that entry rather than the document base. Credentials, nonempty query/fragment, alternate filenames/directories, malformed/foreign schemes are refused. Native metadata supplies the exact file; no project/upload/user-entered URL participates.
- `data/sceneModule.ts:17–35` retains one pending/success promise, evicts only the matching rejection, keeps the first import literal/bundler-owned, and creates a fresh retry query from native metadata. Missing metadata cannot manufacture an executable URL. The cache is module-code state, not actor/project state.
- `LazySceneViewport.tsx:44–58` recreates the lazy boundary on explicit retry outside the failing chunk, retaining upstream raw property state. Changed plan z-order affects picking/visibility only; coordinates/counts and the geometry checker are unchanged.

## Independent execution

1. `npm test`:46 domain/data +52 React DOM PASS. This includes actual staged invalid raw2.5 preservation on lazy failure/retry and guarded config. `suite.log`.
2. `npm run build:check`:source/build hashes, WindPress scan and emitted queried-entry→dynamic-chunk graph PASS. `build-check.log`.
3. Fixed PHP `PlannerApplicationTest.php`:1 test/7 assertions PASS against the actual fixed manifest and scene/entry bytes. `standards-php-bootstrap.php` explicitly requires reviewed classes from the archive, avoiding Composer's linked parent application autoload. Vendor alone is linked. `php-native-metadata.log`.
4. `standards-native-metadata-probe.php`:10 actual Application cases with explicit narrow native-function stubs. Exact allowed scene is published; traversal, query/fragment, foreign URL, encoding, alternate extension/type and missing value produce null metadata. No React dependency is introduced. `native-metadata-probe.log`.
5. `tests/standards-config-probe.mjs`:14 additional executable-URL candidates refused, including hostile document base, credentials, encoded traversal, data/blob/javascript and malformed URLs. `config-probe.log`.
6. `tests/standards-scene-cache-probe.mjs`:actual source loader, module-boundary failure seam. First rejection clears pending; parallel initial/retry calls share identity; retry uses exact manifest file plus ?planner_retry=1; success remains the same Promise; null metadata rejects without evaluating a guessed file. `scene-cache-probe.log`.
7. `tests/standards-built-failure-retry-probe.mjs`:actual emitted graph with only initial unqueried Scene failure injected. Queried entry executes once, fresh Scene retry imports successfully and reuses its namespace. No fake Canvas/GPU. `built-failure-retry-probe.log`.
8. Prior byte-identical plan probe reused:12 PASS. Cancellations and changed-document-before-React-commit remain safe after constraint z-order change. Native SVG geometry/hit testing is not claimed. `plan-recheck.log`.

Reproduction, after restoring the fixed minimal tree and dependency links:

```
cd apps/planner
npm test
npm run build:check
node --loader ./tests/standards-scene-cache-loader.mjs --test tests/standards-scene-cache-probe.mjs
node --loader ./tests/standards-built-first-failure-loader.mjs --test tests/standards-built-failure-retry-probe.mjs
node --test tests/standards-config-probe.mjs
node --loader ./tests/tsx-loader.mjs --test tests/standards-plan-recheck.mjs
cd ../..
php plugins/linker-tools/vendor/bin/phpunit --configuration plugins/linker-tools/phpunit.xml.dist --bootstrap standards-php-bootstrap.php plugins/linker-tools/tests/php/Unit/PlannerApplicationTest.php
php standards-native-metadata-probe.php
```

## Diagnostic boundary

An exploratory test directly imported an **already successful** emitted Scene under two different retry queries. Three warned about multiple instances, while application-entry starts remained1. That test bypasses the production successful-module cache; it is retained as `standards-built-retry-probe.mjs` / `built-retry-probe.log`, not passed off as the supported retry flow. The source cache probe proves that successful imports are reused, and the actual-build first-failure→fresh-success probe had no such warning. This review does not claim arbitrary partially evaluated module/dependency failures or old-release missing assets are repaired.

## Copy and scope

No public source wording/PO/design-copy-final delta since b008. The prior259-message source/German catalogue consistency review remains applicable; private error codes are not customer promises. No added legacy identifiers were found in changed source. Current main AGENTS storage rules were read. This is fixed-source Standards/copy review, not native browser, GPU, touch, full B, A–D planner or production acceptance. Parent owns actual native results.

At completion all reconstructible fixed files are individually SHA-checked and reclaimed, with own dependency symlinks removed. Unique probes/logs/report/manifest survive; cleanup.json records actual counts and free space. No parent/native files are modified.

## Separate Spec-axis correction known at finalisation

After this Standards pass, the independent Spec reviewer reported P3: URL.search/hash are empty for naked ?, # and ?#, so these are accepted despite the strict separator-free contract. Parent accepted the correction. `standards-empty-delimiter-probe.mjs` independently confirms the fixed8e11 behaviour; `known-spec-p3.log` records all3. No arbitrary-code/native manifest bypass was shown; this is a contract mismatch, and Standards PASS must not be used as combined release approval. The future correction needs a narrow recheck. This note preserves the fixed8e11 results rather than pretending the correction is already present.
