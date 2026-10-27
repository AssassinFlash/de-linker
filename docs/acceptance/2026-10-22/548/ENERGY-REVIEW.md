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

Both axes independently rechecked `bd407575`: the original counterexamples
were rejected; the ULP residual was retained and its externally supplied
equivalent still rejected. Standards passed. Spec found one additional P2:
balanced traces could violate the declared fixed allocation order. With zero
battery, 2 kW PV and 1 kW load, a forged trace imported 1 kW and curtailed 2 kW
instead of using direct PV, yet passed. Its solar autarky changed from 100% to
0%. This is model semantics, not an invitation to test arbitrary EMS policies.

Independent equations now reconstruct the fixed priorities at actual delivery,
whose bounds remain independently verified by energy/source/capacity/reserve/
power/command equations. They do not call the
actuator, source withdrawal or its grid-limit helper. Four regressions first
failed against the previous verifier (all forged traces passed), then passed
after repair: direct PV, battery load-before-aux, PV-before-grid charging, and
export-before-curtailment. Standards found a short-interval numerical regression
in the first repair: reconstructing an energy-limited power from large total
inventory subtraction amplified a 1.14e-13 kWh arithmetic difference over 1 ms.
The allocation checker now uses the already independently constrained actual
delivery instead of duplicating the actuator's energy-to-power truncation.
The original simple 1000 kWh / 1 ms / 1 kW internal auxiliary case is retained
as a regression; no minimum interval, hidden tolerance or engineering margin
was added. Planning now has 91 passes, strict mypy/ruff/format passes.
Standards then found a second short-interval issue on `8f253d9b`: over 1 µs,
10 kW is only 2.78e-9 kWh, so a forged empty-battery supply could fit inside
the original absolute energy tolerance. Power/source availability checks now
retain that meaning independently, including a forged internal withdrawal,
future-inventory creation and actual internal auxiliary shortage. Their local
roundoff budgets derive from ULPs of the paired-withdrawal/transition operands;
each check exposes its arithmetic allowance separately. The 1 ms / 1000 kWh
valid case remains. Four additional cases bring planning to 95 passing tests.
Both axes then challenged the remaining energy-only semantics: source mixing,
between-interval continuity, full-battery charging headroom and signed auxiliary
shortage. Each had a 1 µs counterexample. The full verifier now preserves power
meaning in those source/account/headroom checks and exact state inheritance.
Its initial inventory is also supplied separately from the trace and compared
exactly. Six additional cases bring planning to 101 passing tests. The initial
whole-engine regression after 8f253d9b had 248 passes in 13.71s; it will be
repeated after these additional fixes.
The next independent sweep found real (unforged) reserve and cyclic-task
deficits could also be swallowed by the absolute energy budget. Capacity,
reserve and terminal hard boundaries now accept only accumulated, exposed
local arithmetic roundoff. The verifier independently enforces the strict
initial physical window too. Three additional regressions cover these cases;
planning reached 104 tests. Spec then demonstrated why accumulating theoretical
stock ULP bounds was still incorrect: 8760 exact idle frames could change the
same tiny real cycle deficit from failed to passed. The hard-boundary path now
uses an exact rational net-flow witness. Actual tracked deviation is exposed;
no idle or exact-cycle prefix earns a stock-error budget. A separate conserved
terminal comparison has a final representation ULP independent of padding.
Both idle-prefix and exact-cycle-prefix regressions preserve the same deficit
and reject it; planning has 106 tests. No smaller task horizon or physical
margin was introduced. The next fixed review showed two remaining causes:
source-bucket rounding could falsely reject equal-AC noninteger cycles, and
tracked deviation could include real sub-ULP auxiliary consumption or tolerated
stock creation. The witness now independently reconstructs bounded command
power and integrates exact time/efficiency ratios. It does not consume the
rounded source-withdrawal buckets, and its hard limits never borrow tracked
deviation. Source transitions accept only local arithmetic roundoff (zero-flow
assignment is exact). Four regressions cover 1.3 kW/54-step and .9 kW/2000-step
lossless cycles, sub-ULP auxiliary consumption at reserve, and creating stock
under a generic power tolerance for a later outage. The fixed energy/component
planning suite is 110 tests; the concurrently developed real CSV/worker adapter
adds 11 more, 121 passing together before its separate review.
## Final independent recheck

Both axes passed fixed `3c533482efbfb59c02025d7b3c48cf3d83caa0f1`.
Standards independently ran the fixed 110-test planning suite from a temporary
git archive; 20 analytic cycle groups/4000 frames and 9870 empty/full/exact-reserve
traces also passed. Spec independently checked 22 targeted challenge groups,
the microsecond-to-noninteger cycle cases and the 8760-step asymmetric-efficiency
cycle (5 kWh final inventory; 27375 grid, 19710 load, 5475 charge loss, 2190
discharge loss, all kWh). Padding did not change the real terminal deficit or
its final allowance. Neither axis found a remaining blocker or scope expansion.

These results validate this declared numerical component and its independent
checks, not all possible physical systems or all float64 inputs. The full
physical configuration/Genie/Woo/UI integration and live acceptance remain
active, not delivered by this component review.
