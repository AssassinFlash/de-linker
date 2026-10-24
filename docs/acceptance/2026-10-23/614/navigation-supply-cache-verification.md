# Navigation supply cache and copy regression

PR 626's independent Spec review found that the first implementation selected category/visibility candidates before refreshing the request-local cache. `cache_results=false` does not refresh the `product_cat_children` hierarchy option or Woo's stock-hiding option. The Woo visibility-ID helper also has a PHP static map that a WordPress runtime-cache flush cannot clear.

The corrected `Publication::published_ids()` accepts either its existing ID array or a native candidate-reader callback. It refreshes first, then calls the reader once and filters permission in the same assembly. The navigation reader queries `product_visibility` by Woo's native term names, allowing the native taxonomy query to resolve current IDs. Product permission, engineering-role filtering and brand associations stay inside the resulting fresh read. No document assembly or PDF is used.

The updated unit fixture separates persisted and runtime state. Before the source fix it failed seven checks, including the reparented category, stock option, retained static visibility IDs, a newly added descendant, and the overbroad commercial sentence. After the fix the focused SupplyBrands/VisibilityRead tests pass 10 tests and 283 assertions. The direct array authority checks remain fresh; the callback is observed only after refresh and only once.

## Native function replay

`plugins/linker-commerce/tests/fixtures/supply-brands-cache.py` extracts the installed WordPress `get_term_children()` / `_get_term_hierarchy()` and Woo `wc_get_product_visibility_term_ids()` functions verbatim, and runs the actual publication/navigation classes with in-memory adapters. It never boots WordPress or accesses the database, HTTP, a model or a writable instance. The adapters retain separate persisted/runtime options and a genuinely process-static native Woo visibility map. Candidate SQL is represented by category and term-ID intersection over the persisted fixture products; this is a focused native-function replay, not a full WordPress integration run.

Command from the author worktree:

```sh
python3 plugins/linker-commerce/tests/fixtures/supply-brands-cache.py --wordpress-root /Users/chesterjohn/de-linker-local/publication614/wordpress --php /opt/homebrew/opt/php@8.3/bin/php
```

The same command with `--source-revision faa3be3e` returns exit 1: the category, stock and recreated-visibility cases expose `Moved`, `GoodWe` and `Hidden`. The fixed source returns exit 0: all three fragments are empty. Both runs prove the native Woo helper still retains ID 101 after the persistent visibility term becomes 201, and the fixed reader excludes that product without relying on the helper. Both runs use exactly three refreshes for three independent reads. Any PDF resolution throws.

## Commercial copy

The independent Spec reviewer also challenged the fixed All-in-One/battery-system prefix. Integration approved `Commercial storage from ` / `Gewerbespeicher von `. Both actual header files are read by the fixture with only a published battery-system product remaining; desktop/mobile full output now names the commercial category. Other header structure and all ten current-Woo brand fragments remain intact. The draft, objection and approved final wording are in `navigation-supply-copy.md`.

Final source checks: Commerce unit suite, complete Commerce suite with unavailable HTTP integration cases skipped, Commerce PHPStan, WPCS on the four changed PHP files, Python runner syntax and `git diff --check`. Integration owns the final fixed-head independent review, native site readback, visual acceptance and deployment; this note does not claim those gates are complete.
