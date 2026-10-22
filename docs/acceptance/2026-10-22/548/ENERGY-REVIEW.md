# Continuous energy replay: independent review and repairs

2026-10-23. Initial fixed diff `0d5ff890...a556b03e`.
Reviewers loaded only the fixed commit, separate from later working edits.

## Standards

Three blocking findings were independently reproduced:

1. P1: the verifier trusted reported zero command-shortfall fields without
   checking actual delivery against its command. Replacing a valid 1 kW
   discharge command with zero still passed the independent verifier.
2. P1: negative internal auxiliary shortage could cancel excess internal
   consumption while total/source equations still closed. Actual supply and
   shortage needed independent nonnegative/demand-bound checks.
3. P2: full charging of 1 kWh at .95 efficiency over 45 minutes from 0.1 kWh
   unknown inventory produced 1.0000000000000002 kWh; the following step's
   strict capacity comparison rejected its own valid floating-point result.

The reviewer ran all 24 initial energy tests and reproduced the missing cases.
No additional blocking code smell was reported. Independent repetition of
equations is required here; the verifier must not call the actuator to verify it.

## Spec

Two verifier defects were independently reproduced, both P2 in this axis:
actual/command/shortfall consistency was missing, and negative internal shortage
could hide extra consumption. They violated command delivery and nonnegative
flows/explicit auxiliary demand. No scope creep was found. Within the stated
single-AC-bus domain the actual actuator's conversion, loss ordering, continuous
source inventories and solar metrics matched the numerical contract; the
reported verifier defects did not originate in that actuator.

## Repairs and current evidence

Command accounting and not-above-command checks now recompute consistency.
Internal auxiliary shortage is explicitly nonnegative; actual internal supply
is independently checked against demand and available inventory. The numerical
tolerance is an explicit input shared by replay and verification. Initial
over-capacity remains invalid, while intermediate arithmetic residuals remain
in their source inventories and are recorded, not hidden by a post-state clamp.

The implementation also preserves each frame's gross/critical load identity.
Critical/mixed demand gives its scoped solar-load share; whole-site autarky and
gross load are undefined with a scope reason. This closes an output-meaning gap
before a frontend can accidentally label critical-circuit results as site-wide.

The four new regressions cover both original verifier tamper cases, full-charge
continuity with retained residuals, and mixed-demand metric semantics. The full
planning set is 86 passing tests with strict mypy/ruff/format checks. The initial
whole-engine regression run had 239 passes in 13.62s; it will be repeated after
these fixes. A separate synthetic 8760-interval analytic fixture passes; neither
its speed nor its energy totals are a production weather/SKU acceptance claim.

Both axes will recheck the repaired fixed commit. Initial totals: Standards 3
(worst P1 verifier), Spec 2 (worst P2 verifier; two shared causes). Overall goal,
complete physical configuration/Genie/Woo/UI integration and live acceptance
remain active, not delivered by this component review.
