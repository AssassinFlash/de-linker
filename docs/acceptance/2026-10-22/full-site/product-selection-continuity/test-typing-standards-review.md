# Test-only typing increment — independent Standards review

**PASS for the exact five-test increment from full aggregate d9876d3b to eec1822a. No assertion weakening, framework bypass or new source blocker was found.** This ruling is test-only: it does not widen an earlier product/visual/native/deployment acceptance claim.

## Exact boundary

- Historical full 31: `d9876d3b8274039718b85d605b46c0d70cccce867e30324f9d58dcd46cf417bc`, recorded in `source-integrated-files-14cb7f74.json`.
- Current full 31: `eec1822aebf838d41ae5a0b092597a20892a5b5e5de5e9b2d544254e6278b95b`.
- The **15 products remain byte-identical**, aggregate `14cb7f7438fd677721106aa37d0f6ae569e60b469240ec4fb9929feff67395e6`. Both generated catalogs and nine other test/helper files also remain unchanged. Exactly the five tests below differ.
- Independently verified every current manifest hash and both compact sorted-key JSON aggregates. Manifest file SHA-256: `90e03652cf424f556b5d4846c8d392d26fd62795682400462ef52e8d1e4cc8d9`. Current HEAD at readback: `84427eb73115a1f7c2e420775bf38c36ce932f46`; the parent clarified the updated mainline parent as `dcd5560d`, not its earlier reported parent. Rebase did not alter any of the 31 named files. The unrelated new mainline Admission/protection/generated-build integration is outside this five-test ruling; the parent owns its combined full-check and new native interaction run.
- Independent map readback: private `selection-standards-integrated/test-typing-map-readback.json`.

The full diff was read against exact historical preimages, including the untracked-origin tests rather than relying on git diff alone. The old 31-file byte set is available at:

`/Users/chesterjohn/de-linker-data/privacy-visual-20261021/selection-standards-integrated/d987-reconstructed-before-20261022T052457751696Z`

**This is an exact-byte reconstruction made during this review, not a contemporaneous d987 capture.** Neither reviewer had retained a complete old 31-file copy. The other reviewer supplied two original unchanged test copies and three minimal inverse-typing reconstructions, each strictly matching its historical manifest SHA. I independently verified all five, combined them with the other 26 current files whose bytes match the historical map, and recomputed the complete d987 aggregate successfully. The directory contains `provenance.json`, the other reviewer's five-file reconstruction provenance, the old manifest, all 31 exact files and `five-test-only.diff`. It must not be described as original-time screenshot/runtime evidence.

## Five changes

1. **ProductFiltersTest:** only whitespace alignment for the $_GET assignment changes. The array-shaped input, exact empty selection and recommended-sort assertions remain byte-identical.
2. **ContactNavigationTest:** native Location must now be a string before query parsing, instead of coercing an unexpected value. The exact special search-byte assertion remains. The array-key PHPDoc correctly reflects parse_str's possible key type without changing parsing. The six native route cases and actual HTTP→markup→Contact/language/return/alias path are intact.
3. **FamilyNavigationTest:** setup callbacks call a private live flag reader, which returns the same excluded-map value/default. They still observe mutations made after setup; no setup-time constant is captured and no guard case or normalization expectation is removed.
4. **ModuleTest:** the four hook expectations retain AnyInstance(FamilyNavigation), method, hook type/name, priority and accepted argument count. Native WP_Mock onHookAdded→with→perform records a counter for each exact match; the final assertSame requires all four counters to equal one. Missing/wrong matches do not increment; a duplicate matching registration produces two and fails. The native responder type is asserted, other registrations and assertConditionsMet remain, and no ignore/stub of the module register method is added. I read the installed WP_Mock Hook/HookedCallback/expectHookAdded implementations: expectHookAdded itself uses this same responder path with an at-least-once intercept. This is native framework use with stronger exact counts, not a replacement that approves arbitrary callbacks.
5. **ProductShortcodesTest:** only previously present query leaves are recursively encoded. parse_str produces string/array values, and the helper preserves arrays rather than casting them to a string. Newly supplied add_query_arg values continue to be inserted as supplied, retaining the already reviewed native pre-encoding contract. Expected URLs, filter/search/sort/paging assertions and consumer code are unchanged. This remains a focused test substitute; actual native HTTP assertions remain the separate evidence for URL behavior.

No test is deleted/skipped, no expected outcome is relaxed, no production implementation is replaced and no framework/type diagnostic is hidden through a new ignore. The established AGENTS.md and Fowler judgement baseline produce no additional blocking concern in this five-file test maintenance increment.

## Evidence limits

This was **read-only source/framework inspection** plus filesystem hashing, exact before-byte reconstruction and diff capture. I did not execute PHP, tests, npm, a database, a local/native instance, browser, build or production operation. The parent's reported unit **1228 tests / 6348 assertions**, native **8 tests / 464 assertions**, PHPCS and targeted PHPStan results remain parent-executed evidence. Six added native Location type assertions explain the native assertion increase; these counts are not this reviewer's runtime result or new visual acceptance.

## Exact test identities

| Repository-relative path | d987 before SHA-256 | eec1822a after SHA-256 |
|---|---|---|
| `plugins/linker-commerce/tests/php/Integration/ContactNavigationTest.php` | `1cddb1dc5d61bb7a070f20b20390d61943bc4699ea863c35ccda3903438fdecf` | `b0c9d533cde866f64eccddbab5684f1a39dbe0de58678f72c5ca9765c51e1ecd` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/FamilyNavigationTest.php` | `58055fe76cabdca3aecaf4e8c2a60b6c696005f0c9a8847fb4e481c8c48f3a36` | `9c6fe63577ef22f88323a3b5959194972324d9a85f1866a6902a51a70099fae9` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/ModuleTest.php` | `5426c00d5b56084919f081efb87b51e8efcac69599dd735c6119b79f3ccc92a5` | `433a4a148ed8a5c214cd3ebaafb260a4a566610e51bc72f90b7638696f983d40` |
| `plugins/linker-commerce/tests/php/Unit/Presentation/ProductShortcodesTest.php` | `90008cbc952ab788ab4f69c0fab415685c825a06aa501c1971a699288a4fdf38` | `c54bfa1a7f2fb64afdf72f8187da5984fcbfc1143da00645bf8caa265964f86b` |
| `plugins/linker-commerce/tests/php/Unit/Storefront/ProductFiltersTest.php` | `4842a608bc44162f462e36863ba07244fdfaa3789688559be22443ad6da5d32f` | `c740c122fc3fb38fe4df11ade0c8c088d361d719f0182808be6f2863e136bd2e` |
