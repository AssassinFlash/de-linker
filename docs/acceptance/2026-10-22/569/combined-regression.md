# Combined native registration regression

The combined candidate was `2d632574fb655d80ce4031abe7912e443254a201`. This follow-up changes only the two native core-profile fixtures in `RegistrationCapacityTest`; registration guards, transaction ownership, quotas, notification routing and customer-facing output are unchanged.

## Reproduction and cause

The registration class alone passed on the unchanged combined candidate: **64 tests / 1,541 assertions**. A minimal predecessor sequence reproduced the combination failure:

1. `AccountsAdminTest::test_native_widget_toolbar_and_history` loads WordPress's actual `wp-admin/includes/admin.php`.
2. `RegistrationCapacityTest::test_pending_core_profile_error_restores_earlier_billing_writes` manually fires `personal_options_update` without the native form's `email` field.
3. `RegistrationCapacityTest::test_busy_core_profile_does_not_save_earlier_extension_fields` checks the independent connection's capacity lock.

The first profile fixture raised `Undefined array key "email"` in WordPress 7.1.3 `send_confirmation_on_profile_email()` (`wp-includes/user.php:3884`). The predecessor installs this real native callback through `admin-filters.php`; the callback remains active in the shared PHPUnit process. The exception interrupts the simulated request before its `user_profile_update_errors` hook can complete the normal rejection and transaction cleanup. The next fixture then cannot acquire the capacity lock: native `GET_LOCK` returns `0`, where its strict assertion requires `1`. The three-test red result was **1 error / 1 failure / 15 assertions**.

Both profile fixtures now explicitly load the native admin hooks, assert that `send_confirmation_on_profile_email` is installed, and provide the current owner's authoritative, unchanged native email in `$_POST['email']`. This gives the real callback the same required field as the actual core profile form. It neither removes the callback nor simulates successful cleanup. The existing rollback, field preservation, capacity-error and independent-connection lock assertions remain intact. The test's existing cleanup restores `$_POST`.

## Verification

| Native or static check | Result |
|---|---|
| Exact three-test predecessor sequence | **3 tests / 25 assertions, PASS** |
| Native admin predecessor followed by the complete registration class | **65 tests / 1,552 assertions, PASS** |
| Same predecessor, registration class and the complete VAT notification capacity class after local fixture restoration | **72 tests / 1,620 assertions, PASS** |
| WPCS, changed PHP fixture | PASS |
| Commerce full PHPStan level 8 | PASS, no ignore or baseline added |
| Diff whitespace | PASS |

The native command runs from `plugins/linker-commerce` with the existing isolated instance supplied as `LINKER_WP_ROOT`; `PHPRC` points to that instance's PHP configuration so real child processes inherit it:

```sh
php vendor/bin/phpunit -c phpunit.integration.xml.dist \
  --filter 'AccountsAdminTest::test_native_widget_toolbar_and_history|RegistrationCapacityTest'
```

No frontend source, copy, markup or styles change, so this fixture correction introduces no new visible state. The earlier account screenshots are not presented as new coverage. The entire combined native suite and the other mail/held changes remain the coordinating branch's integration gate.

## Separate local VAT diagnostic

A later selection initially reported three VAT assertions with an accepted original job ID but no remaining job. The same three failures reproduced in the VAT class alone, excluding the registration predecessor. Read-only SQL/mail observers showed actual tester-only local captures followed by original-job deletion. SMTP availability was false; this was not an SMTP configuration explanation.

The intentional profile red run had left the local fixture's legacy throttle row and persistent Redis cache inconsistent: `get_option` returned 80 timestamps while the authoritative SQL row was absent. The VAT fixture's `update_option` therefore attempted an `UPDATE` of a missing row and kept a cached value without filling the native transport ledger's source. Invalidating only this instance's derived option cache made the unchanged VAT class pass: **7 tests / 65 assertions**. No VAT, transport, budget or assertion code was changed.

The original local database was backed up before testing. The exact original 80-timestamp legacy value was recovered from that backup, with its original timestamps; the one synthetic customer left by the deliberately interrupted red request was removed through native deletion. The private evidence package retains the SQL/query traces, mail capture metadata, red and green logs, JUnit and before/after readbacks. Raw database contents, email bodies, credentials and request data are not committed.

The final native readback matches the starting business state: 15 users, 13 pending accounts, 4,029 business bytes, zero interrupted/reserved resources, all 38 historical held jobs' status and complete metadata unchanged, the same public operation ledger hash, and the original legacy 80-timestamp serialized value exactly equal to the backup. No public operation allowance or mail history was reset.
