# Public business guards: acceptance record

Local development on live snapshot 20261022-0018, instance g520 (WordPress 9284). No production change or external test email is represented by these results.

## Fixed-source verification

- Real BusinessAdmission fixtures cover native Woo received records, invalid proofs/nonces, retry after cart emptying, interrupted acknowledgement recovery, optional receipt caps with retained team queue, native Woo/core password reset and registration boundary, progressive login, Store API refusal and XML-RPC inventory.
- The real Woo four-argument registration hook is tested with password in its correct third position and validated email fourth; password never enters the journal. Shared policy tests cover NAT/autofill and browser-to-account carry.
- Source reviewed at 8dedcbc43f09a104d9001d11a8252ec960fcea31: both independent Spec and Standards PASS after corrections. Full `just check` and `just test` exited zero before the final narrow form-coordination delta; that delta additionally passed PHPStan, WPCS, TypeScript, ESLint, build-manifest verification, protection client 12 tests and actual shipped account-ui 17 tests.
- Real WordPress HPOS public/admission/business selection: 63 tests / 609 assertions. Classic matrix including additional native commerce cases: 70 tests / 698 assertions. Both passed. The registration fixture now creates an actual Woo customer with the real four-argument hook and verifies completion against its native user ID.

## Real browser evidence

The official Cloudflare dummy-key api.js and challenge iframe returned HTTP 200 in the real browser. Only server Siteverify replies are explicit local fixtures. The original local CSP blocked the official script; the narrow local CSP correction permits the official origin in the needed directives.

Real contact EN/DE forms: verification HTTP 503 prevented admin-post, retained input and displayed localized retry. Restoring the server fixture allowed retry without refilling. Native readback found exactly orders 8069 (en_US) and 8070 (de_DE_formal), both inquiry-received with admission association. External delivery is not claimed: all local mail is captured and tester routing was restored.

Evidence is in the task visualization directory, subdirectory 520: contact-en-confirmed-provider-outage-390.png, contact-en-success-390.png, contact-de-provider-outage-390.png, contact-de-success-390.png and contact-de-success-1440.png. The file contact-en-recovered-1440.png is an in-progress attempt, not a completed recovery pass.

The 390px idle contact screenshots before and after hiding the idle widget are both 390 by 3318 and have exactly zero changed pixels, without a mask. This is local branch comparison, not global live/local parity.

Inquiry CUA: DE quantity Enter updated the native draft from 1 to 2, the native update button from 2 to 3, and reload retained 3. The resulting received order is 8968. EN service failure retained the entire form; restoring Siteverify then clicking the same button without refilling produced order 8969. Both received pages were captured at 390 and 1440. Earlier inquiry retry-result images show intermediate attempts, not completed recovery.

The real browser exposed a native account-ui capture handler marking the first unverified submit as busy and consequently suppressing the verified resubmit. The correction defers this UI-only state until the verified resubmit; server proof validation is unchanged. Registration company/person steps, normal login and reset idle pages were checked in EN and DE at 390 and 1440. Account creation, progressive login and reset key mutation are covered by native fixtures; no production account or password was changed for these screenshots.

## Rollback and separation

The mode defaults off; no private production key is committed. Local fixture wp-config and mail routing were restored; temporary verification MU fixture removed. Combined #522 handles backup, reviewed deployment, private configuration and actual production readback. Off is the admission rollback; code rollback uses atomic deployment. Native permissions, mail isolation and model routing must not be bypassed to obtain a pass.
