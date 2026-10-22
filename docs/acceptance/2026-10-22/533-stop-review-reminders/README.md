# Stop automatic review reminders — local evidence

Owner instruction: recurring saved-inquiry review reminders must consume no mail allowance. This narrow hotfix starts from the deployed source `3c3c3c25fff1d6b6f1aed8a990a410cfd9149577` on branch `codex/533-stop-review-reminders`; it does not include the separate global-intake work.

## Implemented boundary

The compatible `ReviewReminder` callback produces nothing. The existing recovery hook remains registered. At the start of the common Outbox attempt, the exact `REVIEW_REMINDER` category is retained without selecting a transport or reserving capacity. Existing jobs receive a native hold, pending Action Scheduler actions are cancelled from a finite snapshot, and both writes are read back. A failed hold or cancellation stays before transport and emits a fixed diagnostic. Message content, category, attempts, error, audit and historical allowance entries remain intact. Normal standard and critical messages use the existing path.

## Actual local checks

The exclusive `s533rem` instance is a bare native WordPress/WooCommerce fixture, not a visual demonstration. All delivery was loopback SMTP or local PHP capture under the existing local guards; no real mailbox was used.

- Red against deployed source: new narrow tests ran 7 tests / 14 assertions, with 4 failures. The producer read the summary and queued reminders reached transport, including the two injected persistence failures.
- During the first repair run, a cancellation-write fault exposed the native cancel-until-empty helper looping. Only this test process was stopped and the owned instance reset. The final code snapshots pending IDs, cancels each once, and verifies the result; the same fault now completes without transport.
- Final native scope: `ReviewReminderTest`, `InternalSmtpTest`, `MailRetryTest`, `NotificationHoldTest` — **36 tests / 334 assertions, PASS**. This includes zero producer jobs, the actual recovery heartbeat, complete queued-message preservation, failed hold/cancellation, typed nonqueued attempts, and real standard/critical positive controls.
- Independent Spec review of `4e7a55f0` found that AS returns an empty list after a failed SELECT. Separate snapshot/readback fault cases first failed (2 tests / 8 assertions); the repaired native run above proves both faults really hit, record the correct fixed failure phase, retain full message/attempt/error/history, and use no transport or allowance. Woo log-handler duplicates are normalized when asserting the diagnostic text.
- Mail unit scope: **43 tests / 164 assertions, PASS**.
- Complete Commerce PHPStan: **PASS**.
- WPCS on the four changed PHP files and `git diff --check`: **PASS**.

Private raw logs are retained by the coordinator under `incident-20261022/533-stop-review-reminders/`. Inbox observations remain private and are not reproduced in this repository.

## Remaining release gates

Independent full-diff Spec and Standards reviews plus the repair delta, final exact-head CI, production backup and guarded handling of existing jobs, deployment, and loaded-source/budget/inbox readback belong to the coordinator. These local results do not claim deployment or physical inbox verification. No customer UI, CSS, translation or new customer copy changed; no new browser acceptance is claimed.

The initial `4e7a55f0` CI run is historical evidence only; the later AS read-error repair needs its own exact-head CI result. No final CI success is claimed here.
