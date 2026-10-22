# First initialization with a request-local negative option cache

The regression uses independent native PHP/DB connections. B configures only its
own worker's `options` group through WordPress's supported
`wp_cache_add_non_persistent_groups`, then caches that the registry does not yet
exist. A creates the first real held inquiry through the full native Handler.
B resumes the real `Intake::run` / native Sender boundary to save a second full
inquiry. No instance, Redis, global or production configuration changes.

This is a precise store-boundary test: today's upstream Business Ledger lookup
incidentally clears `notoptions`, so both the shared-Redis full-Handler variant
and a full-Handler variant with process-local options passed even before the
fix. The store cannot depend on that unrelated cache invalidation. The native
intake consumer case exposes its actual stale-negative read/write behavior.

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/i542/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter test_first_two_saves_preserve_both_records_after_negative_cache_warmup
```

Before: **1 test, 10 assertions, FAIL** — two real Woo inquiries existed, but
the final capacity registry contained only one entry. After: **1 test,
12 assertions, PASS** — both complete inquiries remain registered, without a
cache reset between A's first save and B's admission.

The fix reads the native serialized option directly from the database under the
capacity mutex. Initial insert cannot overwrite an existing row; subsequent
writes compare the exact original serialized snapshot and require ownership of
the connection mutex. Readback is also direct SQL. Native positive, negative
and autoload caches are invalidated after changes and on boundary exit. The
existing option format and all user-visible behavior remain unchanged.
