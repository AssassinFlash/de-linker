# Native VIES response overwritten by an earlier engine fixture

The full combined native run on `243bb194a4470eb13d4a414017ea554622b53c33` had one remaining failure: the first VAT notification capacity case expected `valid` at line 65 and received `unverified`. This occurs before its accepted-job assertions. It is a separate failure from the earlier local throttle-cache diagnostic.

## Exact native reproduction

Running only these two existing methods against the unchanged combined source reproduced the same failure in 0.627 seconds: **2 tests / 15 assertions / 1 failure**.

```text
ReadSolutionRestTest::test_a_guest_is_refused_and_the_owners_token_signs_in
VatNotificationCapacityTest::test_full_pool_preserves_latest_approved_account_verdict_then_recovers_one_job_without_vies
```

The private read-only HTTP observer recorded one VIES request through WordPress's real `pre_http_request` filter chain:

| Filter point | Observed native response |
|---|---|
| Priority 0 | No response yet; the callback inventory includes the earlier engine fixture at priority 10 |
| Priority 2, after the VAT fixture's actual priority-1 provider | JSON has `valid: true` |
| Priority 11, after `ReadSolutionRestTest`'s priority-10 callback | JSON contains `status`, `yield`, `storage`, `metrics`, `selected`, `warnings`; it has no `valid` field |
| Final local isolation filter | The same engine-result response remains |

The anonymous engine mock was not removed after its test and returned its engine result for every URL, including requests that already had a response. The real `ViesClient` then correctly treated that unrelated JSON as unverified. No VIES cache, limiter, transport budget or production persistence change was needed.

## Narrow fixture correction

`ReadSolutionRestTest` now keeps the callback as a local variable and registers its exact removal through the existing per-test `later()` cleanup. The mock answers only the synthetic engine's `/design/residential` URL, and preserves any earlier native response.

A new native filter-contract test first failed on the unchanged mock: an unrelated local URL received an engine result instead of retaining `false`. After the correction it checks an unrelated URL with no response, an unrelated URL with an existing response, and the engine URL with an existing response; none records an engine invocation. These checks invoke the real WordPress filter without sending a network request.

All existing saved-solution authorization, schema, language and price-exclusion assertions remain in place. The existing VAT assertions still require a valid verdict, one provider call, one original notification job, correct current Reply-to, and no repeated VIES call during recovery. No VAT fixture assertion was weakened, and no business implementation changed.

## Checks and boundaries

| Check | Result |
|---|---|
| New fixture-scope regression before the correction | **1 test / 1 assertion / 1 failure**, engine result incorrectly replaces `false` |
| Original two-method sequence after the correction | **2 tests / 31 assertions, PASS**; one VIES filter chain retains `valid: true` throughout |
| Complete saved-solution REST and VAT notification capacity classes | **14 tests / 126 assertions, PASS** |
| Changed PHP fixture WPCS | PASS |
| Commerce full PHPStan level 8 | PASS, no ignore or baseline added |
| Full native suite, with JUnit | **484 tests / 7,402 assertions / 1 unrelated failure / 9 skips, no errors**; all seven VAT cases pass after the complete preceding suite |

The full run is **not a clean full-suite pass**. Its only failure is the unchanged `ContactNavigationTest` German brand dataset: this local snapshot renders `/de/Marke/saj/`, while the test expects `/de/brand/saj/`. The same case fails alone without running any saved-solution test, and its source is identical to the combined base. No route setting, business source or assertion was changed for that separate local snapshot difference.

All nine skipped cases are `ProductSearchRestTest`: the two item-number datasets, unknown query, five invalid-query datasets, and German product URLs. The JUnit names were checked against a separate verbose run; each reports `Set LINKER_COMMERCE_TEST_SITE to a local WordPress with the catalogue.` That HTTP-site environment variable was not set for the native suite. No new skip was introduced.

The successful two-method observer additionally confirms that the HTTP callback inventory after teardown exactly matches its before-test inventory. Only the original ACF callback and local HTTP isolation remain; the engine mock, VAT provider and per-test queue-runner filters are removed.

The minimized red ran in the coordinator's explicitly loaned `si533` instance with its original source unchanged. Its native before/after aggregates were byte-for-byte identical, including all 38 mail jobs and their full metadata hashes, public admission ledger, legacy mail history and transport ledger. That instance already had 16 users, 14 pending accounts and 4,362 business bytes when loaned; this diagnostic preserved that exact starting state.

The correction and native green checks run in the separate `codex/569-vies-fixture-isolation` worktree with the existing isolated `r569` snapshot. No production writes, deployment, real mail, model requests, browser actions or global configuration changes were made. SQL snapshots, response-shape observations, native logs and JUnit stay in the private incident evidence directory; no message bodies, credentials or personal data are committed.

The final `r569` readback retains 15 users, 13 pending accounts, 4,029 business bytes, zero interrupted/reserved resources and all 38 historical held jobs unchanged. Both native mail-history option hashes match the original local backup. The public admission ledger hash changes during the full native run: all 12 original receipts remain byte-for-byte unchanged, three native synthetic receipts are added, and six already-expired buckets are pruned by normal admission. Retained bucket usage does not decrease; original events remain. No quota or operation history was reset, and this change is not presented as an unchanged ledger hash.
