# #254 acceptance on c254

Implementation only: `/Users/chesterjohn/Documents/de-linker-worktrees/c254`, branch `feat/254-german-urls`, instance **http://127.0.0.1:9129**. The main checkout was not used for edits. No merge, deploy, production write or real test email was performed. Claude owns the production handoff.

Snapshot **20261018-1043**, taken **2026-10-18T02:52:16Z**, loaded **2026-10-18T02:54:26Z**. [Snapshot readback](snapshot.json). Do not re-sync merely to repeat the tests: they restore their fixtures/options/tasks themselves.

- [Complete route/status/title table](completion.md) and machine-readable [route results](route-results.json).
- [Discovery and every English segment](inventory.md), [crawl responses](live-crawl.json), [all sitemap XML](live-sitemaps.json), exact [crawl input](discovery-input.json) / [sitemap input](sitemap-input.json).
- [Public red → green evidence](red-green.md), [title copy review](copy-review.md), [Spec/Standards reviews](review.md), [legacy absence](legacy-absence.json).
- [Selected prototypes and approved increments](prototype-comparison.md).
- [English pixel results](pixel-results.json), [approved visual changes and fixture disclosure](change-ledger.md), full EN before/final and DE/state PNGs with capture manifests.
- [Production dry run, apply, verification and rollback](production.md). The read-only Apify script was exercised against the still-original production addresses: [probe result](readback-probe.json). These pre-deployment results are not claimed as post-deployment acceptance.

The verified code commit and the final command/JUnit results are recorded in [verification.json](verification.json). [Full just check output](checks/just-check.log) and [just test output](checks/just-test.log) preserve the current-source command records. Default skipped integration suites are not acceptance: the explicitly enabled c254 commands below produce the JUnit records.

```bash
just check
just test

LINKER_I18N_SITE=http://127.0.0.1:9129 \
LINKER_I18N_WP="$PWD/docs/acceptance/2026-10-18/254/wp-c254.sh" \
LINKER_254_EVIDENCE_DIR="$PWD/docs/acceptance/2026-10-18/254/mail" \
/opt/homebrew/opt/php@8.3/bin/php plugins/linker-i18n/vendor/bin/phpunit \
  -c plugins/linker-i18n/phpunit.xml.dist --testsuite integration \
  --filter 'GermanUrlsTest|JournalTitlesTest' --log-junit /tmp/254-german-urls.xml

LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/c254/wordpress \
/opt/homebrew/opt/php@8.3/bin/php plugins/linker-commerce/vendor/bin/phpunit \
  -c plugins/linker-commerce/phpunit.integration.xml.dist \
  --filter 'OpenInquiryTest|BlogSingleFaceTest' --log-junit /tmp/254-inquiry-reader.xml
```

Each integration command is run twice consecutively on c254. The URL suite uses only HTTP, public WP-CLI and captured mail; native CLI APIs prepare owned users/products/orders and restore them. It verifies dry run, occupied/unreviewed fields, first-backup protection, 0-change repeat, rollback, stale rewrite cache, original bootstrap retirement, source save and `present` persistence, reset keys, recipient-language staff/cron mail, real inquiry details and native logout nonce validity.

Mail stays local. `mail/approval.eml` is one tester delivery; the queue JSON files prove additional frontend/staff/cron routing and links. Synthetic keys/nonces are redacted in committed evidence. No production mail test is part of the runbook.

The mail attachment retains native UTF-8/8bit bytes. A final artifact check caught redundant quoted-printable decoding in the test harness; this was removed and the native transfer-encoding header plus UTF-8 validity are now asserted before evidence is saved. Business mail generation did not change in that correction.

For full read-only c254 consumer verification, first create/reuse the guarded `visual-account.php` fixture and generate its native logged-in cookie into an uncommitted local file. Then run:

```bash
python3 docs/acceptance/2026-10-18/254/audit.py --cookie-file /tmp/254-owned-cookie
python3 docs/acceptance/2026-10-18/254/pixel-compare.py
```

The audit checks every reviewed old/new response, actual titles, internal links, canonical/hreflang/share metadata and all native sitemap children. The English sitemap path set is compared with the saved live XML. Logout is a native action (301 compatibility → 302 transition → German account); it is not a separate document. Polylang's native paged-hreflang omission is retained; page-number and language-switch links are tested over HTTP.

Computer Use uses the same in-app browser at **1440×900** and **390×844**. It loads the pinned main source baseline and final source sequentially in this same c254 worktree, with byte-preserving source restoration, native `present` and native WindPress Generate between them. The local-only fixture makes native images eager, waits for fonts, native image decoding, two paint frames and the paused first video frame, then captures from scroll position zero without preparatory scrolling. Dimensions, language, title and media readiness are recorded. The metric captures use the same tab's native CDP PNG screenshot command (scale 1), with format assertions; the default browser API returns lossy JPEG and is not used for pixel proof. There are no presumed dynamic masks. The owner-authorized product, inquiry, blog index, blog category and service faces are recorded as visual changes. The other nine EN page types at both widths produce 18 whole-page comparisons with exactly zero changed pixels. No masks or tolerances are used. The separately authorized reader and search designs have their own EN/DE desktop/mobile screenshots and native-action records in design-layouts.json. Missing-image/spinner preliminary captures were rejected.

Visual states use guarded local fixtures only. `visual-fixture.php` is temporarily copied to c254's mu-plugins directory, then removed. `visual-account.php` creates only the marked synthetic customer; `visual-orders.php` creates only marked EN/DE inquiry records for native confirmation URLs. After native logout, pass those order IDs to `visual-cleanup.php`; it verifies ownership before removing them and the marked customer. The error screenshot opts into `?i254-visual-state=error` to seed the existing session flash; real submit/validation behavior is verified separately by OpenInquiryTest.

The final design details are shown by [desktop cards](visual/journal-cards-en-1440.png), [German mobile discovery](visual/journal-platform-de-mobile.png), [desktop reader](visual/reader-en-desktop.png) and [share toolbar](visual/reader-share-de-1440.png). The owner supplied the preserved reference images alongside their explicit request to redesign these faces. [Actual native search / chapter / mobile service observations](design-layouts.json) record no horizontal overflow, chapter targets below the sticky header, localized searches and all four vertical service capabilities.

The final short labels and app-dashboard topic navigation follow the owner’s [density/category feedback](owner-dashboard-feedback.png). They use a native LC/Tangible post-field extension and code-published reviewed copy, with no additional database migration. The full reader/browser titles remain unchanged. The dedicated JournalTitlesTest HTTP seam verifies distinct card identities and both full reading titles.
