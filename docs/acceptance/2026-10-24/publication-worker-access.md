# Publication worker application credential acceptance

The implementation is isolated in the publication-worker-access worktree, based
on `fe87a8d42fd4f74266186770cb95896902ad95f4`. The initial source/test/contract
commit is `b834f406`; the native root-dispatch correction is `8e13d580`. The
deployment owner runs the native fixture on the existing `publication614`
instance. The implementation agent did not write that instance or production.

The fixed native purpose is
`6c50fdd8-1640-4d5e-9ac8-05fefd9aa290`. This is a public application ID, not a
password or production credential UUID. No production key was created here.
Provisioning and mandatory retirement order are in
[the credential contract](../../agents/publication-worker-access.md).

## Diagnoses and corrections

The first native fixture invocation failed before its body ran. The installed
WP-CLI 2.12 `eval-file` command normally evaluates a leading PHP close tag before
the file, which makes its strict-types declaration invalid. The driver now uses
the native `--use-include` option. The fixture also prints safe, fixed assertion
descriptions to stderr before rethrowing, and always cleans up in `finally`.

The initial non-job matrix then observed
`GET /wc/v3/products → 401 / woocommerce_rest_cannot_view`. That was Woo's
anonymous controller refusal. It did not prove a scope-generated 403. Inspection
of actual core and Woo timing exposed a real gap: current-user resolution could
run late, after core's application-password error filter. Cookie initialization
could turn the late native refusal into anonymous access, and a public WC
endpoint could consequently execute.

The correction makes the restriction sticky in
`wp_authenticate_application_password_errors`, whose user/item already passed
core's password match. This grants no identity or capability. Successful native
authentication is tracked separately through
`application_password_did_authenticate`; only that successful state can permit
an HTTP job dispatch. The old unit test now explicitly distinguishes an
unverified credential/cookie from a verified-but-refused native purpose item.
The latter regression failed with one callback execution before this change
and passes with zero. The native matrix includes a genuinely public WC canary,
an anonymous 200 control, and Store API paths. It accepts no 401/404 exception
for a purpose request: every non-job path must return 403.

The concurrent canary readback also exposed a fixture-observation error: the
long-lived CLI process could retain its earlier option value after an HTTP
process updated it. The fixture now creates its two non-autoload counters at
zero, evicts only those two exact `options` cache keys before readback, and
asserts 0 reads / 0 writes before controls and 0 reads / 1 ordinary-key write
after concurrency. It never flushes the shared cache or evicts `alloptions`.

After the first complete native pass, an additional unit counterexample showed
that an internal job before priority 20 could spend the outer request's one-use
permission. Priority-15 and priority-minus-one pre-dispatch children, and a child
after the priority-110 authentication hook, were each allowed while the outer
HTTP job was incorrectly denied. This was treated as a required correction.

`8e13d580` identifies the native HTTP root structurally before spending that
permission: the full trace must contain exactly one native server `dispatch()`
and `serve_request()` pair, directly adjacent, with the same server object.
Other server instances count as nesting. Internal refusals preserve the outer
permission. The trace uses `DEBUG_BACKTRACE_PROVIDE_OBJECT |
DEBUG_BACKTRACE_IGNORE_ARGS`; no arguments are collected and the trace is never
logged or retained. The small check is necessary because native pre-dispatch
runs inside `dispatch()` and `is_dispatching()` also reports true for children.

## Verification

- Initial corrected scope, `b834f406`: PHP 8.3 unit suite **37 tests / 124
  assertions**, complete MU PHPStan and WPCS passed. Root reported native
  execution session `12119`: **1 PHPUnit test / 11 assertions**, the exact
  **48-check** inner matrix and zero purpose canary reads/writes passed in
  **6.510 seconds**. This is evidence before the subsequent root-frame delta.
- Root-frame delta, `8e13d580`: the three ordering regressions were first red.
  Final isolated unit suite **45 tests / 148 assertions** passed, including the
  same request object, another server, nested serving, pre-dispatch ordering and
  authentication ordering. Complete MU PHPStan and WPCS passed.
- The native driver now requires exactly **52 checks**, adding both early
  pre-dispatch and post-authentication children. Each verifies that claim, ack
  and another-server children return 403 while the outer HTTP job returns 200.
  Root reported the final run passed: **1 PHPUnit test / 11 assertions**, exact
  **52-check** matrix, **6.507 seconds**. The implementation is cherry-picked on
  root as `39f1c87f`. Its guard SHA-256 is
  `67b45ce9bb4fb9bcbe5801d9d44be1cb5bb84da33b11b9c172dcccd8c000e497`.

Reproduce the native check from this worktree's `mu-plugins` directory, while the
instance owner holds its write lock:

```sh
LINKER_MU_WP='just wp publication614' \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  --testsuite integration --filter PublicationWorkerAccessSmokeTest
```

The fixture creates marked synthetic users/application passwords, substitutes
only local canary callbacks for the jobs routes, and restores the previous MU
files. It never claims or acknowledges a real publication job, sends mail,
changes MFA, or changes the old inventory key. The root owner performs actual
instance cleanup and source/queue readback independently.

Production provisioning, worker restart, source load/ack readback and rollback
remain deployment-owner work. A local fixture or committed key scope does not
declare those deployment gates complete.

At author handoff, independent Spec and Standards review of the final delta is
running. The sole author worktree is retained until those reviews and root
integration are accepted. Its temporary vendor symlink is removed; it pointed
to existing root dependencies and did not duplicate or modify them. No new
local instance, database, backup, dependency installation or service was made
for this implementation.
