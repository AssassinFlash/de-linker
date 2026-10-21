# Customer evidence acceptance — in progress

Implementation issue: https://github.com/AssassinFlash/de-linker/issues/516

Fixed source base: `36dae3737e79530d7124cd8cb0e98cf70fda4961`.
The dependent inquiry-classification implementation remains in its own PR.

## Real storage evidence

- The complete focused run passed 32 tests / 227 assertions on the loaded
  `g516` instance using HPOS, and separately on `g516classic` using native classic
  orders. The latter is a pipeline fixture only; UI acceptance uses `g516`, which
  has the live theme/uploads snapshot.
- New fixtures exercise frozen acceptance data, exact VAT provenance and
  contradictions, model-input separation, actual Sender submission with quoted
  text/backslashes, repeated correction, withdrawal, original legacy stamps,
  rejected stale edits, rejected nonce/permission, a failed private-event write,
  a second real MySQL connection, native Woo privacy export/removal, and no extra
  mail/status changes. The existing inquiry-assessment lifecycle is included.
- Anonymization suite: 21 passed. New private event payloads are emptied in
  comment metadata; generic Woo note text contains no submitted customer text.
- All fixture recipients use the existing tester isolation. No production mail,
  account action or model call was added by this feature.

Reproduce each real-storage run from `plugins/linker-commerce`:

```sh
LINKER_WP_ROOT="$HOME/de-linker-local/g516/wordpress" \
  php vendor/bin/phpunit -c phpunit.integration.xml.dist \
  --filter 'CustomerReviewTest|CustomerEvidenceTest|InquiryAssessmentTest'

LINKER_WP_ROOT="$HOME/de-linker-local/g516classic/wordpress" \
  php vendor/bin/phpunit -c phpunit.integration.xml.dist \
  --filter 'CustomerReviewTest|CustomerEvidenceTest|InquiryAssessmentTest'
```

## Native-store repair found by the fixtures

WooCommerce 11.2.0 `WC_Data_Store_WP::add_meta` calls `wp_slash` only for string
values. WordPress `add_metadata` recursively unslashes arrays. In contrast,
`update_metadata_by_mid` and HPOS preserve the array values. The first classic
write of a staff note with backslashes therefore failed the canonical readback.

`StructuredMeta` compensates only when a structured key is first added through
the actual classic data store; later updates and HPOS retain their native input.
The caller reloads saved metadata before consuming it. This preserves the array
schema and keeps existing notification/recovery readers compatible. The same
first-write protection covers the accepted provider snapshot and local evidence.

## Remaining gates

`just check` and `just test` completed successfully. The latest focused PHPStan
and PHPCS runs also cover the final missing-account safeguard. Final EN/DE
Computer Use at 390/1440, fixed-diff Spec and Standards review, PR and CI remain
separate gates. No merge, deployment or
production activation has occurred for this implementation. The 29-case research
matrix remains the acceptance boundary; test counts alone do not prove every
rendered or operational case.
