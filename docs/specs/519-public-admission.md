# Shared public admission

Issue: #519. Policies: #507 and #508 (resolution comments
6324053873 / 6324114050). Part of #505. This implements reusable mechanisms;
#520 and #521 connect the actual business/resource doors, and #522 owns rollout.
A registered helper is not evidence that a door is protected.

Use the existing Commerce plugin as owner, with narrow WordPress filter/REST
interfaces consumed by Tools. Woo's native account/order hooks, permissions and
mail remain authoritative. LC has no server-side challenge or atomic quota API;
WP nonces do not provide single-use/replay protection. WordPress options/MySQL
are already the native rate-counter store. Add no paid plugin, alternate model,
second CSS pipeline or custom customer-page layout.

Read the mode and Turnstile keys from private wp-config/environment configuration.
No secrets are saved in options, issue text, logs or builds. Modes are explicit:
off retains current behavior; observe records advisory results without claiming
enforcement; enforce requires configured validation. A configuration or provider
failure is unavailable, never a successful verification or a content-spam label.
The staff health surface must identify mode and configuration separately from
actual connected-door coverage. Keys in this repo's fixtures are official public
test keys only. Production must reject the dummy-key configuration.

Siteverify uses the fixed official HTTPS endpoint, strict success Boolean,
hostname/action binding and a stable UUID idempotency key. Omit optional remoteip.
Tokens are bounded to the documented 2048 characters; the provider's 300-second
single-use validity is not replaced with a client claim. A three-second HTTP
ceiling is an initial operational parameter chosen here to limit form waiting;
a retry keeps its request UUID and is bounded by the token lifetime. Classify
invalid/expired/replay separately from provider/configuration failure.

A proof is bound to the current server-derived browser/account subject and
allowed action; its initial lifetime is 300 seconds (no longer than the challenge
token window). It authorizes quota-controlled use only, never account approval,
private records or unlimited model calls. An anonymous HttpOnly/SameSite browser
cookie is a pseudonymous bucket, not a claim to identify a person. Clearing a
cookie cannot be completely prevented; independent account, connection and site
ceilings remain necessary. Never trust forwarded IP headers.

Admission and resource accounting are separate. Multi-dimensional fixed-window
and in-flight reservations compare/take atomically; denial leaves every dimension
untouched. A request UUID is bound to its payload fingerprint. Before dispatch,
cancellation may return resources; after upstream dispatch a timeout/disconnect
cannot refund spending or replay it. Durable outcome/lease state permits recovery
without treating a lost response as a free second request. Business side effects
must additionally bind their native source record to that UUID in #520.
The WordPress ledger is one non-autoloaded JSON option read directly under a
connection-owned, database/prefix-scoped mutex. One atomic UPDATE persists all
dimensions plus the receipt; no nested SQL transaction commits Woo's unrelated
work. Failed writes leave the previous journal, and a lost response recovers the
same UUID rather than a free second reservation. Initial safety bounds: a
one-second mutex wait, at most sixteen dimensions/links per operation, a maximum
300-second in-flight lease, 24-hour receipt retry window, 10,000 live receipts and an 8MiB JSON journal
ceiling (checked before decoding and before writing).
These are operational bounds selected here, not vendor or customer facts. A full
or corrupt ledger is explicitly unavailable; it never resets itself to zero.

Anonymous/registered transitions preserve the browser count and import/link the
relevant account budget so login or a new conversation cannot reset allowance.
All initial business/model/file/engine limits come from #508 and remain distinct.

Keep pseudonymous counters and receipts outside autoload and public REST options;
no customer body, password, raw token, raw IP or API secret is in their payload.
Bound cleanup to expired windows/leases while retaining dispatched receipt state
through its retry window. Include live-pull anonymization and native privacy
coverage for any subject-linked new payload. Staff counters identify reasons and
remaining/retry timing, not fabricated exact euro costs.

The shared client starts only on actual form/tool interaction. Official Managed
widgets use interaction-only appearance; expiry/error/timeout is visible to the
calling form and input remains intact. No password restoration storage. A verified
form automatically resumes its original submission. Native Woo notices and LC /
WindPress own presentation; the shared module owns no customer CSS.

Acceptance: real WP database and second-connection concurrency, no partial quota
spend, stable replay/changed-payload rejection, safe pre-dispatch release and
post-dispatch retention/crash recovery, browser/login accounting, configured /
invalid / unavailable validation, privacy/anonymization, scoped and full checks,
independent Spec/Standards reviews, and real EN/DE 390/1440 states. Dummy-key
fixtures and real network/widget availability are reported separately. Local
instance g519 uses the live theme/uploads snapshot before any UI work. No model,
mail, production enablement, DNS change or purchase is required by this ticket.
