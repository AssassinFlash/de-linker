# Genie entry-context lock deadline

## Production symptom

On the deployed #790 candidate, the WordPress runtime dependencies all loaded
once and all required globals existed, but Genie still intermittently displayed
`Genie could not load.`. Chrome resource timing recorded:

```text
https://de-linker.com/wp-json/linker-ai/v1/genie/entry-context
duration: 5004.7 ms
responseStatus: null
```

The client aborts `entry-context` at 5,000 ms. That live timing proves the
browser deadline expired; by itself it does not identify the server-side
waiter. The cold-mint path also had a 5-second named-lock wait at the same
boundary, so lock contention would reach the browser deadline. The exact
original waiter was not separately instrumented.

## Change

- Keep the browser-claim lifetime at 5 seconds.
- Wait at most 1 second for the MySQL named lock.
- Reuse the existing read/add-option fallback when another request holds the
  lock, which still converges both callers on one browser key.

The new integration test holds the real MySQL named lock in a separate process
and sends the actual REST request over HTTP. It requires the request to wait
past the bypass threshold but return in under 2 seconds, publishes the claim
from the timeout fallback, and proves a second cookieless request receives the
same scope.

## Local verification

- `EntryScopeConcurrencyTest`: 4 tests / 56 assertions.
- `just genie-concurrency ci_preflight`: 7 tests / 98 assertions.
- Linker Tools PHPUnit: 313 tests / 2,522 assertions.
- Linker Tools PHPCS: pass.
- Linker Tools PHPStan: pass.

Production deployment and browser readback remain required before this fix is
complete.
