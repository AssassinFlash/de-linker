# #245 · Customer access to wp-admin

The admin-access explanation is a state of the account chain specified in [184-account-chain.md](184-account-chain.md).

## Behaviour and data flow

`WC_Admin::prevent_admin_access()` retains ownership of the access decision and protective redirect. `AdminAccessNotice::protect()` observes the final `woocommerce_prevent_admin_access` boolean, returns it unchanged and records it on the current native WordPress login session. Existing session information and expiry remain intact. A denied decision attaches a one-use `wp_redirect` destination adapter; Woo still calls `wp_safe_redirect()` and exits.

The adapter marks the translated account URL with `?admin-access=staff`. The Polylang cookie is resolved through `PLL_COOKIE` and the companion plugin's `Languages` helper; absent or unsupported language preferences use `Languages::SOURCE`, missing/deleted twins retain the source account, and a missing account permalink retains Woo's destination. No request-supplied return destination is used.

The marker is read-only presentation state. Its visibility requires a logged-in account-page request whose current WordPress session holds Woo's recorded denial. There is no independent role or capability list. Another session does not inherit the decision, and a later Woo allow decision replaces the denial. The record has the lifetime of the existing WordPress session; signing out removes it with that session.

`/wp-admin`, `/wp-admin/` and `/wp-admin/users.php` use the same explanation. The existing account page, LC assignment, header and footer remain the shell. Only Woo's inner `myaccount/my-account.php` include is replaced, after the pending-review card's template filter. Approval state does not alter the explanation; normal account gates remain unchanged. Returning to account removes the marker, and switching languages preserves it.

WordPress `wp_logout_url(wp_login_url(admin_url()))` supplies the primary action: nonce-protected one-click logout, then native staff login with a fixed wp-admin return destination. User Switching owns its signed switch-to/switch-back URLs and authentication cookies. Its native fixed switch-back link remains visible on the explanation. AJAX/admin-post exemptions and guest staff-login remain Woo/core behaviour.

## Presentation and native mechanisms

| Need | Carrier |
| --- | --- |
| Admin protection | `WC_Admin::prevent_admin_access` and its existing filter. No replacement admin-init guard or capability rule. |
| Decision across the redirect | Current `WP_Session_Tokens` session metadata. No additional authentication cookie, transient expiry policy or user-wide role flag. |
| Explanation content | `content/livecanvas/account/admin-access.html` under the existing account LC page. Scalar fields supply escaped email, reviewed text and native URLs. Woo has no explanation template for its redirect, so its supported inner-template filter selects this fragment. |
| Card style | Existing account `.linker-gate` card/buttons and WindPress tokens. New selectors only wrap long email and stack/pad this card's actions. |
| Language selection | `PLL_COOKIE`, `Languages`, Polylang's page pairing and the shared header query-state whitelist. |
| Account and sign-in | The existing account chain in [184-account-chain.md](184-account-chain.md). No new page, rewrite endpoint or PHP layout. |

## Copy

EN identifies the current customer email, explains that the admin area is for Linker staff, and names the sign-out/staff-login and account actions. DE uses formal Sie wording:

- `Bereich für Linker-Mitarbeitende`
- `Sie sind mit Ihrem Kundenkonto %s angemeldet.`
- `Der Verwaltungsbereich ist ausschließlich für Linker-Mitarbeitende vorgesehen.`
- `Abmelden und mit einem Mitarbeiterkonto anmelden`
- `Zu meinem Konto`

The email comes from the authenticated user, never the request.

## Acceptance

- All three admin addresses reach the explanation for existing customer sessions in each approval state, EN/DE, 1440/390.
- One click signs out and presents the native staff login; submitting staff credentials reaches wp-admin.
- Native User Switching enters the customer view and switches back to staff.
- The page follows Woo's actual decision, including extension filters; a query marker without a recorded denial does not select it.
- Unit tests cover destination language/twin/permalink fallbacks and the complete scalar field map. Real browser fixtures cover sessions, actions, native exemptions and language switching.
- The four approval states produce the same visible page; identical state captures demonstrate that invariant rather than separate layouts.
- Existing account sign-in design retains exact live/local full-page parity at both widths and languages, without masks. The new explanation is the authorised #245 change.

Evidence is indexed in [the acceptance record](../acceptance/2026-10-18/245/README.md).
