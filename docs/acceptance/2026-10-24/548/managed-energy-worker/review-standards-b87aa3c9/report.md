# Independent Standards addendum

Reviewed source pin: `b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3`.
Prior reviewed pin: `99de9d6e5bcdb9417edbbfadbb694342e5a2234f`.
Command: `git diff 99de9d6e5bcdb9417edbbfadbb694342e5a2234f...b87aa3c9b39c0955f381c6847e9c5137f0c2b8f3`.
Commit: `b87aa3c9`. All hunks across three files (17 added lines) were read. This supplements the prior 26-file full review.

**Documented-standard violations: none remaining in this delta.**

The native reload found a consumer regression at the prior pin: private worker fields reached a browser contract that rejects additional properties. The correction belongs at the existing PHP data-assembly boundary. `Planner/Gateway.php:202–205` explicitly projects the four browser runtime keys and four limit keys after validation and effective-limit clamping. These lists agree with the existing strict session schema (`apps/planner/src/data/readProtocol.ts:60–73`) and declared interface (`protocol.ts:25–34`). Worker execution/storage fields remain available on the private protocol without entering bootstrap.

This follows canonical `AGENTS.md:88` (PHP data assembly rather than presentation), `CONTEXT.md:52–53` (rulebook authority), and the clarified managed-worker contract (`docs/specs/548-managed-energy-worker.md:56–59`). It changes no customer wording, visual composition, physics, resource values or model routing.

The native test (`tools/local/tests/integration/test_planner_native.py:203–209`) exercises the owned WordPress bootstrap and asserts its exact runtime/limit key sets. It checks the consumer boundary that failed; the surrounding fixture requires an explicitly named snapshot-backed local instance. The enclosing task owns the reported red/green execution evidence; I did not rerun it.

**Fowler heuristic judgments: no actionable smells found.** The small inline projections stay with their sole boundary consumer. Matching wire-key declarations across PHP, TypeScript and the integration assertion are contract evidence, not sufficient reason for a new cross-language abstraction.

No added legacy implementation identifiers or TODO/FIXME markers were found. Only this report was written; no source, configuration, database, managed process, dependency or git mutation was performed. Source pin was read back. Full-goal UI/production acceptance remains open. **Standards findings: 0; worst issue: none.**
