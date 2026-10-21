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

## Shared runtime and initial verification bounds

Verification-only dispatch limits: 20/browser/minute, 100/direct-connection/hour,
5,000/site/UTC day; one browser and two site verification calls concurrently.
The caller supplies no limit or identity. These are initial operational safety
bounds under the owner's delegated recommendation; they are separate from the
business/model quotas in #508. Verification leases are ten seconds. The two REST
verification routes reject raw bodies over 16KiB before argument validation.
This bounds application parsing; host-level ingress protection remains a rollout
check. Preparation signs a small stamp and never invokes the provider.

Native hooks are registered from Commerce's actual module list. The same REST
controller is used by the staff diagnostic and future native consumers. A verified
proof must also resolve to the successfully completed verification receipt at the
last dispatch boundary. A business proof is consumed once atomically with dispatch;
resource proofs remain scoped and budgeted during their original lifetime. A retry
with the same completed operation/payload recovers its native outcome before asking
for a fresh challenge. Unknown in-flight outcomes tell the customer to check the
status; they never falsely claim the submission was not received.

The shared client loads only its first-party bundle when enqueued. No Cloudflare
script, cookie or provider call is created by passive browsing. Actual interaction
prepares a stamp and loads the fixed official explicit-render script; concurrent
warm/submit calls share one attempt. Requests have a 15-second network timeout;
a challenge has a two-minute interaction timeout. Those client bounds are initial
usability recommendations, not provider guarantees. Expiry/error removes the
attempt and permits a fresh retry, without storing or clearing customer fields.
The client supports native pretty and query-string REST URLs, account REST nonces,
user locale and EN/DE vendor language. No customer CSS is introduced.

The staff diagnostic displays off/configuration separately, declares actual
consumer modules, and has a verification-only button. Counts are journal receipts
within the original 24-hour retry window, not a full traffic/cost history. It
contains no credential editor. Hourly native WordPress maintenance and every
admission use the same recovery operation; cron delivery must be checked in #522.

## Review corrections

Observe records shadow reservations, dispatches, completions, would-deny quotas
and retries in the same journal, with an `observe_` purpose. Every refusal or
storage/cookie failure remains an advisory result; it never blocks the original
native operation or silently authorizes a verified operation. These observations
are distinct from hard provider cost enforcement in #521. Off performs neither
shadow nor enforcement work.

Reservations return trusted consumers only safe dimension names, current remaining
units and fixed-window reset times. Quota refusals return the actual fixed-window
reset or earliest sufficient in-flight lease recovery, rather than a guessed
one-second wait. Staff summaries show the minimum remaining among active buckets
per dimension and the latest known reset/recovery; no subject hashes are exposed.

Aggregate admitted/quota/replay/payload-change categories are bounded to 256 daily
rows, expire at UTC midnight and carry the policy source version
`public-admission-519-v1` (#507/#508). This is an initial diagnostic storage bound;
when full, unseen diagnostic categories are omitted without changing admission.
These counters remain partial diagnostics, not a complete traffic history.

A signed-in subject is also associated by the existing private account-owner hash
when a verification receipt is reserved. This adds no account quota. Native
privacy callbacks therefore cover successful, failed and verification-only visits.

The atomic UPDATE checks both the exact original JSON and
`IS_USED_LOCK(name) = CONNECTION_ID()` in its own WHERE clause. Lock ownership is
also required during readback. A wpdb reconnect cannot overwrite a peer's admitted
operation with the old snapshot; real KILL CONNECTION plus a winning second
connection is included in the fixture suite.
