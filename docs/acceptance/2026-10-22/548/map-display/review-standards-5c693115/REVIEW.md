# Standards: PASS for the fixed full diff

Reviewed `git diff be5711bf429c86dc5118e55227c0a48bb78d26b1...5c693115d345a676d7a737bdfb886597b74fbe80`: four commits, 156 changed files. This carries forward the exhaustive `81cd1c5b` source/tests/dependencies/builds/languages/native-PHP/local-CSP review and independently checks the correction and added evidence. No Spec verdict was used.

**Hard documented breaches: none open. Previous P2 closed.** `README.md:60` requires canonical lock URLs. All 189 planner `resolved` URLs now use `registry.npmjs.org`, including all 28 entries cited previously at `apps/planner/package-lock.json:186` onwards. Parsed lock data differs only in those URLs; every other field, version and integrity remains identical. `apps/planner/.npmrc:2` supplies package-local `replace-registry-host=always`; `apps/planner/bin/build-manifest.mjs:30` includes it. The README describes the actual isolated package layout without waiving the registry rule.

**Fowler baseline judgment calls: none justified.** No implementation hunk changed after the prior audit. The shared lazy boundary/retry extraction removes duplication; converter, request owner and native manifest retain distinct responsibilities. The small configuration/manifest correction adds no necessary corrective smell.

Independent Git-object probes establish that all 97 runtime sources, all 116 tracked `src` files including tests, and seven emitted artifacts are byte-identical to the prior pin. All 103 source and seven build hashes match. The prior scoped, full-licence vendor CSS, WindPress pipeline, reviewed gettext, native PHP, transient provider-grant and legacy-absence findings therefore remain applicable.

Stored official npm JSON independently matches the three locked versions, integrities, canonical tarballs and recorded SHA values; per-response metadata reports HTTP200. Apify's terminal status message also reports three failed crawl requests, retained explicitly rather than treated as an error-free crawl.

Five retained native JSON/PNG pairs agree with EN/DE desktop/phone identity framing and the fixed entry SHA; workspace, keyboard and same-project revision-3 records are consistent. This is evidence inspection, not a new browser execution or complete map acceptance. Existing suites were not repeated; corrective build/check/format logs were inspected. No source copy, checkout, dependency install, stack or network was created. No engineering, country, provider/legal, production or whole-goal acceptance is claimed.
