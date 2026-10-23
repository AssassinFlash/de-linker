# Woo engineering reference and preparation receipt delta

This is local source work for [implementing WooCommerce publication authority](https://github.com/AssassinFlash/de-linker/issues/614). No production data, model route, shared local instance or original PDF was changed by this worker.

## Confirmed source design

The retained engineering overlay contains one verified Trina reference module, 30 existing figure entries and two hosted PDF rows. Runtime `EngineeringFeed` and `Publication` no longer read that file. `data/engineering-overlay.json` remains only the explicit CLI migration input/evidence; future maintenance is on the Woo product, using the existing Figures and Documents meta boxes and native Woo attributes.

The created simple product has `_linker_engineering_role=reference_pv_module` and its existing `mat_*` identity in `_linker_engineering_id`. It is published, hidden, virtual, without price, SKU or any product category. Brand/model are native Woo attributes. Woo's default category assignment is removed after a reference save. Native visibility, Store API direct/collection reads, existing draft pruning and purchasing exclude this role. The purchasing guard runs at priority 20, after the existing unpriced inquiry permission at 10. The public identify label/text contract returns `unavailable` without a sales product ID. The canonical publication manifest retains the reference for engineering consumers.

`feed.overlay` derives its figures through `Publication::figures_for` and its documents through the same ordinary current Woo association. Each overlay includes `canonical_product_id`, `product_revision` and `reference_revision` (the latter two are identical). Documents retain `document_id`, `document_revision`, `blob_sha256` and `product_ids`. No SHA or URL alone authorizes a figure. Missing bound inputs required by the engine's native module loader (seven numeric fields and dimensions) omit the reference from the ready overlay while retaining the Woo source record. Consumers reject operations requiring that reference and keep independent operations available.

Based on this independent-operation requirement, the initially proposed combined compatibility version was corrected with the engine owner: `compatibility_revision` hashes only the compatibility contract. Reference facts, bytes, association and publication changes are separately validated through their ordinary product/document dependencies. A reference change therefore does not invalidate a calculation that never used it.

## Reversible migration

Run only in the assigned environment, after the required backup when applying data changes:

```sh
wp linker-commerce publication migrate-reference --dry-run
wp linker-commerce publication migrate-reference
wp linker-commerce publication migrate-reference --withdraw=<created-product-id> --dry-run
wp linker-commerce publication migrate-reference --withdraw=<created-product-id>
```

The preview resolves the originals and checks the native Woo attributes without writing. Initial adoption starts draft, associates existing local PDFs, writes the retained facts, captures their evidence once and finally publishes. Missing/private/withdrawn originals stop adoption. Reruns find the existing engineering identity and leave all Woo data, status and bindings unchanged, including when the source is draft or its URL now has different bytes. The reversal sets only this migration's marked reference record to draft; files and source data remain. Restore through the normal Woo publication control. No new upload, independent editable JSON source or sales SKU is needed.

## Knowledge preparation contract

Knowledge `jobs/ack` now distinguishes safe `prepared_products` from complete preparation of all current document associations. `preparation_complete` must be boolean `true` to complete the job; an absent, false or non-boolean value keeps it pending and retryable while retaining the current safe products. The queue records `Some current document associations still lack proven passages.`. `unprepared_documents` accepts only current `{document_id, product_id, reason}` associations (`no_proven_passage` or `document_unparsed`); no excerpt is persisted. Nonempty diagnostics force incomplete status even if the worker claims true. Reference PV records are outside the knowledge expected-product scope. Engineering receipts keep their existing contract. Preparation state stays outside the source revision.

## Verification and handoff

Commerce full unit: **1,272 tests / 6,493 assertions passed**. Full level-8 PHPStan passed. WPCS passed for all 17 changed PHP files. The POT/PO passed `msgfmt --check`, and the compiled German MO was read back for all four admin labels. The new `Integration/EngineeringReferenceTest.php` is ready for the root-owned real WordPress instance; this worker has not run writes in that shared instance. It covers read-only preview, initial native Woo migration, all 30 bound fields/two documents, native purchasing and Store API, label/text identify, stale draft pruning, idempotence after Woo editing, reversible withdrawal, same-URL replacement and missing required inputs, explicit re-confirmation, final relation removal and ordinary dependency validation. Real WordPress results remain pending the root integration run; unit success does not substitute for that gate.

The three new admin labels use the approved German wording: `Engineering role` → `Verwendung im Systementwurf`; `Reference PV module` → `PV-Referenzmodul`; `Engineering ID` → `Referenzkennung`. `Product` reuses the existing translation. The narrow POT/PO update and compiled MO are included. No customer layout or design changed. Resource inventory is unchanged: the existing single source worktree is retained for review; publication614 remains owned by the root integration task. No new backup, instance or worktree was created.
