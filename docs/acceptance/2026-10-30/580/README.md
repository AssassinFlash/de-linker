# #580 Genie native runtime recovery

The inline Genie loader no longer treats a printed WordPress script tag as
proof that its browser runtime exists.

## Browser fault injection

The existing `g563i` instance was reused and stopped after the checks.

- EN and DE were each checked at 1440 and 390. With both native and bare i18n
  blocked, each language showed its own error and Retry labels with no
  horizontal overflow. After unblocking only the bare fallback and clicking
  Retry, each rendered its own Genie welcome.
- The live boot payload mapped every dependency URL. Opening Genie beside the
  German planner retained the native `hooks.min.js?ver` and `i18n.min.js?ver`
  requests and made no bare request for either. The Genie bundle loaded once.
  The stopped planner worker was not used to claim a successful planning
  request.

## CI concurrency failures found and fixed

The first complete native preflight found
`GlobalBusinessCapacityTest::test_two_business_connections_share_the_last_complete_record_slot`
returning `linker_intake_pending` instead of `linker_business_capacity`.

The cause was lock order: one business transaction owned the capacity option row
while a competing worker held the named IntakeStore mutex and used
`FOR UPDATE NOWAIT`; the first transaction then needed that mutex to bind. The
fix permits only business first-save work to release the named mutex and retry
MySQL 3572 within its existing one-second budget.

The first version of that fix applied the retry globally and made
`MailCapacityTest::test_uncommitted_outer_capacity_fails_competing_native_worker_without_waiting`
take 1.0045 seconds instead of failing immediately. The retry is now an explicit
opt-in used only by `BusinessCapacity`; mail and unrelated IntakeStore consumers
retain `NOWAIT`.

## Verification

- `EntriesTest`: 31 tests / 185 assertions.
- Full linker-tools PHPUnit: 313 tests / 2520 assertions.
- Full commerce PHPUnit: 2181 tests / 7982 assertions, 525 native cases skipped.
- PHPCS, ESLint and Prettier: clean.
- PHPStan with a 1 GiB memory limit: clean.
- `just ci-content`: pass.
- Both original lock-contention tests passed five consecutive rounds.
- A real two-connection deadline case held the capacity row open past the
  budget and proved business retry returns `linker_intake_pending` in under 1.2
  seconds, so it cannot gain a second one-second acquisition window.
- Native mail group passed 252/252 in classic storage and 252/252 in HPOS.
- Native inquiry 155/155, inventory 65/65 checks, runtime 19/19, and admin checks
  all passed.
- The first remote CI pass exposed a test-only race: the provider-budget retry
  case used the same 0.1-second wall budget meant for the separate deadline
  case. Budget exhaustion now has ample wall headroom; the deadline case remains
  at 0.02 seconds.

The retained screenshots and machine-readable readback are in
`/Users/chesterjohn/de-linker-data/acceptance-548-533-20261030/580-*`.
