# Existing draft: first evidence binding on normal Woo publication

This is a narrow continuation of [the Woo publication authority](https://github.com/AssassinFlash/de-linker/issues/614), based on merged main `553b654083b6aedf61b12d428cb3419c7a4c5501`. The separately accepted navigation source is unchanged.

## Failure and root cause

The first production adoption command iterates the published manifest. An existing draft therefore may retain valid raw figures, FAQs and hosted PDFs without either generated evidence key. Native WordPress `update_metadata()` returns false before emitting its update action when the new value equals its single current value. A normal publish that leaves those source fields unchanged consequently queues preparation but never reaches the existing metadata-driven binding capture.

The initial pure-memory replay used the installed WordPress `update_metadata()` function and the actual figure editor/publication module. It returned `prep_queued=true`, `binding_absent=true`, and `native_unchanged_meta_write=false`. Status-only WordPress publication also queued without initializing bindings.

The root session then ran the fixed test-only commit `056035564301c207bc5459f9d7e4b47c9a1c1284` against the actual existing `publication614` WordPress instance on old main `553b6540`, using PHP 8.3 and the integration bootstrap. Result: **1 test, 8 assertions, exact behavioral failure**: `Final Woo save initialized the missing figure bindings.` No bootstrap/type failure occurred. The fixture completed its restoration. The private runtime log is retained outside the repository as `phase2-first-binding-native-red.private.log` in the existing withdrawal evidence directory.

## Smallest native seam

Woo's native `WC_Data::save()` dispatches `woocommerce_after_product_object_save` after its data store's update/create call. The editor's product-data save, Woo REST and Woo CRUD converge there. LC owns presentation and has no role in evidence initialization. Woo owns the save event, metadata and Action Scheduler persistence; it does not supply this site's generated document-identity/byte-SHA bindings. The custom addition is only the missing initialization at that native event.

`Module::product_saved()` calls `EvidenceBindings::capture_missing()`, then emits the existing preparation signal. The capture first uses the existing fresh publication check for both saved locale and canonical source, then independently tests each canonical binding key with `metadata_exists()`. Only a missing key is initialized. An existing empty string, null, array or stale binding is retained exactly; the existing figure/FAQ capture and byte-match rules are unchanged. A routine save of an initialized product reads no PDFs through this new seam.

Plain status-only `wp post update` remains a WordPress write that queues preparation and immediately changes public permission. It is not a completed Woo object save, so this change does not claim to initialize missing bindings for it. Normal product/technical-source maintenance uses the Woo editor, Woo REST or Woo CRUD. No extra manual per-tool synchronization or delayed CLI-specific layer is added.

## Regression evidence and execution boundary

The author ran the focused WP_Mock tests and Commerce unit suite, with actual temporary PDF bytes removed after each test. The focused tests cover initial canonical capture through a locale save; fresh source/locale withdrawal despite prewarmed published runtime copies; per-key initialization; empty/malformed existing metadata; unchanged stale bindings after same-URL byte replacement; initialization-before-final-queue ordering; and the status-only WordPress boundary. The existing cited-FAQ replacement/reordering regressions remain included.

Author verification uses the project's explicit `/opt/homebrew/opt/php@8.3/bin/php`, with `plugins/linker-commerce` as the working directory. `vendor/bin/phpunit` passed **1725 tests / 7130 assertions**, with **333 integration cases skipped** because this author did not load WordPress. The focused filter passed **13 active tests / 91 assertions** (the matching three native tests were skipped). Full `vendor/bin/phpcs -q` and `vendor/bin/phpstan analyse --no-progress --memory-limit=-1` both passed. An earlier direct executable invocation used the PATH PHP 8.5 interpreter and reported six unrelated `$argv` errors in the unchanged mail-budget fixture; the project-specified PHP 8.3 command passed without source changes to that fixture.

The native `tests/php/Integration/PublicationInitialBindingsTest.php` creates only uniquely tagged fixture drafts and tiny PDFs. It deletes only those fixtures' generated keys to represent the pre-adoption draft, then uses the real `WC_Product::save()` publication path. Its cases assert:

- Same-value native metadata updates return false; normal draft-to-publish generates both first bindings and leaves durable preparation work. Raw facts/FAQs/relations, fact content fingerprint, document identity and PDF SHA stay unchanged.
- After an initialized product's PDF changes in place, draft/publish keeps both old binding records exactly and public facts/FAQs remain unavailable.
- Draft withdrawal and removal of the last explicit document relation keep the file gate at 410 without deleting the original. Recreating the relation does not renew existing intentionally empty binding fields.

The fixture captures only publication Action Scheduler actions stored by its own PHP process, removes those exact IDs after its owned products/files are removed, and restores the original pending marker. It does not reconcile or overwrite preparation receipts, create a new instance, replace plugin links, or call a model. Native execution belongs to the root integration session; this author did not write an instance or production data. The fixed-source native green and final production readback are still separate acceptance gates until their results are recorded.

The aggregate product/source revision can change because generated binding metadata is part of the product version and the product's publication state changes. The preserved revisions asserted here are source-content fingerprints and document byte identity, not a false claim that the whole published manifest remains identical.

No customer-facing copy, markup, styling, image or model route changed. Normal code rollback restores the previous hook behavior; generated bindings are ordinary retained product metadata and remain governed by fresh status, relation and byte checks.
