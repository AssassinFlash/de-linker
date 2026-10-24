# Standards closure: saved solar settings

Source: `471755229cf369f4a82711bd7b9f12d05e161154`.
Accepted base: `367640fcf09eba92eb77b8e61aaedaa6957cdd7b`.
Reviewed the complete cumulative diff across five commits, including every delta after `cf951e3d`, under current main-repository `AGENTS.md`, owned `CONTEXT.md`, the accepted isolated-runtime ADR and package configurations. No nearer contributing/coding-standard file exists. The Spec axis was not read.

**Findings: zero remaining documented-standard violations; zero material Fowler-baseline smell findings. The initial P3 is closed.** `WeatherForm.tsx:9–13` now names the exported coordinate/year definitions, distinguishes protocol bounds from provider coverage and cites retained primary-source evidence for the hourly non-leap interpretation. This satisfies main AGENTS.md §4's numeric-source-comment requirement. The original report is preserved byte-identically as `standards-initial.md`.

The new test-helper changes add a concrete return type and typed collections without changing assertions or request data. The development-only browser entry now unmounts its former React root on HMR disposal. It does not enter the production module graph. No new secret/model/private-control authority or legacy-code carry was found; native gateway/identity PHP remains unchanged.

Independent final checks in `standards-tests.txt`: the exact uncached strict mypy command passes 159 files without silent imports; 22 affected-helper and actual TS→ASGI save-contract tests pass. All 158 source and seven build hashes match frozen blobs. Production JS, Vite metadata, scan output, CSS and PO/MO/planner JSON are byte-identical to the previously verified pin. The prior independent checks for 99 actual source/compiled/native-i18n translations and placeholders, four exported schemas, five generated modules and 55 imports therefore remain valid. Cumulative added-line legacy scanning has no hits.

The broader mypy run remains non-green: recorded evidence reports 199 errors in 16 other test files. Independently comparing all 16 files and recorded hashes confirms they are byte-identical to the accepted base. This debt remains unwaived and is not presented as a passing whole-engine gate.

Only Standards artifacts were written. Temporary test storage was removed; no running instance, backup or worktree was created. This accepts the increment's source Standards axis only. Native installation, live acquisition, site/commerce behavior, deployment and the full #548 goal remain unaccepted here.
