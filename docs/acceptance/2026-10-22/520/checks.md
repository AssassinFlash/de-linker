# Public business guards: acceptance record

Local development on live snapshot 20261022-0018, instance g520 (WordPress 9284). No production change or external test email is represented by these results.

## Checkpoint verification

- Real BusinessAdmission fixtures cover native Woo received records, invalid proofs/nonces, retry after cart emptying, interrupted acknowledgement recovery, optional receipt caps with retained team queue, native Woo/core password reset and registration boundary, progressive login, Store API refusal and XML-RPC inventory.
- The real Woo four-argument registration hook is tested with password in its correct third position and validated email fourth; password never enters the journal. Shared policy tests cover NAT/autofill and browser-to-account carry.
- PHP unit checkpoint: 1390 tests / 6039 assertions / 204 integration skips. Browser client checkpoint: 8 tests. Additional native fixtures and full checks are being finalized; later exact-head results supersede checkpoint counts.

## Real browser evidence

The official Cloudflare dummy-key api.js and challenge iframe returned HTTP 200 in the real browser. Only server Siteverify replies are explicit local fixtures. The original local CSP blocked the official script; the narrow local CSP correction permits the official origin in the needed directives.

Real contact EN/DE forms: verification HTTP 503 prevented admin-post, retained input and displayed localized retry. Restoring the server fixture allowed retry without refilling. Native readback found exactly orders 8069 (en_US) and 8070 (de_DE_formal), both inquiry-received with admission association. External delivery is not claimed: all local mail is captured and tester routing was restored.

Evidence is in the task visualization directory, subdirectory 520: contact-en-confirmed-provider-outage-390.png, contact-en-success-390.png, contact-de-provider-outage-390.png, contact-de-success-390.png and contact-de-success-1440.png. The file contact-en-recovered-1440.png is an in-progress attempt, not a completed recovery pass.

The 390px idle contact screenshots before and after hiding the idle widget are both 390 by 3318 and have exactly zero changed pixels, without a mask. This is local branch comparison, not global live/local parity. Other page/state coverage and classic storage matrix are in progress.

## Rollback and separation

The mode defaults off; no private production key is committed. Local fixture wp-config and mail routing were restored; temporary verification MU fixture removed. Combined #522 handles backup, reviewed deployment, private configuration and actual production readback. Off is the admission rollback; code rollback uses atomic deployment. Native permissions, mail isolation and model routing must not be bypassed to obtain a pass.
