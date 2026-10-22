# 543 · native asynchronous assessment

Source baseline: `c0900e7e5bb152557e7a1135fc94ff8c8f903d97` (the retained-notification fix on the deployed source baseline). This branch does not include the unrelated product-selection change.

Local instance `a543`, `http://127.0.0.1:9311`, owns only its database/site/cache namespace. The native snapshot loader installed the production theme/uploads/active plugins from `20261022-0018`; its readback reported 212 published products, 2756 attachments, zero missing attachment files and zero remaining production origins. Mail is intercepted locally and external HTTP is blocked. A synthetic local service token only enables the simulated provider fixture.

## Before / after evidence

- Incident evidence: general AS dispatch could start assessment after the absolute ten-second deadline, despite subsecond successful model inference. The durable queue is retained; its global sixty-second dispatch lock is not changed.
- Initial real native transport experiment: two/eight-second simulated classifications began at 0.11/0.13 seconds and completed at 2.13/8.14 seconds. Customer responses arrived at 1.18/1.26 seconds. Reading the installed native transport identified its minimum one-second cURL timeout rounding.
- After authenticated early acknowledgment: a representative run returned customer responses at 0.193/0.286 seconds, with `Queue::defer` taking 0.086/0.092 seconds. The separate background PHP process began at 0.105/0.110 seconds and completed classification at 2.125/8.118 seconds. Both initial notices used the actual simulated typed result within the same original deadline. These are local measurements, not a production SLO or model-accuracy claim.

## Executed checks

Commands from `plugins/linker-commerce`:

```sh
LINKER_WP_ROOT="$HOME/de-linker-local/a543/wordpress" \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter 'AssessmentAsyncTest|InquiryAssessmentTest|CustomerEvidenceTest|CustomerReviewTest|NotificationHoldTest'
/opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit
/opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpcs -q
/opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpstan analyse --no-progress --memory-limit=-1
```

The asynchronous tests install a guarded temporary fixture into this owned local instance and remove it afterwards. Actual wall-clock sleeping happens in a separate HTTP PHP process; token claim races use independent PHP/database connections. The service-boundary fixture cannot call any model or send real mail. Existing integration fixtures block this new loopback only inside the PHPUnit process so that their own manually driven consumers remain deterministic; the real HTTP fixture has no such block.

Final local results:

- Native combined assessment/evidence/review/hold/async suites: **53 tests, 514 assertions, PASS** (34.1 seconds).
- Complete commerce unit suite: **1481 tests, 6125 assertions; 257 expected integration/conditional skips**. Native tests are executed separately above.
- PHPStan level 8: PASS. WPCS on every changed PHP file: PASS. Translation validity (8 catalogs) and coverage: PASS, no customer-visible strings added.
- Fresh native timing run: two-second fixture response **0.262 s**, defer **0.082 s**, queue **0.102 s**, total assessment **2.112 s**; eight-second fixture response **0.242 s**, defer **0.110 s**, queue **0.127 s**, total assessment **8.134 s**.
- Legacy identifier additions: zero; source changes are one new native runner and six Queue registration/defer lines. The existing classifier, model channel, provider-budget contract, snapshot and Outbox are reused.

Exact-head CI is recorded in the PR/issue. Deployment, managed-host FPM/LiteSpeed behavior, customer EN/DE paths and inbox acceptance are still required at release. This worktree does not merge or deploy.


## Fresh-snapshot fixture correction

Combination testing on a fresh snapshot exposed a fixture precondition: the original a543 run had a manually configured local synthetic service token, while the fresh instance had none. Both instances actually loaded `WP_Async_Request` and registered the callback. Without a configured service, the unchanged production `Queue::defer()` correctly produced `service_unavailable` and the normal notification, so the fixture's expected wake-up was absent.

Removed the manually seeded token from the owned a543 configuration after a private backup. With no configured token, the original native dispatch test reproduced RED (`dispatches=0`). The fixture correction generates a synthetic token only inside a local PHPUnit/HTTP/worker PHP process when the constant is absent. It does not write WordPress configuration, replace an existing token, change the production configured guard, or contact a provider. Each temporary HTTP loader has a distinct filename and is removed on teardown. A separate unconfigured-service test verifies `uncertain/service_unavailable`, ordinary notification handoff and zero wake-ups.

On this token-free snapshot, all **8 Async tests / 150 assertions** pass, including independent PHP/database workers, disconnected customer HTTP and actual two/eight-second classification simulation. Representative customer responses: **0.352/0.637 seconds**; queue starts **0.139/0.269 seconds**; assessment completion **2.285/8.291 seconds**. An independent `wp` process afterwards reads `token_defined=false`, while the native callback remains registered. Combined release-tree results are attached to the follow-up PR/issue; no production setting was changed.
