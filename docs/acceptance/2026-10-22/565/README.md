# #565: native administrator MFA, customer access preserved

Branch `codex/565-admin-mfa`, implementation base `1f054757`.
[Spec](../../../specs/565-admin-mfa/README.md) ·
[dependency installation and owner handoff](deployment.md) ·
[native German notice copy review](copy-review.md).

## Result and scope

The official free **Two-Factor 0.17.0** runs on this site's real snapshot with
WordPress7.1.3, PHP8.3.35, Woo and the existing account forms. Native wp-login and
Woo administrator authentication require the configured per-user factor. Ordinary
and pending customers have no registered factors and gain no MFA screen. No
production authentication bridge, public-page layout/style or customer copy was
changed.

This is **local engineering preparation**. No production plugin installation,
real TOTP/recovery enrolment, password/role/session change, API revocation or
Hostinger security change occurred here. Production activation is incomplete
until the owner registers and verifies their own factors on their own device.

## Environment and provenance

- Exclusive native `m565`, `http://127.0.0.1:9332`; production snapshot
  `20261022-1653`, taken08:56:45UTC, loaded11:53:45UTC on2026-10-22. Snapshot theme,
  uploads and LiveCanvas/WindPress presentation were loaded before UI testing.
- Native web php.ini memory2048M; WP-CLI runtime unlimited. Engine/Genie services
  were not started. Local mail capture and WordPress HTTP isolation stayed on.
- Official stable plugin archive SHA256
  `4d1b0f8e5d82e24876c2b4e86f119122e28a8dbaf76dfde495173226c3356f37`;
  WP-CLI strict official file checksum verification1/1 PASS.
- Official formal German archive SHA256
  `8d5e133f7ef0697f6f8c48a240ff8a078702bda97bc39eac5fc98fe6da9c318c`.
  Archive bytes and the exact three language filenames are verified before
  extraction. One missing administrator notice is merged with native gettext;
  vendor source remains unchanged/checksum-valid. Actual singular and plural
  German notices were then observed in CUA.
- Direct extraction initially left Redis's `translation_files` directory index
  stale. Dependency preparation now performs the exact narrow invalidation used
  by the native language upgrader. No global cache or quota journal is flushed.

See [provision readback](evidence/provision.sanitized.json) and
[final dependency readback](evidence/dependency-final.json).

## Native authentication and customer regression

[`just admin-mfa`](../../../../tools/checks/admin-mfa.py) creates disposable local
identities and uses real HTTP forms/cookies, native WordPress sessions and
Two-Factor provider methods. It refuses a non-native/unisolated target or a
Commerce checkout it does not own. Secrets, cookies, reset tokens and bodies are
never included in the public result.

The enforce run passed **36/36** checks, including actual same-origin reset
prepare/verify and signed proof consumption:
[raw sanitized result](evidence/native-enforce-final.json). The final ordinary
native run additionally follows the actual captured/queued customer reset link,
submits a new synthetic password and verifies login with that password, also
**36/36 PASS**. The two runs cover **40 distinct assertions**; repeated checks
are not added together. See [final result](evidence/native-final.json).

| Boundary | Actual assertion |
|---|---|
| TOTP setup | Invalid setup code refused without usable factor; valid native setup accepted |
| Unfinished administrator auth | Correct password → challenge, no logged-in cookie, zero authenticated sessions, protected Profile unavailable |
| TOTP success/error/replay | Wrong code creates no auth; correct code reaches Profile and records `two-factor-login`; same TOTP rejected on replay |
| Recovery | Native code logs in once; remaining codes10→9; used code refused |
| Woo account login | EN and DE administrator passwords stop at factor; valid native TOTP/recovery completes login |
| Existing customers | Approved and pending users, EN and DE, log in without a factor; native per-user configuration remains false |
| Reset | Native EN/DE reset request works without TOTP; same-origin protection remains real under enforce; final native reset completion/new-password login also works |
| API boundary | Ordinary administrator password fails REST; synthetic application password still authenticates the same user separately |

An early HTML parser edit accidentally referenced start-tag-local `values` from
`handle_endtag`; Ruff caught it before commit. It was removed. Actual account,
reset and factor pages containing normal `</a>` tags subsequently passed the
native harness, rather than relying on a static syntax check.

The reset-completion extension initially selected a captured reset link whose
page had no password form. The fixture's fallback could choose an already-used
historical email before the current one. It now validates the captured/queued
candidate with native `check_password_reset_key()` for the owned synthetic user
before returning it; it does not create a replacement token or bypass validation.
A focused EN/DE native completion passed. The first failing URL was not retained,
so the precise historical candidate cannot be reconstructed. This test-selection
fix changes no application reset behavior.

## Actual browser cases, EN/DE ×1440/390

The `screens/` files are CUA captures from the actual snapshot. Width changes
check readable layout and the native interaction states; no CSS or existing
page composition changed, and no new whole-site pixel-parity claim is made.
`evidence/screenshots-sha256.json` lists all82 captures. The long synthetic
email on the DE390 inquiry confirmation is not wrapped and reaches the right
edge; this inherited customer-surface limitation is recorded, not attributed
to MFA or called pixel-perfect acceptance.

| State | Browser evidence |
|---|---|
| Admin factor / incorrect code / recovery input | `en-*admin-{factor,invalid,recovery}.png`, `de-*admin-{factor,invalid,recovery}.png` |
| Missing DE vendor notice fixed | `de-*admin-warning-translated.png`, `de-*admin-recovery-translated.png`; singular and plural actually rendered |
| Customer login under enforce | EN approved account `en-*customer-enforce-signed-in.png`; DE pending account `de-*pending-enforce-signed-in.png` |
| Registration under enforce | Two-step EN/DE forms create pending accounts directly: `*-registration-enforce-complete.png`; native user has no factor |
| Reset under enforce | EN request succeeds; DE outage preserves input and displays retry, then the same page succeeds after recovery: `*-reset-enforce-*.png` |
| Guest contact/inquiry | Actual native confirmations under enforce: `*-contact-enforce-sent.png`, `*-inquiry-enforce-sent.png`; no account/TOTP |
| Verification outage contact | DE `*-contact-outage-review.png`: native record8239 saved awaiting staff review, no confirmation email claim |

The normal enforce records are contact8227/8230 and inquiry8233/8236, all
`customer_id=0`, `inquiry-received`, no review hold, native Ledger completed with
the matching order outcome and **one consumed verified parent** each. Outage
record8239 has the same completed native business association, review hold true,
and zero consumed successful verification parents. Native data is in
[evidence/cua-native-final.json](evidence/cua-native-final.json). A302/HTTP200
alone was never counted as accepted submission.

### Bounded negative findings

The initial mode-off experiment used the preserved legacy shared connection
limit3/UTC-hour. Two registrations plus one EN contact spent that bucket in the
12:00–13:00UTC window; DE contact was then refused. A fresh cookie jar on the
same connection at12:32:42UTC reproduced the refusal without an MFA challenge.
The red screenshots remain `de-*contact-rate-limit.png`. This is a quota result,
not an MFA regression. ReceiptLimit is separately the customer-receipt budget.
No ledger was reset or policy relaxed to make the tests pass.

For the current combination, only an exact-instance temporary MU loader enabled
`enforce`+`required` with official synthetic test keys. The local fixture replaced
the challenge SDK and canonical siteverify transport, including explicit outage;
it did not replace Identity, prepare/verify, proof signatures, Ledger, preflight,
reservation, dispatch or Woo storage. Jev was disabled only for this fixture's
lifetime; no paid model or real mail was called. This proves integration around
the provider, not real Cloudflare network availability or CAPTCHA usability.

Two early UI inquiry attempts initially stayed on the form with no visible
failure; their local server log contains no admin-post until a subsequent click.
Exact cause is unproven. Two fresh controls with unchanged Two-Factor+enforce,
the same field-filling/semantic-click procedure and temporary non-value DOM
click/submit/invalid instrumentation succeeded on the **first** click: EN1440
record8252, DE390 record8255, one native record each. The observation was not
reproduced; this evidence does not establish a causal MFA defect or guarantee
all first clicks. No speculative product patch was added.
[Bounded control](evidence/inquiry-click-control.json).

## Mail and cleanup boundary

Two early password-request messages were captured as local `.eml` files; both
had exactly the single tester recipient and no Cc/Bcc. Later native fixture
messages could remain in Outbox because snapshot delivery budgets were preserved.
Readback of two final queued reset jobs showed all original recipients synthetic,
and native TestMode projection exactly one tester with no Cc/Bcc. See
[mail isolation evidence](evidence/mail-isolation-final.json). This is neither
external delivery nor an inbox-receipt claim. There was no test SMTP/model send.

After verification, the exact-instance MU loader, mode file and temporary DOM
instrumentation were removed; synthetic users/factors/application passwords,
tracked fixture inquiries/jobs and private disposable browser input files were
cleaned. The original local mode was restored, local isolation retained and the
native quota journal preserved. Viewport override was reset and the owned browser
tab closed. Official Two-Factor remains locally installed, with **no remaining
synthetic users**; [cleanup readback](evidence/cleanup.json).

## Verification and release gate

Targeted Ruff, formatting, strict mypy, both PHP fixture lint/PHPCS and gettext
format compilation pass. The native suite is wired into the existing isolated
`mu-smoke` CI job after its EN/DE setup. CI on a bare fixture is distinct from
this live-snapshot UI acceptance. Independent full-diff Spec/Standards review
and CI are coordinator gates after the review-ready commit/PR; this record does
not mark them passed in advance. No merge/deploy is performed by this branch.
