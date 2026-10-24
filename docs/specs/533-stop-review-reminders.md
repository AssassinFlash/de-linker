# Stop automatic review reminder mail

Owner ruling, 2026-10-23: repeated saved-inquiry review reminders must not consume
mail allowance. The default is permanently disabled, with no settings switch.
This supersedes only the automatic ReviewReminder producer behavior in the
mail-capacity specification; ordinary business notifications and recovery remain.

The owner observed the same aggregate reminder arriving hourly with no new
individual notification. Its body contained only count, age, timestamp and the
staff URL. That observation does not show a held individual notification was
released. Inbox/source evidence stays private with the coordinator.

## Required behavior

- ReviewReminder::tick creates no job/action and performs no summary, reminder
  history or mail-budget read/write. Keep the callable construction and historical
  OPTION/ceiling constants for compatibility/audit, without producing messages.
- Keep the shared RecoverySchedule hook and its actual inquiry heartbeat/recovery.
- Before Outbox selects/reserves SMTP or PHP capacity, the exact trusted
  Message::REVIEW_REMINDER category returns without transport. No subject/body
  heuristic or category rewrite. Include queued and typed nonqueued invocations.
- For an existing job, persist native NotificationHold reason
  review_reminders_disabled and timestamp, preserving an already existing hold.
  Clear metadata cache before reading and before readback. Retain complete
  Message/category/status/attempts/error/audit. Do not delete or refund old budgets.
- Snapshot that job's pending AS IDs once, cancel each once through the native
  store, then read back. Check the native DB error separately for the initial
  snapshot and final readback: an empty AS result after a failed SELECT is not
  confirmed absence. The native cancel-until-empty helper can loop forever
  after a failed cancellation and is unsuitable here. Leave running actions alone.
- Hold write/readback or cancellation failure still returns before transport.
  Keep original job/history and emit only a fixed bounded diagnostic identifying
  the failing phase; exclude raw DB/provider errors and body.
- Normal standard and critical notifications use their existing native paths.
  No new mail API/queue, model, customer text, CSS, translation or setting.

## Narrow acceptance

On an isolated native instance with local mail capture: producer zero jobs and
unchanged history; real registered recovery heartbeat still advances; queued
reminders preserve full body/category/attempts/error with zero transport/budget;
forced hold/cancel failures remain silent; normal standard/critical mail still
uses actual native transport. No UI state changed, so no browser rerun is claimed.

The coordinator owns production backup, guarded hold of already queued reminders,
deployment, loaded-source/budget/inbox readback. Local checks do not prove release.
No production mail test is authorized by this implementation.
