# Native identity and project gateway

This increment connects the private planning protocol to the site's native
WordPress/WooCommerce identity. It does not release hardware selection or
engineering reports, and does not replace any model channel.

1. Only WordPress's current, REST-authenticated user or a presented, native
   Woo guest cookie can own projects. Account requests require the native
   REST nonce and login session. A guest cookie must pass Woo's own signature
   reader, have a future expiry, match the current handler's guest ID, and
   have a live row in the native Woo session table. A quota cookie, CartToken,
   claimed user ID or copied session data never establishes ownership.
2. A first same-origin bootstrap may create a native Woo session. It persists
   only a non-secret presence marker, issues the native HttpOnly cookie, and
   requires a subsequent presented-cookie confirmation before project access.
   Guest RPCs also require a Woo-session-bound nonce. Missing REST nonce on
   a still-signed-in browser cannot silently turn that browser into a guest.
3. Browser RPC paths are an explicit allowlist. Principal headers, service
   credential and previous guest are constructed only by the server. The
   account-claim endpoint is never a public RPC. All planner responses,
   including core REST errors and unknown paths, are private and expose no
   cross-origin read permission. Body, JSON-depth and transport response caps
   are enforced before expensive parsing/forwarding. Redirects are disabled.
   The pre-dispatch guard runs before the installed integrations; a refused
   body is removed from the native Request before later filters can parse it.
   Its original refusal is reasserted afterward because installed ACF
   initialisation can discard a previously returned error. Accepted requests
   retain their original wire bytes. Core cookie authentication is unchanged.
   Numeric JSON commands use finite binary64 values with absolute magnitude
   at most 2**53 - 1, the shared exact integer representation window. This
   is an explicit interoperability limit, not an engineering limit. The
   private command DTO rejects larger values before any durable write; PHP
   also rejects them before forwarding and before re-encoding a read/replay,
   so broader trusted/internal CAS data cannot be silently rounded.
   Unsupported methods with bodies are subject to the same guard, because
   installed integrations may parse JSON before WordPress matches the route.
   Reusing a native Request cannot carry an earlier refusal into another route.
4. The native `woocommerce_guest_session_to_user_id` event records a complete
   private claim command in one native post insert. It verifies the old
   presented native cookie against the event and current user; copied data
   cannot mint this command. No network call is made inside the login hook.
   A purpose-bound, HttpOnly ticket signed with native `wp_hash` carries only
   this verified transition through a failed native outbox insert. It is
   bounded by the former guest's expiry; it grants no project reads. Once
   the full outbox command is durably read back, that recovery ticket can be
   cleared. The outbox remains until the private engine confirms the claim.
   Each guest/account transition has its own purpose-bound cookie name. A
   later account's failed login capture cannot overwrite an earlier account's
   recovery proof. A bootstrap processes at most eight valid tickets; further
   tickets remain for the next request. No unbound claim ticket is issued.
5. Action Scheduler retries the same immutable event key. Network failures,
   invalid replies and conflicting claims retain the native record. Replays,
   duplicate deliveries and failed native deletion are safe because the
   engine transfers the whole guest once and retires it atomically. Recovery
   may queue a ticket already bound to account A while account B is current;
   it can only transfer to A and cannot expose A's projects to B. Pending
   recovery is reported honestly rather than labelled saved or completed.
6. Bootstrap reads the engine's current-identity status. A retired guest is
   replaced through the native Woo session mechanism and must confirm its
   new cookie. A foreign-project 404 does not trigger this rotation. Browser
   query caches are scoped to a server-derived native session hash and must
   be discarded when that scope changes. Every application RPC pins its
   opening confirmed scope; a later asynchronous caller cannot dispatch
   through a newly confirmed identity. Cache and navigation callbacks also
   check the client's current confirmation synchronously: native identity
   confirmation can precede React's next render and component cleanup.
7. Public resource admission uses the existing native ledger for quota only,
   independent of ownership. New project creation, revisions, uploads and
   calculation requests carry durable idempotency keys; a permanent engine
   replay cannot spend the same operation again. Within one native quota
   context an uncertain retry reuses its admission. Read/poll calls never spend a calculation unit.
   Operational ceilings are documented and do not imply engineering limits.
   Before a metered write, PHP asks the private engine's read-only
   `/operations/replay/{path}` for the same raw command. An existing owned
   receipt returns its original project revision/asset or current view of the
   same frozen run, without CSV parsing, source recapture, context compilation,
   another mutation or a new quota reservation. A different command under an
   old key conflicts. A missing receipt proceeds through native admission and
   the real command repeats ownership/idempotency checks. This replay path is
   not publicly allowlisted and cannot claim sessions or invoke other commands.
   An uncertain native receipt still present is completed from confirmed
   engine evidence; its absence after 24 hours does not authorise another debit.
   The private response supplies the hash of the validated canonical domain
   command used by that same permanent receipt. Native admission uses this
   hash, the same project-qualified receipt scope, owner and operation,
   rather than implementing a second JSON
   canonicalisation rule. Equivalent wire formatting can recover and settle
   the same receipt; a changed domain intent conflicts.
   The native transport journal uses a separate opaque identifier derived from
   the native principal, quota binding and original intent key. This avoids a
   raw UUID globally colliding after login or quota-cookie renewal. The engine
   still receives the unchanged original key/body. If no engine receipt exists,
   a previously dispatched attempt keeps its resource charge and a new native
   quota context admits the explicitly retried attempt. Existing receipts are
   not rewritten or refunded by inference. Evidence: the real native dispatched
   timeout→login fixture previously returned409 despite zero engine projects.
   A still-present legacy raw-UUID receipt is reused and settled only when its
   purpose, quota binding and principal-derived intent fingerprint all match.
   Context lookup uses the same atomic journal lock/recovery as admission. A
   different purpose/binding is unknown; changed input in the same legacy
   context conflicts before new admission. Legacy records cannot distinguish a
   changed intent from another guest principal sharing that quota binding, so
   a mismatched fingerprint is conservatively refused rather than reused.
   Already-confirmed permanent engine results remain recoverable; a mismatched
   legacy entry is never settled as that result's receipt.
   A confirmed unused reservation refunded by native expiry/cancellation can
   start a new transport attempt on explicit retry. The old receipt remains
   terminal. Its successor ID is deterministic from the current principal,
   quota binding, original key and preceding terminal ID, so parallel retries
   converge before the journal's atomic reserve. Both legacy and new-style
   receipts use this rule. Dispatched/unresolved/completed attempts are reused;
   erasure tombstones cannot reopen admission. Resolving at most32 successor
   entries per request is an initial operational bound, not an engineering or
   business limit; exhaustion returns a temporary refusal with the original
   frozen intent retained when the engine has no receipt. An already-confirmed
   permanent result is returned despite traversal exhaustion, without new
   admission or pretending an unlocated journal entry was settled. Journal
   persistence failures remain explicit. Permanent engine replay precedes this work.

Acceptance requires real HTTP cookies/nonces and a running local site, not
only mocks: two isolated guests, reload, native login/registration and logout,
wrong nonce/origin, absent/expired/tampered cookie, CartToken clone, a native
outbox retry during upstream failure and a restored connection. No test email
is sent to production recipients. This increment's completion does not close
the unified planner's remaining editing, calculation, country, report or site
acceptance gates.

Initial local resource policy: 16 MiB command bytes, 32 JSON container levels,
32 MiB reply bytes and a 5 second RPC timeout. Public mutation keys are native
UUID v4s and the shared journal reserves a 30 second dispatch lease. Per-browser
and per-account ceilings are respectively 10/100 new projects per UTC day,
240/1200 revisions or parameter updates per hour, 20/100 CSV imports per day,
and 30/120 calculation submissions per hour. Corresponding site ceilings are
500/day, 5000/hour, 500/day and 500/hour. These are initial local operational
policy, not production workload evidence or physical scope; load acceptance
and matching ingress settings remain part of the full delivery. The journal
reuses completed/uncertain command keys without another debit. The browser
retains the original command snapshot, key and wire bytes for retries, so
an edit cannot change an in-flight save. Server idempotency follows canonical
domain intent, including declared CSV provenance and mapping, rather than
insignificant JSON whitespace or key order. Long-running work is governed by durable worker
leases rather than a WordPress request lease.

## Current increment evidence

Six opt-in integration tests ran against the owned `p548` instance with the
actual WordPress 7.1.3 / WooCommerce 11.2.0 snapshot and real engine process:

- Two native cookie jars: create, read, reload, repeat the same save, history,
  stale-revision conflict and cross-owner/forged-header refusal. Empty input
  objects remain JSON objects across the PHP gateway.
- Missing/wrong native guest nonce, foreign origin, wrong content type,
  absent cookie, unknown methods/paths and the non-public claim endpoint.
  Core's additional logged-in no-cache directives remain intact; every
  response includes `no-store` and `private` and exposes no CORS origin.
- Tampered signature, a valid-but-expired cookie generated with Woo's own
  native hash method in a fixture, and a session row deleted natively.
  Revocation requires a new confirmed cookie and cannot reopen the old owner.
- A genuine Store API CartToken clone cannot inherit the source's projects.
- Native login during an unavailable planner transport retains the complete
  outbox event. Restoring the route completes ownership transfer; replayed old
  guest cookies, missing account REST nonce and logout do not expose it.
- A temporary, request-scoped local MU fixture rejects native claim inserts.
  Recovery tickets survive logout and login to a second account without
  overwriting one another. After removal of that fixture, recovery queues
  both immutable events and the actual Action Scheduler dispatcher completes
  the first account's event. Each account can read only its own project.

The short-lived MU fixture was removed and the owned transport option restored
in `finally` blocks. Native test account passwords are generated in memory,
excluded from representations, and the local accounts are deleted afterward.
Local mail remains captured. No production route, account, mail or data was
written. PHPStan level 8, WPCS and all 289 existing Tools unit tests pass; the
initial unit failure was a missing locked `jsdom` installation, resolved with
the plugin's unchanged lockfile. Ruff and strict mypy cover the native HTTP
fixtures. This is component integration evidence; the modern app's rendered
browser acceptance and full production release remain open.

### Independent review corrections

The first fixed native-gateway review at `d2e5766d` found two genuine integration
gaps: callback-only limits ran after native JSON parsing; the native journal's
one-day receipt retention could charge a permanent command replay again. Those
findings were retained and fixed before release, rather than treating the six
successful functional tests as complete acceptance.

The corrected eight-test native suite passes. It instruments the actual
installed Request/Server and all installed REST filters: a 16 MiB-plus body,
100 levels and 600 levels are rejected while the largest input reaching any
native JSON parser is zero bytes. Literal quoted brackets/backslashes still
reach the parser unchanged. The installed ACF filter's error reset was traced
and covered. A separate real engine/native HTTP test removes only its own
fixture UUID from the native journal, then recovers the same project, empty
object/array and numeric input without changing quota state or adding a new
receipt. A changed input under that UUID returns conflict.

The private replay cases also pass for create, revision, CSV, battery and
energy jobs (queued and completed), preserving original revisions after later
edits and refusing foreign/team/non-authenticated callers. Source rights and
CSV logical metadata have one shared construction for mutation and lookup.
The full engine suite passes 413 tests; Tools' 289 unit tests, PHPStan, WPCS,
Ruff and mypy pass. The native outbox's repeated account-event query is now one
selector shared by pending and foreground recovery. Independent re-review of
these fixes remains required before this component is accepted.
