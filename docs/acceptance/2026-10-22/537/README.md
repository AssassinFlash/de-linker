# Notification hold acceptance

Local instance `h537`, http://127.0.0.1:9302, separate worktree `notification-hold-537/de-linker`; installed live snapshot `20261021-1023` (212 published products, 2,756 attachments, no missing attachment files). All mail remains locally isolated. A fake local service token enables HTTP interception fixtures; no model was invoked. No production write or deployment was performed by this execution task.

Release source base: `dcd5560d`. The unrelated product-selection update on main is excluded.

## Before/after

- `red.txt`: native manual retry of an already held job previously consumed mail budget.
- `red-lifecycle.txt`: stale FINISH previously rewrote held evidence.
- `red-release.txt`: no native original-job release service existed.
- `red-capture-note.txt`: composing a queued message previously created a false Woo “sent” note.
- `red-busy-finish.txt`: a busy held FINISH previously scheduled another callback.
- `native.txt`: actual native lifecycle, customer evidence/review and notification regression suite; includes two independent PHP/DB connections, concurrency, nonce rejection, original-job one-delivery and failed-schedule rollback.

## Computer Use

Eight screenshots: `en-held-1440.jpg`, `en-held-390.jpg`, `de-held-1440.jpg`, `de-held-390.jpg`, plus the corresponding `*-released-*` files. Native WooCommerce inquiry editor; held reason/time/original job and separate release form are visible without a customer UI change. The browser viewport override was reset after capture.

The protected German button was clicked for synthetic local inquiry #8196, original job #8197. `ui-readback.json` records unchanged inquiry status, model initial label and original body/target; held markers cleared, one pending delivery action, original job still private with attempts 0, throttle 80 unchanged. The scheduled date is the next actual local quota slot, so the released UI is not represented as physical delivery. A separate isolated native test exercises exactly one eventual delivery after capacity becomes available.

`copy-review.md` records the wording review. `docs/specs/537-notification-hold.md` owns behavior, cache/mutex boundary and rollback cautions. Independent Spec and Standards review is coordinated by the parent before delivery.
