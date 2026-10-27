# Standards review — PV settings

Initial report, immutable. Reviewed full cumulative diff
`git diff c7232e3d91e80d87887ca3d1d398f92852dec021...15f018d812556294901559e5956197f8e4bc74a8`.
Commits: `0e16d6d5298616d9eb757c4cbcd621b9d3407f04` and
`15f018d812556294901559e5956197f8e4bc74a8`.

**Verdict: changes requested — one documented-standard breach.**

- **[P3] Add the module form's numerical-source comment.**
  `apps/planner/src/components/energy/PvModuleParameters.tsx:45` introduces the
  25 °C reference and an illustrative −0.29 %/°C coefficient; lines 91, 105 and
  124–125 introduce URL/hash/page bounds. The file has no source/schema comment.
  Authoritative `/Users/chesterjohn/Documents/de-linker/AGENTS.md:78`, §4,
  requires “每个数字与阈值必须有来源注释” (every number and threshold needs a source
  comment). Add a comment citing the retained pvlib source for `temp_ref=25`,
  label the coefficient as an example rather than a supplied/default value,
  and cite `pv-generation.schema.json`'s `Text`, `Hash` and `PositiveInteger`
  definitions for the bounds. The adjacent array and converter controls already
  provide equivalent comments. This is a traceability breach; no wrong physical
  value was established.

**Heuristic smells:** none material identified. Fowler smells were considered
as judgment calls, with the accepted isolated-app and shared-domain decisions
taking precedence.

Reviewed against current AGENTS, worktree CONTEXT, README, accepted ADRs
0001/0002, issue-tracker guidance, domain-language/i18n rules, presentation rules,
exported schemas and retained primary model evidence. No
`CODING_STANDARDS.md`/`CONTRIBUTING.md` was found. No Spec or copy review was read.

Independent checks passed: strict planner TypeScript; source/build hashes and
lazy-module identity; 11 decimal/solar domain tests; 8 real React-control tests;
2 browser-to-ASGI/worker contract tests; i18n validity/coverage; shipped PO/MO
semantic equality and planner JSON binding. Added source contains no legacy
identifiers, inline layout, second CSS compiler or new model channel. Actual
commands and results are in `standards-tests.txt`.

This review establishes this local increment's checks, not installed native
runtime, source acquisition, engineering/country/equipment release or production
acceptance. It makes no whole-engine CI claim.
