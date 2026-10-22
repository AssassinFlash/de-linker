# Native mail combination regression repairs (#568)

This increment starts from combined source `2d632574fb655d80ce4031abe7912e443254a201`.
It is confined to the Mail boundary and native mail/admin fixtures. Registration
implementation, model routes, browser presentation and production are unchanged.
The exclusive snapshot-backed `b568` instance was backed up before `just up`
rebound its project plugins to this separate worktree; external HTTP and mail
remain blocked/captured by its native local isolation.

Exact #568 workflow `39824577222` passed its general check and failed the native
assessment/customer-evidence/staff-review group: six NotificationHold cases still
found a scheduled action where the preserved incident contract requires none.
A separate combined run also found two AccountsAdmin mail-fixture failures.
A local minimal 13-case run reproduced all eight failures before changes.

## Actual final-writer and caller-transaction failures

Two new real-native invariants were red before the repair:

1. JobStore creates an original job bound to an inquiry whose native source is
   already held. Its automatic recovery arming must not create a future delivery
   action. The job remains durable and charged in its original pool.
2. Retry receives an existing held job while its caller owns an open native
   transaction. It must not schedule recovery or touch transport/budget before
   checking that hold; the caller must still own the transaction.

Both previously created an AS action. NativeJobCapacity now consults the actual
native job/source hold after its original write/ACK and before recovery arming.
Outbox retry checks a definite hold before its caller-transaction scheduling
branch; the existing later fresh check remains for the independent lock phase.
The lookup is explicitly marked impure for static analysis because it refreshes
native database state; an earlier false read cannot prove a later read false.

The tests retain zero attempts, unchanged original body, unchanged mail budget,
no pending AS and caller transaction ownership. They additionally assert that
retained held jobs still occupy ordinary count/bytes. No capacity is refunded,
no old job is recaptured, and unknown outcomes are not compensated.

## Existing native fixture assumptions

The incident fixture previously created a job and then attached the hold markers.
The new JobStore correctly arms ordinary *new* jobs, while the historical incident
operation had explicitly cancelled pending actions before retaining those jobs.
The fixture now reproduces that historical cancellation using the native AS API,
then keeps every original no-action/zero-budget assertion. This correction is
separate from the two real writer invariants above and cannot hide them.

AccountsAdmin's two-notification test previously called the VAT email with past
status arguments but no actual current-version native source. It now persists
the native verdict/version, invokes the real email consumer, and verifies its
exact same-version ACK and pending=no before checking both original queue rows,
recipients, Bcc, account links and EN/DE subjects. No fake send-success is injected.
The digest language fixture explicitly chooses and restores the team language
for its EN/DE assertions, independently of the loaded snapshot's Chinese team
preference. Production language policy is unchanged.

## Verification and limits

- Initial minimal reproduction: 13 tests / 121 assertions, eight failures.
- Two added final-writer/outer-transaction invariants: 2 tests, both red.
- Repaired minimal consumer run: 15 tests / 229 assertions, pass; subsequent
  expanded run also includes the extra held-occupancy assertions.
- Expanded owned native combination: **269 tests / 3,691 assertions, pass**.
  This includes the previous 233-case scope, every NotificationHold case, every
  AccountsAdmin case, CustomerReview and all seven VAT notification cases.
- Commerce unit: **1,718 tests / 6,364 assertions**, pass, with 418 native cases
  skipped by the unit bootstrap. The 269 native cases above ran separately.
- Whole Commerce PHPStan and five changed PHP files' WPCS pass; whitespace and
  added retired-identifier checks pass.

The original local 38 held jobs remain at attempt zero. Their complete native
metadata/status digest stays `e680902e6fd5f1521512c3486cdae059be3363834937f062def5a5b31ad4a815`;
their scheduled pending/running action counts remain zero; the complete 39-job
digest stays
`33d7c7ac0bb3d5013a032892a1fd7254024dc699f72167450e755039cdb9b528`.
The unrelated unheld original job 11830 is preserved. These are local-baseline
readbacks, not a claim about current production history or a different snapshot.

Private logs, exact local backup and sanitized readbacks are under
`/Users/chesterjohn/de-linker-data/incident-20261022/mail-combo-568/` (0700/0600).
Registration-specific combined-suite failures belong to the separate registration
worker. Its later prefix/VAT fixture difference is not declared solved by this
scope's passing run. The coordinator still owns full-diff review, exact combined
CI, production backup/migration/readback and authorized actual customer/inbox
acceptance. No new UI or customer copy is introduced in this increment.
