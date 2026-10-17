# #245 · Customer access to wp-admin

Authority: AGENTS.md, owner ruling 2026-10-17, issue #245. Staff review/deployment belongs to Claude. The implementation session uses only local instance `c245`.

## Behaviour and native mechanisms

`WC_Admin::prevent_admin_access()` remains registered and returns its own protective redirect for users without its staff capabilities. `AdminAccessNotice::protect()` observes its final `woocommerce_prevent_admin_access` boolean unchanged, and attaches a one-use `wp_redirect` adapter when it is true. Woo still calls `wp_safe_redirect()` and exits. The adapter marks the translated account URL with `?admin-access=staff`; it never uses a request-supplied destination. The site language comes from the whitelisted Polylang front-end language cookie because the denied request is in wp-admin, outside a front-end language route.

The marker is read-only presentation state. Only logged-in accounts without Woo's staff capabilities can render it. Both `/wp-admin/` and `/wp-admin/users.php` take this path. The existing account page, LC assignment, header and footer remain the page shell. The explanation replaces only Woo's inner `myaccount/my-account.php` include, after the pending-review include, so pending/restricted/rejected sessions can also read the explanation without altering their approval state or usual account gate. Back to account removes the marker.

WordPress `wp_logout_url(wp_login_url(admin_url()))` supplies the primary action: nonce-protected one-click logout, then the native staff login with a fixed wp-admin return destination. Credentials, role checks and post-login dispatch remain WordPress/Woo behaviours. User Switching's own signed switch-to/switch-back URLs and cookies remain its own; the native fixed switch-back link stays visible on the explanation.

## Native-first exhaustion and presentation ownership

| Need | Native path and reason for the narrow adapter |
| --- | --- |
| Deny customer admin access | Keep `WC_Admin::prevent_admin_access`; no replacement admin_init guard or capability changes. Its filter observes the decision, the redirect filter changes only that decision's destination. |
| Explain the denial | Woo's redirect does not carry an explanation. Use its existing translated account page and supported inner Woo-template filter. No new page, endpoint, rewrite rule or PHP page layout. |
| Compose the card | `content/livecanvas/account/admin-access.html`, interpreted by the same LC-fragment shortcode channel as the account workspace. Scalar shortcode fields supply escaped email, reviewed text and native action URLs. No HTML composition in PHP. |
| Style the card | Reuse the live account `.linker-gate` card/buttons and tokens in WindPress. The new scope wraps long email and stacks the long staff action with vertical padding; it changes no other gate. No plugin stylesheet or inline styles. |
| Switch language | Existing header language links retain this page's `admin-access` query state, alongside the existing query whitelist. Polylang still resolves pages and language paths. |
| Switch user | User Switching 1.12.2 as installed in the snapshot; no hook or cookie override. |

AJAX/admin-post exemptions and guest staff-login remain Woo/core behaviour. Customer approval and staying signed in (#222) and inquiry submission (#246) are outside this change.

## Verification and rollback

Repeatable browser fixtures are in `tests/e2e/specs/admin-access.spec.ts`: four approval states × two admin addresses × two languages × two widths, staff login in both languages, switch to customer/back to staff, bidirectional language switching, and native AJAX/admin-post/guest login. Fixtures create and remove their own users; no existing account, option or password is changed. Local mail is captured to files. The rejected-session fixture models a previously signed-in customer whose state changed, without changing login rejection policy.

Evidence and commands: `docs/acceptance/2026-10-18/245/README.md`. Existing sign-in design parity has exact live/local full-page RGB comparisons at both widths and languages, without masks. The new explanation is the owner-authorised #245 behaviour change; it has no pre-deployment live counterpart.

Rollback is the previous commerce plugin version plus its previous WindPress volume/cache; there is no database migration or new content record to remove. Deployment and the live customer walk are deferred to Claude after review.
