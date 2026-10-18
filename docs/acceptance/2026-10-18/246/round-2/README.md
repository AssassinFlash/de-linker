# #246 / PR #290, review round 2

The round-1 implementation is accepted by [Claude's round-2 review](https://github.com/AssassinFlash/de-linker/pull/290#issuecomment-6240929308). This continuation addresses the atomic connection limit, a separate site-wide receipt allowance, fresh-cookie guest submissions, and the optional-name interface needed by #243. Worktree and local instance: c246 only.

## Accepted pixel gate and reproducible capture method

Claude recaptured live vs c246 at feature head `51e27285`. The full contact page, with **no mask and no tolerance**, passed every language/viewport pair:

| Language / width | Live vs c246: differing pixels | Live repeat control |
|---|---:|---:|
| EN 1440 | 0 | 0 |
| EN 390 | 0 | 0 |
| DE 1440 | 0 | 0 |
| DE 390 | 0 | 0 |

Method recorded by Claude: a fresh browser context for **each capture**, the same Chromium on the same machine, identical viewport, animations disabled, all images forced eager and decoded before capture, and each image wait bounded to five seconds. Repeating the same live URL also gave zero differences. This evidence supersedes round-1's unresolved photo/anti-aliasing residuals: those came from the earlier capture method, not the site.

`tests/visual/pixel-parity.mjs` is absent from the rebased `origin/main` (`0a239ae2`); the review says #229 will supply it. The method above is retained here so the gate does not depend on the absent shared script. These are the reviewer's measured results, not a claim of a new capture by this continuation.

## Implementation and TDD evidence

- **Atomic connection allowance:** commerce owns `Inquiry\RateLimit`, using the same conditional `UPDATE` technique as #235. Both handlers validate fields/bot checks and reserve one of three slots in the fixed hourly window **before** Sender writes. There is no commerce → tools dependency. Eight simultaneous PHP requests previously passed together; after the fix exactly three pass, creating three inquiries and six Outbox rows. The other five create no mail. See [red](atomic-red.txt) / [green](atomic-green.txt), `PublicSubmissionTest::test_parallel_public_requests_accept_exactly_three_and_queue_no_rejected_mail`.
- **Site-wide customer receipt cap:** ten per UTC day, a chosen tenth of the sourced shared Hostinger 100-mail/rolling-24h allowance (AGENTS §4; `docs/research/2026-10-09/mail-root-cause.md` §3, §9), matching #235's small allocation. The fixed day window is explicit; it does not measure the host's rolling usage. Sender atomically reserves before the status notification. At exhaustion it saves `_linker_receipt_skipped=daily_cap`; the record reaches `inquiry-received` and the team mail still enters Outbox. Only the customer receipt trigger is omitted. Both doors are covered by [red](receipt-cap-red.txt) / [green](receipt-cap-green.txt), with team To asserted from `Options::notify_to()` and the customer row absent.
- **Truthful EN/DE success state:** reviewed copy discloses the omitted receipt and keeps the one-business-day reply promise. Visual review caught the existing mobile CSS hiding `.linker-next-steps`; [the visibility regression](mobile-notice-red.txt) records it. The disclosure now lives inside the LC success panel, and WindPress `empty:hidden` removes its empty paragraph for normal receipts. PHP supplies data only. This extra visible sentence in the capped state is the round-2-required change; ordinary contact/form geometry is unchanged.
- **Fresh-cookie submissions:** real Chromium contexts start with no cookies, render the form with **no Woo session cookie**, then add a product in another request to establish that cookie before submit. Both contact and Proforma requests submit successfully as customer ID 0. Contact retains a zero-item record; the request carries the current draft product. The guard did not fail this transition, so the existing nonce signature is retained under the user's conditional HMAC instruction.
- **#243 interface:** `Submission::from_handoff()` validates reply email/message/consent with optional name and feeds the existing `Sender::message()`. Visible forms still require a name. Nameless receipts use “Hello,” / “Guten Tag,”; team subject/body fall back to the actual reply email. [Corrected red](nameless-copy-red.txt) / [green](nameless-copy-green.txt) exercise the real queued letters. No Genie hand-off transport or conversation attachments were implemented.

[Copy draft → adversarial review → EN final / independent DE](copy-review.md) · [Standards and Spec reviews, including resolution of the optional-name finding](review.md).

## Local verification

Rebased onto `origin/main` **`0a239ae2`**, preserving upstream #242 account-aware price reasons and #297 internal SMTP routing. Commerce catalogs were regenerated from current sources with `just i18n-commerce c246`, with no manually merged POT retained. [Coverage](i18n-coverage.txt) has gap 0 for all domains; [generation](i18n-commerce.txt).

`just sync c246` loaded snapshot **20261018-0923**, taken **2026-10-18T01:34:35Z**, and applied local licences. Branch LC presentation was applied and WindPress compiled through its admin: cache **683,654 bytes**. The browser matrix below was rerun after sync, rebase and compilation.

| Check | Result / evidence |
|---|---|
| `just check` | PASS, exit 0; [output](just-check.txt), WPCS + PHPStan level 8, catalog validity/coverage and build/source parity |
| `just test` | PASS, exit 0; [output](just-test.txt), commerce unit configuration 1,179 tests / 5,460 assertions / 112 skips; JS 141 + 6, browser 9; Python suites green |
| Real c246 integration, repeated | Both runs 117 tests / 1,232 assertions / nine existing HTTP-fixture skips; [run 1](integration-1.txt), [run 2](integration-2.txt); every new public-submission case executes |
| Fresh-cookie browser matrix | 16 cases: EN/DE × 1440/390 × contact/request × receipt/capped; [output](browser.txt), per-case screenshots and queue readback JSON below |
| Receipt routing and omission | Normal state: one team row + one customer row. At cap: one team row, no customer row, one received record. Readback JSON retains intended routing; mail transport stays local |
| Reviews | Standards 0 hard / 0 actionable smells; Spec's one optional-name finding resolved; [review](review.md) |

The post-sync full integration run initially exposed an extensible digest-list assumption and two diagnostic fixtures using raw WordPress locale switching after a commerce domain reload. The tests now check the existing digest prefix and use the real flow's `LocaleSwitch`. [Initial failures](integration-before-fixture-fixes.txt) and the two green full runs are retained; no SMTP production behavior or settings changed.

## Browser evidence

Each test asserts empty initial cookies, no Woo cookie after render, a Woo cookie before submit, a guest-owned received record, expected product count, queue recipients/count, visible receipt disclosure when capped, and no horizontal overflow. Captures wait for fonts, force images eager/decode with each wait bounded to five seconds, and disable animations. JSON next to every PNG contains cookie-name transitions and synthetic order/Outbox readback.

| Language / viewport | Contact capped | Proforma request capped |
|---|---|---|
| EN 1440 | [Screenshot](guest-en-1440-contact-capped.png) · [queue](guest-en-1440-contact-capped.json) | [Screenshot](guest-en-1440-request-capped.png) · [queue](guest-en-1440-request-capped.json) |
| EN 390 | [Screenshot](guest-en-390-contact-capped.png) · [queue](guest-en-390-contact-capped.json) | [Screenshot](guest-en-390-request-capped.png) · [queue](guest-en-390-request-capped.json) |
| DE 1440 | [Screenshot](guest-de-1440-contact-capped.png) · [queue](guest-de-1440-contact-capped.json) | [Screenshot](guest-de-1440-request-capped.png) · [queue](guest-de-1440-request-capped.json) |
| DE 390 | [Screenshot](guest-de-390-contact-capped.png) · [queue](guest-de-390-contact-capped.json) | [Screenshot](guest-de-390-request-capped.png) · [queue](guest-de-390-request-capped.json) |

Corresponding `*-receipt.png` / `*-receipt.json` files show ordinary receipts for every row. Computer Use in Chrome additionally inspected the contact success notice; full-page image review found and then verified the corrected mobile Proforma disclosure.

The fixtures restore their options and limits, delete their synthetic inquiries/products, remove their Outbox rows and unschedule their retries. All delivery is a local file or test-owned loopback SMTP sink; no real mail is sent. Manual site work used c246 only. No deployment, merge or production write occurred. Remote CI and hand-back are recorded in the PR verification comment.

Rollback: revert the round-2 commits and run the normal LC/WindPress presentation path in the target environment. Counter rows are non-autoloaded options under `linker_commerce_limit_`; old fixed windows are pruned on takes. No production migration or irreversible deletion is part of this branch.
