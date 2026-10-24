# German frontend supply regression

Integration found the three German navigation supply descriptions empty on the actual `/de/produkte/?product-page=2` page, although CLI rendering of the same templates was populated. The direct anonymous HTTP reproduction confirmed an empty featured description and zero home/commercial supply sentences. This was a frontend language-query defect; it was not an empty Woo supply set.

A read-only native frontend probe on the existing `publication614` WordPress confirmed the boundary. With the real Polylang frontend's current language set to `de`, category candidates were zero. Instrumenting only `get_terms_args` in that process showed an internal `slug=[home-storage,commercial-storage]` lookup with `lang=de`. A process-local control removing that term-language restriction restored 28 candidates and the real GoodWe/Pylontech/SAJ brand names. The downstream `pa_brand` object-ID query and canonical permission worked. All temporary filters and the language change ended with that process; no hook, route or instance configuration was installed.

The cause is Polylang's native `PLL_CRUD_Terms::adjust_query_lang()`: while a product query has an empty `lang` value, an internal term query with `slug` is still scoped to the current frontend language. `suppress_filters` and the existing internal post-query marker do not override that nested term lookup. WP-CLI did not load this frontend context, so the prior CLI check missed it.

The fix retains the existing fresh batch. Inside its candidate reader, a native `get_terms()` call resolves LC's category slugs with explicit `lang=''`, before the product query begins. The product query then uses those term IDs and native descendant expansion, so its internal lookup no longer repeats the English slug under German language filtering. Publication, canonical source, reference-role and native visibility checks are unchanged. There is no brand hardcoding, old-copy fallback, global language-filter override or second product source.

The new read-only fixture boots the existing native frontend outside WP-CLI, verifies `PLL_Frontend`, and switches the real process-local Polylang language between `en` and `de`. It loads the author's exact SupplyBrands source under an isolated class/typed adapter, leaving the shared integration plugin symlink untouched. It reads both actual header templates and executes their ten fragments. No records, routes, settings or instance files are written, and no model is called.

```sh
/opt/homebrew/opt/php@8.3/bin/php -c /Users/chesterjohn/de-linker-local/publication614/php.ini plugins/linker-commerce/tests/fixtures/supply-brands-frontend.php --wordpress-root=/Users/chesterjohn/de-linker-local/publication614/wordpress --site-url=http://127.0.0.1:8888
```

Before the source fix, English home/commercial/storage scopes were populated and all three German scopes were empty; the fixture exited 1. After the fix, all seven native frontend checks pass. All ten real fragments are populated: German uses `Energiespeicher von`, `Heimspeicher-Batterien von`, `Gewerbespeicher von` and `und`; the current supply sets match English and contain no EcoFlow. This is a native source/frontend regression, not a claim that the shared HTTP site has already been updated.

The unit fixture also checks explicit all-language category identity lookup and term-ID descendant queries. The existing pure-memory hierarchy/stock/visibility races still pass, preserving one refresh per independent read and zero PDF access. Integration must fast-forward/present the fixed source and rerun the original real German HTTP/menu path and CUA before publication.
