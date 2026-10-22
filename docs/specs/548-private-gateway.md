# Private project HTTP adapter

This is the authenticated service hop of the same active full planner delivery.
It does not replace WordPress native identity, CSRF, resource admission or the
guest-login transfer bridge. It is not yet mounted in the existing public engine
or exposed by a browser route. Those integrations must pass before release.

## Identity and transport boundary

The existing calculator Gate is conditional and POST-only. Private project
history, uploaded files and results require a separate fail-closed boundary on
**every HTTP method**, including unknown paths, GET, HEAD and OPTIONS. No
environment off switch or public health exception bypasses this boundary.

The server supplies the existing private service credential and a server-derived
principal kind/subject. WordPress must construct those only after verifying the
actual native user/guest session; no browser-provided Actor, owner or principal
header is forwarded. The principal is a stable identity, not the short-lived
quota bucket. Missing configuration gives 503; absent/ambiguous/wrong credentials
give 401; absent/ambiguous/invalid principal gives 400, all before body parsing.
Credential comparison is byte-safe and constant-time. Duplicate authority
headers are rejected. These headers are a private service assertion, not a new
browser login mechanism or proof that native WP integration already works.

The body has an explicit deployment byte ceiling. Declared length is ASCII
integer only, checked without unbounded integer conversion; streamed bodies
are counted too. Disconnects and length mismatch are rejected before calling
an operation. Both successful and error responses use `Cache-Control: no-store,
private`, `Pragma: no-cache` and `X-Content-Type-Options: nosniff`; downstream
handlers cannot replace that with public caching. No browser CORS or OpenAPI
documentation is exposed by this private app.

## Commands and read models

Private RPC operations use POST with strict integer `schema_version=1`, strict
finite typed command documents and no extra command fields. All lifecycle
commands go through the existing single Workspace authority. The caller cannot
select code, model versions, dependency hashes, numerical settings or an owner.
Enqueue returns a durable run; the HTTP process never performs numerical replay.

Operations cover create/read/revise project, bounded project/run navigation,
enqueue/read/cancel energy run, owned asset metadata/bytes, CSV import and
explicit numeric battery scenarios. An owned run may download its own immutable
energy trace. No raw content-hash or filesystem-path download is accepted.
Project views do not return owner subjects. Team principals have named read
access and cannot create or mutate through this adapter.

Reads and writes check ownership each time. A foreign project write is rejected
before publishing an orphan input blob. Revisions use expected-revision and
idempotency semantics; old run reads never substitute the latest inputs. Trace
and file reads use the run/project asset identity and recheck content hashes.
Missing and foreign references have the same 404 response.

Navigation is bounded by a deployment maximum page size. Project lists contain
only summaries, without reading input blobs; they order by modified time and ID
and identify themselves as live navigation. Run pages use immutable creation
time and ID cursors and contain summaries, not full manifests/results. Cursor
selection never changes the owner predicate. Individual immutable run/history
reads remain the authority for engineering results.

CSV upload is base64 inside the bounded private command, with a separate decoded
file ceiling, explicit mapping/units/timezone/origin and a user declaration of
source/rights. That declaration is preserved as such; it is not independent
measurement verification or official provider licensing. Battery input accepts
only the existing `explicit_scenario` contract and stays distinct from equipment
release. Provider acquisition is a separate trusted adapter, not a browser claim.

Protocol bounds of 256 characters for identifiers/labels/project titles and
4096 for source notes are application transport choices, not physical limits.
Deployment byte/CSV/page limits have no hidden default. Worker interval limits
and numerical tolerances stay frozen by the existing energy service.

Errors return domain codes or validation field paths/types, without exception
traces, row/file values, submitted private content or service credentials.
Unexpected internal failures do not become valid results. The factory must
reject differing HTTP/energy/kernel authorities rather than mix their data.

## Actual acceptance required

- All HTTP methods fail authentication before parsing even when the old Gate
  mode is off; missing configuration, duplicate/non-ASCII authority fields,
  malformed/oversized declared length and streamed overflow fail closed.
- The validated private principal replaces stale scope data; body Actor/owner/
  Context fields and schema bool/float coercions are rejected.
- Own create/revise/read/reopen/history work; another principal cannot read or
  mutate project/run/asset/trace; team may perform named reads but no writes.
- Project/run pagination is disjoint and bounded, without full-result/blob
  loading. Resource ceilings and failed foreign writes publish no new assets.
- Actual HTTP CSV upload + explicit scenario → revision → enqueue → real Worker
  → result and exact trace bytes, using the independent two-hour fixture:
  load 4 kWh, solar to load 3.62 kWh, grid 0.38 kWh, eta 0.9 each way.
- Editing after enqueue retains the old run/input/source identity. Equipment
  and country assessments remain unassessed by this component.

These checks prove the private adapter against synthetic authenticated service
assertions. Real WP bootstrap, signed guest/user lifecycle, both login routes,
durable guest transfer/revocation, Origin/nonce policy, abuse admission, browser
storage/cache behaviour, public mount and production readback remain required
parts of this same delivery. They cannot be inferred from TestClient.
