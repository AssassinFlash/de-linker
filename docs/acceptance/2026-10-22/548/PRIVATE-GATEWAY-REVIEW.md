# Private planning RPC: component acceptance

Date: 2026-10-23. Final reviewed implementation:
`bc68b112cc7d1cb2a12ac8e539fb012dc2938b46`.
Initial component base: `08c8e6db5e4efafb13763bfa37289499aac72268`.
Contract: `docs/specs/548-private-gateway.md`.

## Standards

Independent fixed archives passed. The reviewer found no documented-standard
violations or actionable baseline smells. Final incremental HTTP tests: 44.
Independent original ASGI cases covered methods, duplicate/case-varied headers,
invalid subjects, configuration absence, body framing/limits/disconnects, scope
replacement and unconditional private cache headers. Unexpected exceptions
before a response return one private error; partial responses fail as streams
without a second response-start.

The reviewer separately checked every valid Unicode scalar in batches against
the preceding canonical encoding: bytes/hashes were identical. Lone surrogate
values/keys and corrupt persisted forms were rejected. Schema/path diagnostics
are bounded transport policy, not physical tolerances.

## Spec

The independent reviewer found and the implementation closed three classes of
counterexample in this same batch: inconsistent framework/error envelopes;
small recursive requests generating excessive validation output, including
UTF-16/32 auto-detection bypass; and credential-source errors outside FastAPI's
own exception boundary. The final fixed archive passed all counterexamples,
legitimate Unicode/NUL-escape/BOM reads, 168 chunk/depth combinations and 44
HTTP tests. No spec gaps or scope creep remained for this component.

Actual HTTP upload/revise/enqueue/Worker/read/history/trace paths retained
ownership and frozen bytes. The synthetic two-hour physical fixture produced
3.62 kWh solar supply and approximately 0.38 kWh grid supply; this is not a
site measurement or equipment release.

## Boundary

This is private server-to-server RPC with explicit deployment limits. It is
not publicly mounted and has no browser CORS or authentication-off mode.
Native WordPress session/nonce/Origin verification, admission, login outbox,
browser integration, review-site and production readback remain part of the
same active delivery. A typed Actor/header behind the service credential is
not evidence that those native browser paths are complete.
