# Native erasure versus staff restoration

Reproduced on isolated `i542` with the production theme/uploads/database snapshot,
using two independent PHP processes and DB connections. No real model or mail
calls. Source before the fix: `9463a829db54c5d3fc773db5d796380dfdd593ca`.

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/i542/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter 'test_native_erasure_and_staff_release_serialize_across_connections|test_completed_native_erasure_cannot_be_resurrected_from_stale_object'
```

| Actual interleaving | Before | After |
|---|---|---|
| A takes record release mutex and retains original Woo object; B runs the complete native eraser on its own connection; A resumes restoration | B reported `erased` while A held the release mutex; A could capture from its stale object | B reports retryable `intake_erasure_busy` before any native erase listener writes; A can complete its authorized release; no premature erase claim |
| A retains original Woo object; B completes native erasure and removes registry/meta; A takes the release mutex and attempts restoration with the old object | Restoration returned a new job after completed erasure | Restoration returns `WP_Error`; no job is created; durable ERASED marker and deleted registry/meta remain unchanged |

Before: **2 tests, 17 assertions, 2 failures**. After: **2 tests, 24 assertions,
all pass**, in 1.542 seconds. This is controlled connection interleaving, not two
sequential calls against the same Woo object/cache. The worker executes
`WC_Privacy_Erasers::remove_order_personal_data`; it does not mock the eraser.

Root cause: the erasure callback used only the capacity mutex, while restoration
already held a separate record mutex and then trusted an object loaded before
capacity acquisition. Removed registry entries were not a release refusal.
The fix gives native erasure the same record→capacity lock order, writes the
durable erased marker before the remaining native lifecycle, and requires both
fresh native state and a live registry association before notification capture.
