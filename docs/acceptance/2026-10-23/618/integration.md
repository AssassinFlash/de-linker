# Unified publication integration

This is the integration record for [migration, full-chain acceptance and deployment](https://github.com/AssassinFlash/de-linker/issues/618), under [the EcoFlow withdrawal map](https://github.com/AssassinFlash/de-linker/issues/607). Pending gates below are not production acceptance.

## Preserved production baseline

The phase-one protection remains in production. A fresh SSH readback confirmed **68 product records present, all draft; 49 protected original paths present, none missing; 48 distinct content hashes**. The private evidence is `~/de-linker-data/ecoflow-withdrawal-20261023/phase2-preservation-readback.json`. Products, media records, original PDFs and customer-owned history are preserved. The separate security task's Genie entry block and the existing emergency PDF rules are retained.

The current production LiteSpeed Cache plugin is inactive, confirmed through native WP-CLI. This is an observed current state, not a guarantee about a cache enabled later.

## Integration environment

One previously owned instance, `publication614` on `127.0.0.1:8888`, is reused with this worktree's plugins. The verified `20261022-2309` site snapshot supplied the actual theme, uploads and templates; local-only phase-one draft states were then applied. Other sessions' instances and the unified-planner worktree were not modified.

The site has 85 canonical published supply products and 142 authorized document identities before reference migration. Initial adoption was actually executed with `wp linker-commerce publication bind-figures`; it binds existing explicit Woo evidence and does not claim renewed semantic verification of every number. The engine and Genie run from this checkout at ports 8889 and 8890. Genie initially opens the existing older index; that startup alone does not constitute preparation or loaded-source acceptance.

A fresh native read measured 85 products, 142 documents, 609 SQL queries and 616,968,549 file bytes: manifest 2.833 seconds, independent file hashing 1.949 seconds, all hashes matching. HTTP later measured 3.086 seconds. Earlier 12–17 second observations coincided with machine load above 260 and are retained as failed performance observations; these different-load samples do not establish a controlled before/after improvement. Each new authority read still hashes current original bytes and refreshes request-local cache; no TTL or shared Redis flush was added.

## Review and native findings

The full Spec/Standards review at `b1e9dec0` found managed-document revival, stale FAQ byte bindings, worker startup/import and failed-build retention problems, 409/503 conflation, receipt cleanup path problems and incomplete standalone translations. Those source defects were repaired before the next full review.

The independent full-range review of `5eabfffc…1b6822ae` reported three Spec findings (alphanumeric engineering tokens misclassified as models; reference-module evidence outside current permission; raw FAQ fallbacks) and one Standards finding (the same raw FAQ consumer). Their fixes require a final delta review; the axes remain separate.

Actual native Woo fixtures exposed that `WC_Cart::add_to_cart()` does not execute `WC_Form_Handler`'s `woocommerce_add_to_cart_validation` hook. The complete-list adapter now runs that native hook and rolls back the whole operation when a later line fails. Both previously failing native rollback cases passed after this change.

The first combined native run had 20 tests / 129 assertions with three failures and one downstream error. Two were the native hook above. Saved-solution transport fixtures lacked the local service token and, for guests, the browser cookie after PHPUnit had sent output. Services were started through the native local runner and the guest fixture now supplies/restores its synthetic browser cookie. The corrected combined native run is pending; the original failing run is not counted as a pass.

FAQ output now uses the single cited, byte-bound field in both the public product ability and the library. Singular and ACF editorial metadata remain stored; neither is an alternative permission source. Native fixtures cover EN/DE answers disappearing with replaced bytes while the records and files remain present.

Engineering receipts require contract version 2 and explicit reference-input dependencies. Ordinary signed Genie product lists retain their separate contract. Reference-module facts are being migrated from the former engineering file into a hidden, virtual, unpriced Woo engineering reference record without a sales SKU or product category. This preserves the existing reference-only scope and the sole Woo maintenance entry; runtime feed generation must stop reading the old file. Reference revisions are independent dependencies, so a changed reference does not invalidate a calculation that never used it.

## Visual observations so far

Computer Use inspected the actual snapshot-backed site at EN/DE and 1440/390. The library FAQ and document lists retain their layout and other brands. Typing EcoFlow produces zero FAQ and zero document results in each language and width. Screenshots are in `screenshots/`. These are library observations, not yet the configurator, Genie action-state or historical-account acceptance.

## Remaining gates

- Complete reference migration and knowledge-applicability fixes, then review their complete delta.
- Corrected native Woo suites, two-process withdrawal/cache regression, loaded feed/index preparation and automatic queue acknowledgement.
- Required configurator, Genie and historical action states, EN/DE at 1440/390.
- Committed build verification, CI, full Spec/Standards closure and review-station acceptance.
- Necessary production recovery point, atomic deployment, stable workers and actual runtime/loaded-source readback, followed by phase-one controls and bounded resource cleanup.

No phase-two code or data has been deployed in this record's current state.
