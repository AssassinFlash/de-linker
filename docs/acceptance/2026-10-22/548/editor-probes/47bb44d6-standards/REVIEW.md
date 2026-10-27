# Standards incremental recheck — 47bb44d6

Fixed target `47bb44d6ca2ff664d0bf638e394ab6fa842ac2fd`. Corrective diff `8e11c7c3dfbcf658765b53b5f7fa4074e03ed560...47bb44d6ca2ff664d0bf638e394ab6fa842ac2fd`; full base remains `8a4a80b132f692062125807e509a57926fb0f518`.

**Standards PASS.** No new documented coding-standard breach or actionable judgement smell. Retain prior8e11 Standards and copy passing scope. The separate Spec P3 is independently confirmed closed here: naked ?, # and ?# are now rejected. No public wording/PO/terminal-copy change.

At fixed `apps/planner/src/data/config.ts:39–40`, the resolved URL must equal origin+pathname; this catches even empty query/fragment delimiters that URL.search/hash hide. Existing origin/directory, credentials and anchored scene-filename constraints remain intact. This is a narrow canonical executable-asset boundary, not a new project/user-supplied code source. No new abstraction or duplicated dispatch was introduced.

## Independent checks

- Official config test, actual React lazy-failure/raw2.5-preservation test, and unchanged14-candidate hostile base/credential/encoded traversal URL probe:3 PASS. `targeted.log`.
- `standards-empty-delimiter-probe.mjs` was copied unchanged from8e11; an adapted separate `standards-empty-delimiter-recheck.mjs` asserts the desired rejection. All3 now accepted=false. `empty-delimiter-recheck.log`.
- `npm run build:check`: actual current source/build hashes match, and emitted WordPress-style queried entry→lazy shared-core graph passes. `build-check.log`.
- Unchanged `standards-scene-cache-probe.mjs` with its explicit import-failure boundary seam:pending is evicted on rejection, retry uses the exact new manifest SceneViewport-uF-OdQNM.js?planner_retry=1, in-flight and success Promise identities are retained; missing metadata invents no executable URL.1 PASS. `cache-probe.log`.
- Unchanged `standards-built-failure-retry-probe.mjs`:actual emitted modules, only original Scene import failure injected. Fresh retry succeeds, the queried entry executes once, repeated same retry import returns the same namespace.1 PASS. `built-failure-retry-probe.log`.

Reproduction after restoring the manifest's fixed minimum and linking the installed node_modules:

```
cd apps/planner
node --loader ./tests/tsx-loader.mjs --test tests/config.test.mjs tests/design-lazy-failure.test.mjs tests/standards-config-probe.mjs
node tests/standards-empty-delimiter-recheck.mjs
npm run build:check
node --loader ./tests/standards-scene-cache-loader.mjs --test tests/standards-scene-cache-probe.mjs
node --loader ./tests/standards-built-first-failure-loader.mjs --test tests/standards-built-failure-retry-probe.mjs
```

Standards and complete smell baseline remain the same as prior review; project rules override heuristics, formatting/type gates are not duplicated. The current storage rule was followed using one minimal fixed reconstruction and one dependency link; tracked copies are SHA-verified then reclaimed. Previous unique probes/results remain intact. No parent/native/production edits or package installation occurred. No synthetic host result is claimed as GPU/native/browser evidence. This does not close full B or the complete planner goal.
