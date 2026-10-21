# Public business and account guards

Issue #520; accepted policy #507/#508; shared mechanism #519 / PR #523.
This specification describes this branch. Activation and production readback
belong to the combined #522 rollout, not this ticket.

## Customer contract

Browsing has no challenge. Contact and inquiry remain open to guests. Jev content
labels never decide admission, account approval or deletion. The protection
checks the actual native write boundary before orders, accounts, external VAT
calls, reset keys, comments or mail. Normal successful login keeps the native
password flow without a challenge; repeated failures trigger verification.

The shared modes are off, observe and enforce. Observe is advisory and cannot
block a customer. Enforce requires a scoped, server-validated proof and an atomic
allowance. Valid verified autofill replaces the old three-second and three-per-IP
rules. Invalid proof creates no business record or business mail. A protection
outage reports failure, retains editable input and the existing solution draft,
and offers retry or sales@de-linker.com. It never reports an unsaved inquiry as
received. Passwords, reset tokens and proof secrets are not recovery payloads.

## Native boundaries and source inventory

| Entry | Native boundary | Write protected |
| --- | --- | --- |
| Contact and inquiry, including direct admin-post | Existing Contact/Inquiry Handler after native nonce and field validation; Business::run | Sender's native Woo order and customer/team mail |
| Woo registration | woocommerce_process_registration_errors, actual arguments errors / username / password / email | Customer creation, VIES, registration mail; password deliberately ignored |
| Core registration | registration_errors plus extra form nonce | Core user creation/mail; does not enable disabled registration |
| Woo and core password reset | Shared lostpassword_post before key generation; profile_update acknowledges saved key | Reset key and native reset mail |
| Login | wp_authenticate_user after progressive failure hints, before password hashing | Repeated authenticated attempts; native password and permission checks retained |
| Woo draft forms, GET commands and wc-ajax | wp_loaded before native form handlers | Add/remove/undo/update/coupon/shipping/review and owned saved-solution add |
| Reorder | woocommerce_load_cart_from_session before native session hydration executes reorder | Reorder's early cart clearing and insertion; native nonce/capability checked |
| Woo Store API cart mutations | rest_dispatch_request after native permission and parameter validation | Native cart mutation callback, including native batch subrequests |
| Comments and REST comments | preprocess_comment; REST wrapper after native permissions | Comment insert/notification; staff moderation retained |
| XML-RPC | Native method map | Enforce removes unauthenticated pingback.ping; authenticated methods and read-only pingback lookup retained |

Snapshot inspection: core users_can_register=0, Woo account registration enabled;
default comments and pings open, with a native filter currently closing public
comments. The enabled-comments fixture temporarily opens only its disposable
test post; it does not reopen site comments. These are snapshot values, not claims
about future production state. No broad XML-RPC disable or blanket query rule is
introduced. A product_id read alone is not a draft mutation. Native nonce,
ownership, Store API permissions and account approval/price gates remain.

## Allowances

Accepted #508 business budgets are shared across contact, inquiry, genie_contact,
genie_inquiry and conversation_mail: anonymous 10/hour and 20/UTC day; signed-in
20/hour and 100/UTC day; broad direct-connection 100/hour. Forwarded headers are
not identity. Login carries accumulated browser spending once into the account;
logging out does not reset browser counters. Draft writes do not consume
business-message allowance. #521 consumes the trusted policy/context hooks at
its actual handler boundaries; Commerce Sender does not debit them again.

Additional #520 starting allocations are operator recommendations within the
owner's delegated scope, not measured customer demand or industry facts:

| Operation | Initial subject allowance | Broad connection |
| --- | --- | --- |
| Registration | 5/UTC day | 100/hour |
| Password reset | 5/hour; independent target 2/hour and 5/UTC day | 100/hour |
| Verified progressive login | 20/hour | 100/hour |
| Draft mutation | 120/hour | 100/hour |
| Public comment | 10/UTC day | 100/hour |

Progressive hints are 3 failed attempts/browser or 100/direct connection within
10 minutes. A site hint at 1000 failed attempts/10 minutes stops allocating more
hint rows and requests verification. Hints do not reject a correct verified
password and store no username/password. They use the existing atomic native
RateLimit storage, with hourly expired-row pruning; failures do not fill the
business idempotency journal.

Unverified optional customer confirmations share target 2/hour, 5/UTC day and
the existing site 10/UTC day allocation. Target refusal does not spend a site
slot. Contact/inquiry, registration-received and unverified Genie conversation
confirmation consume this trusted seam. A cap omits the optional receipt while
retaining the account/inquiry and team notification. Password reset allocation
is separate so contact spam cannot suppress account recovery. Native Outbox
delivery throttles and 24-hour retry remain unchanged.

## Idempotency, recovery and privacy

The form carries a random logical UUID; payload, identity and action are bound
server-side. BusinessRecord stamps UUID and scalar input/subject HMACs before
Woo's first save. A completed retry returns the same native received record,
even after cart emptying; changed payload or another browser cannot recover it.
If the final journal acknowledgement is lost, an exact associated received Woo
record recovers the result without repeating Sender. A pending record is not
success and is not blindly replayed. HPOS and classic storage use their native
exact lookup, then the same status and binding checks.

Inquiry fingerprint includes the original Woo cart hash and validated fields.
A changed draft before first submission requests review; successful retry uses
the original posted hash after cart clearing. Failed inquiry fields reuse the
existing recovery path. Failed contact fields use the same signed Woo session,
allowlisted, consumed once, with a five-minute lifetime. Recovery excludes
password, proof and nonce, and escapes fields on rendering.

Optional customer receipt body is fixed and includes neither supplied name,
message, arbitrary URL nor product lines. Team mail retains actual inquiry data.
The wording acknowledges a message addressed to the team rather than claiming
that the recipient personally submitted it. Trusted recipient ownership HMACs
associate admission records with native privacy erasure; native Woo erasure
anonymizes the order's retry references along with its personal data.

## Native UI and minimal custom seams

LC/Woo retain page composition and native forms. WindPress retains styling; no
plugin CSS or inline design is added. Hidden proof fields are data fragments.
The shared client loads Cloudflare only after interaction, then places its
interaction-only widget next to the original submit action. Idle widget is
hidden to avoid adding a gap to native layout. Pending verification deduplicates
clicks; retry keeps the actual submitter and rechecks proof. Ordinary draft links
become native POSTs with proof outside the URL; Woo AJAX retains its own path.

Woo/WordPress provide forms, nonce/capabilities, persistence, privacy and mail.
They do not provide this site's cross-entry subject allowance, scoped Siteverify
admission, native-write idempotency or fixed target-capped receipt policy. These
need server adapters. LC tags and WindPress cannot authorize a server mutation,
so the checks belong at native handlers rather than page markup or snippets.

The local isolation CSP required the official challenges.cloudflare.com script,
frame and connection origins. The narrow local allowlist now permits these;
mail and private-service isolation remain. Browser acceptance uses the official
dummy-key script and iframe; only server Siteverify replies are explicit local
fixtures. This is not production verification.

## Delivery evidence

See docs/acceptance/2026-10-22/520 for native fixtures, checks, independent reviews,
copy critique and browser states. Combined integration must exercise shared #521
business/receipt seams and #511's actual async Jev transport. No production
activation, successful delivery or full visual parity is inferred from unit
tests, local screenshots or CI alone.
