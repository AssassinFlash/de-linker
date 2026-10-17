# #245 · Implementation-session review

This is the implementation session's Spec + Standards self-review of the complete change. Claude's independent PR review is pending; this record does not replace it.

## Spec

- Woo's protective decision remains unchanged. The adapter is installed by `Account\Module`, observes `woocommerce_prevent_admin_access`, changes only the next redirect, and removes itself after use. Native admin-init and capability checks remain active.
- `/wp-admin` (including canonical slash redirect), `/wp-admin/` and `/wp-admin/users.php` reach the explanation for signed-in customer sessions. The four approval states are fixtures, not changes to the approval implementation. Rejected sign-in is still rejected; an existing session can read the explanation.
- The page shows the authenticated customer's email, explains the staff boundary and offers both required native actions. All five strings have EN and independently drafted formal DE, with the draft/challenge/final record in `copy-review.md`.
- The staff action is WordPress's signed logout URL and fixed staff login destination. The real browser suite submits staff credentials and observes wp-admin in EN and DE.
- User Switching's user-list action and original fixed switch-back link are exercised, not a fabricated switch URL. Their authentication cookies are not modified by this implementation.
- Language switching keeps the explanation selected; account navigation removes the read-only marker. AJAX/admin-post and guest native staff-login paths remain outside the explanation.
- Live walk: 未完成. Claude performs it after deployment; this session must not write to production.

## Standards

- Composition is `content/livecanvas/account/admin-access.html` under the existing account LC page shell. The PHP include delegates to that fragment; the data shortcode emits escaped scalars and WordPress URLs, with no PHP layout or style.
- All style additions are scoped to `.linker-admin-access` in WindPress `auth.css`; existing gates and the shared header/footer styles are unchanged. WindPress compilation ran through the real local admin and read back a newer cache.
- No new dependency, database table, rewrite endpoint, page record, snippet, model route or approval rule. The Module constructor gains one optional dependency to match the existing explicit hook-wiring test.
- Whole-change inspection found no introduced legacy identifier (`tv_b2b_`, `Linker_AI_`, `dlk-`), copied implementation or authority reference to old-system rule numbers. The account/approval high-risk path changed only by registering the adapter and selecting its LC include for this explicit read-only state.
- Existing account sign-in page is pixel-identical to live in the same Chromium process at 1440 and 390, EN and DE: 0 unmasked differing pixels in all four full-page pairs. The authorised new explanation has no live counterpart before deploy.
- Browser fixtures create/delete their own users and leave existing account data/options untouched. Local mail transport remains the existing file recorder.

Validation logs and exact commands are indexed in `README.md`.
