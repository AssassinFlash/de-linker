# Shared public admission acceptance

Issue #519; map #505; PR #523. Source head `066b37357d4a3f558b662b8a863ae774cb46c0a6`
(code at `36f9535f07ff8ad6b0e9066d7eddfde647c9f450`, then CI-only registration).
Base `4f722c2636a61861c74e1a39b58350c0c218af3d`.

## Verification

- Complete `just check`: exit 0 after the review repairs, including all plugin
  PHPCS/PHPStan, JS lint/types, Python checks, German coverage/copy, internal URLs,
  catalogue validity and build/source manifest reproduction.
- Complete `just test`: initial complete run exit 0. A final full run after all
  review repairs is recorded in the PR/CI readback before ready-for-review.
- Latest real WP/Woo integration: `LINKER_WP_ROOT=…/g519/wordpress php
  vendor/bin/phpunit -c phpunit.integration.xml.dist --filter
  'PublicControllerTest|PublicLedgerTest|PublicVerificationTest|PublicProofTest'`:
  **37 tests, 218 assertions, pass**.
- Shared browser client: **5 tests pass** for lazy interaction, concurrent proof
  reuse, pretty/query REST URLs, preserving input on failure, expiry and recovery
  after a provider-script error. Types and JS lint pass.
- Live-pull anonymization fixture: **19 tests pass** in the full suite. The new
  private journal option is omitted from pulled production snapshots.
- Native PO/MO plus WP-CLI `make-json --no-purge`; Commerce German gap 0.
- The four real WP protection fixture classes run in CI's existing `mu-smoke`
  WordPress/MySQL environment. No external model or mail is invoked.

Critical real fixtures cover multi-dimension all-or-none reservation, stable UUID
replay/changed payload, single business proof consumption, no successful dispatch
without a completed Siteverify receipt, pre-dispatch refund versus post-dispatch
spend, actual lease recovery time, browser/account carry, corrupt journal failure,
account/recipient privacy and erasure racing with late completion. A real second
DB connection kills the first after its journal snapshot, wins the last allowance,
and verifies wpdb's reconnect cannot overwrite it: stale writer unavailable,
winning peer retained, next admission denied. Native privacy also covers signed-in
verification-only successful and failed visits without a business submission.
Observe tests retain shadow accounting and refusal/retry reasons while quota,
identity or storage trouble does not block the original business flow.

## Computer Use

Instance `g519`, WordPress `127.0.0.1:9281`, engine/genie 9282/9283; live
picostrap/theme/uploads snapshot `20261022-0018` loaded before UI work.
No bare WordPress UI is used as the design reference.

Actual native Woo admin and the production shared client were driven with
Computer Use at 390px and 1440px in English and German formal. Selected evidence
in `screenshots/` covers off/not configured with the disabled diagnostic,
configured dummy-key success, provider failure, direct retry success, and final
per-dimension remaining/reset plus admitted/replay/quota diagnostics. Final
390px and 1440px DOM widths equal the viewport (no horizontal overflow).

Network observation of passive reload: **zero Cloudflare responses**. A diagnostic
click makes prepare, loads the official explicit widget, and verifies through the
same REST/controller/journal as future native consumers. The button performs no
business write, model call or mail. No real CAPTCHA was solved for these dummy-key
fixtures.

Real network versus fixture distinction:

- The official public dummy secret's real network Siteverify result succeeds for
  its fixed `example.com` test hostname, omitting a real production action. The
  strict application correctly rejects the hostname mismatch. This is not a
  successful de-linker.com production verification.
- UI success and outage/retry use an explicitly local-only HTTP fixture restricted
  to the fixed official endpoint and exact public dummy secret. It short-circuits
  synthetic response states; it is not production code and cannot accept a live
  secret. The real dummy widget script/iframe load was separately observed.
- The local acceptance helper temporarily allowed that fixed dummy-key HTTP call
  past local isolation; mail isolation and all other destinations stayed intact.
  The temporary helper was removed, original wp-config restored byte-for-byte,
  and staff locale restored to the original English default after capture.

The five verification receipts plus one synthetic shadow receipt remaining on
this isolated local instance are test evidence. No customer inquiry was created.

## Release boundary

Default mode off. No native business/resource consumer is claimed connected by
this PR; the health page says so. #520/#521 attach actual doors; #522 owns the
combined real-entry matrix, backup/rollback, production configuration and readback.
No production deployment, key installation, DNS operation, purchase, attack probe
or real test mail occurred in #519. The previously authorized production Turnstile
pair remains only in the user's private config outside Git.
