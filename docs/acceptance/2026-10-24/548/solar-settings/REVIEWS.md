# Independent reviews of the saved-source increment

Accepted base `367640fcf09eba92eb77b8e61aaedaa6957cdd7b`; final source
`471755229cf369f4a82711bd7b9f12d05e161154`.

## Spec

`spec-initial.md` freezes the first review at `235b9178`: one P1. Its actual
TypeScript-to-Python counterexample demonstrated that preparation retained a
weather selection bound to a different request, blocking native Save.

`spec-closure.md` independently verifies the `cf951e3d` fix against actual
backend validation and the new real ASGI regression. The source/history remains
retained, replacement Save succeeds and inconsistent reattachment is still
rejected. No backend binding rule was weakened.

`spec-final.md` covers the complete base-to-final diff at `47175522`: **zero
open findings**. The prior `49579c19` conclusion is retained separately. Final
comment/test-typing/development-entry changes preserve the accepted behavior.

## Standards

`standards-initial.md` preserves the frozen `cf951e3d` review: one P3, missing
source comments for coordinate/year bounds. `standards-final.md` closes it at
`47175522` and covers the full cumulative diff: **zero remaining documented
violations and zero material Fowler-baseline findings**.

Independent checks include actual schema parity, all 99 reviewed EN/DE strings,
PO/MO/planner/native-i18n output, source/build hashes, affected helper tests and
the TypeScript-to-ASGI contract. The initially failing default type check is
retained in `standards-tests.txt`; the three imported-helper annotations were
fixed and the exact uncached default check now passes 159 files without silent
imports. All 16 remaining whole-engine type-error files were independently
verified against the accepted base. Their 199 errors remain unwaived.

## Copy and scope

`copy-review.md` and `copy-final.json` retain draft, opposition and approved
English/formal German, including the consequence of explicit weather
replacement. The final inventory has 99 entries. `native-i18n.json` verifies the
actual native translation library and positional bound placeholders.

Reviews are independent and their findings remain separate. The available
agent capacity required serial execution of the two axes; neither reviewer read
the other's report. All reports are pinned and preserve initial failures.

These conclusions accept this scoped increment. Native paired installation,
live acquisition, complete PV model controls, engineering/country qualification,
all product deliverables/consumers and full-goal publication remain separate
required gates; no goal was completed or reduced here.
