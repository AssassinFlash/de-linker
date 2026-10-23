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

The first combined native run had 20 tests / 129 assertions with three failures and one downstream error. Two were the native hook above. Saved-solution transport fixtures lacked the local service token and, for guests, the browser cookie after PHPUnit had sent output. A later combined run exposed an older test's HTTP transport leaking into the following saved-solution case; its cleanup now removes that exact callback. Services were started through the native local runner and the guest fixture supplies/restores its synthetic browser cookie. The corrected combined native run passed **24 tests / 231 assertions**; the original failing runs are not counted as passes.

FAQ output now uses the single cited, byte-bound field in both the public product ability and the library. Singular and ACF editorial metadata remain stored; neither is an alternative permission source. Native fixtures cover EN/DE answers disappearing with replaced bytes while the records and files remain present.

Engineering receipts require contract version 2 and explicit reference-input dependencies. Ordinary signed Genie product lists retain their separate contract. A native admission fixture exposed that replay initially applied the engineering marker to Genie too. The repair stores the consumer as trusted server metadata, separate from browser JSON, and retains fresh Woo checks for both. The complete native resource-admission suite passed **28 tests / 535 assertions**, including genuine REST Genie add/save, completed retries, completion lifetime and refusal after a product becomes draft. Tools full unit **313 tests / 2,437 assertions**, full PHPStan and changed-file WPCS passed.

Reference migration's real Woo fixture first failed because Woo 11.2 immediately restores its default category after `set_object_terms([], product_cat)`. The fix uses native relationship unlinking and reference-only hooks while retaining ordinary products' default-category behavior. The corrected native reference suite passed **2 tests / 63 assertions**, including all 30 figure fields, two documents, Store API/purchasing exclusions, idempotence, withdrawal and same-URL byte replacement. The actual local CLI preview and write then created reference record **8369**, preserving the existing 30 facts and two files. No production reference has been created yet. Runtime feed generation reads Woo, and the former engineering JSON is only a one-time migration input. Reference revisions are independent dependencies, so a changed reference does not invalidate a calculation that never used it.

The knowledge-scope repair's cached-corpus measurements are partial acceptance evidence: 793 authorized chunks from 76 document hashes, 69/85 products with at least one safe passage, and zero releases among 1,817 chunks containing actual unavailable models. An initial twelve-query BM25 comparison still regressed from seven expected-page hits to two; original quality parity is not proven. Joint passages now require a complete recorded group of explicit document/product/revision bindings; content SHA cannot replace any revoked identity. A current three-model datasheet whose authored column header was separated from its parameter table is being repaired using original table structure. A different G10 association pointing to G11 content remains rejected. Preparation completeness remains false and missing associations stay visible.

The final reference suite subsequently passed **4 tests / 98 assertions**, including deliberately different native term IDs and term-taxonomy IDs, plus actual derived metadata normalization. Independent Spec and Standards delta reviews through `5e0eb990` closed the source findings without claiming the remaining runtime gates.

Actual HTTP engine preparation then completed claim, full schema load, engine-only restart, process readback and accepted Woo acknowledgement for source `04a8e966a46143279a81c6db3b30bbc1df45252a4f83aa8d1cc61c4339c41268`. Runtime version `156be14b796a2db747dc1626e72eadab82ffc7396a6d09c3922d08489a0f9e62` reports **86 prepared records: 85 supply products and reference 8369**. Residential calculation returned 200 with GW10K-ETA-G20 and complete reference/dependency proof. Hand-drawn roof packing returned 200, 21 modules / 9.66 kWp, with its one reference and two current document dependencies. The first automatic outline request is still waiting on its external building-data first download; a subsequent request correctly returned busy, and neither is counted as an outline pass.

The first PR CI run caught two fixture style errors and a real event-scope defect: a private reminder's metadata write queried the unrelated publication scheduler, consuming the mail fault fixture's first query. An independent read-only differential reproduction confirmed the root cause. It also proved that directly registering void `changed()` on the native `wp_update_attachment_metadata` filter could replace its array with null. This phase-two code has not been deployed. The repaired module observes persisted metadata actions, filters source IDs and taxonomies, and preserves attachment filter values. Actual WordPress regression plus the unchanged reminder cases passed **13 tests / 86 assertions**; the new metadata preservation cases now run in CI. No existing reminder assertion was weakened.

## Visual observations so far

Computer Use inspected the actual snapshot-backed site at EN/DE and 1440/390. The library FAQ and document lists retain their layout and other brands. Typing EcoFlow produces zero FAQ and zero document results in each language and width. Configurator input views and historical-account views were also captured in both languages and widths. Screenshots are in `screenshots/`.

A local-only historical fixture (**8413**) belongs to the local administrator and references a preserved draft EcoFlow product. This is synthetic acceptance data, not a production customer's design. Actual LiveCanvas rendering initially read the current product name despite the native Woo fallback already using stored history. The account data adapter now uses `historical_items()` too. A real page reload showed `EcoFlow Recorded model at save`, with the original stored record unchanged. Computer Use downloaded its owner-gated report successfully and verified `%PDF-1.7`; `history-report-fixture.pdf` is that small synthetic downloaded artifact. These observations do not claim remaining configurator result/withdrawal or Genie frontend action-state acceptance.

## Remaining gates

- Complete reference migration and knowledge-applicability fixes, then review their complete delta.
- Two-process withdrawal/cache regression, actual knowledge build/index loading and automatic queue acknowledgement, and the automatic roof-outline result. The initial engine schema failures were repaired and its actual preparation chain subsequently passed; production still requires its own readback.
- Required configurator, Genie and historical action states, EN/DE at 1440/390.
- Committed build verification, CI, full Spec/Standards closure and review-station acceptance.
- Necessary production recovery point, atomic deployment, stable workers and actual runtime/loaded-source readback, followed by phase-one controls and bounded resource cleanup.

No phase-two code or data has been deployed in this record's current state.
