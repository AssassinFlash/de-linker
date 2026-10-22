# Time/measurement increment: independent review

2026-10-23. Initial fixed diff `7591075a...2aae2ab8`.
Both reviewers read only the fixed time increment, not uncommitted dispatch.

## Standards

Two P2 typed-error omissions were reproduced: a valid TZif magic followed by
truncated bytes leaked `struct.error`; ISO offsets that normalize outside
Python's UTC date/time domain leaked `OverflowError`. They should instead be
`VersionUnavailable` and `InvalidInput` respectively.

One non-blocking judgement was also adopted: string-only transformation names
lost the intermediate coarsening history. Original 15-minute data averaged to
an hour and refined back to 15 minutes retained raw native resolution while
losing measured peaks. This is not restored measurement precision.

The fixes normalize these errors and retain input-document/target-axis hashes,
input/output interval durations, exact-copy status, effective coarsest interval
and whether any reconstruction occurred. New regressions cover both UTC
boundaries, truncated TZif, and coarse→fine peak loss. Reconfirmation is pending
on the repaired fixed commit.

## Spec

Initial Spec review passed with no separate missing requirement, scope creep or
confirmed wrong implementation. The reviewer independently ran all 23 initial
time tests; 300 irregular microsecond grids passed a separate Fraction overlap
oracle. It also verified same-clock autumn start/end folds, spring's apparent
two-hour wall-clock span as one real hour, offset/fold conflicts, and replay
from captured TZif after OS file reads were disabled.

This initial pass does not overrule the Standards error-boundary findings.
The time contract has been sharpened to require intermediate precision history;
the repaired increment will be independently rechecked.

Initial totals: Standards 2 P2 plus 1 adopted judgement; Spec 0. These are time
input results, not full annual PV/storage, equipment or production acceptance.
