# Existing inventory credential: native local acceptance

Issue [574](https://github.com/AssassinFlash/de-linker/issues/574), map
[533](https://github.com/AssassinFlash/de-linker/issues/533). The implementation is
based on origin/main `3bb955569eecc972b71df7cf4d5df69eb6aac41c` in an independent
worktree. No production installation, activation, credential use, role change,
password change, merge or deployment occurred in this task.

## Result and scope

The new MU plugin confines one privately bound native application-password
user/UUID tuple to these effective native REST reads:

- `GET /wp/v2/media` with `mime_type=application/pdf`;
- `GET /wc/v3/products`, preserving the existing consumer's `status=any` query.

It does not identify the tuple from client input. Core first checks the password;
the native authenticated user and credential item select the scope. A native
authentication error rejects other protocols and raw methods, and
`rest_pre_dispatch` checks every effective REST dispatch, including subrequests.

Cookie authentication, customer password login and unrelated application
credentials retain their native behavior. No customer-facing UI or copy was
added. The coordinator explicitly classified this as a native API task, so a
bare isolated instance is used for mechanism acceptance; this is not a UI parity
claim.

## Test environment and evidence

Instance `i574`, `http://127.0.0.1:9353`, WordPress 7.1.3, PHP 8.3, WooCommerce
11.2.0 and Polylang 3.8.10. The local native HTTP guard and mail capture are
required by the runner. No external HTTP, real mail or model is called.

The final machine-readable result is [evidence/native.json](evidence/native.json).
It contains only aggregate counts, case names, booleans and response hashes, with
no credentials, user identities, raw response rows or native application UUIDs.

Run from the assigned worktree:

```sh
just up i574
just wp i574 linker-i18n setup --user=local-admin
just inventory-access i574 --evidence /PRIVATE/PATH/native.json
```

The runner refuses a foreign checkout, missing native guards or a preexisting
owned fixture. It persists ownership immediately after each successful native
user/post creation, before later credential or metadata work. Failed persistence
compensates only the just-created record and reads its absence back. The outer
`finally` cleans all previously recorded resources and removes only this test's
temporary binding and loader. Cleanup failures retain durable ownership for
explicit recovery rather than discarding it.

The upload fixture also creates an exclusive directory using a fresh UUID and
persists that namespace plus its intended file before file creation, writing or
attachment metadata. Its synthetic bytes and all deletable attachment paths stay
inside that directory. Native cleanup and a filesystem readback verify that the
owned file and empty directory are gone. No fixed preexisting-capable upload is
registered for deletion.

The native language setup is meaningful: an initial bare instance had no
Polylang languages, so products were absent from the consumer's default-language
collection even though an explicit all-language diagnostic could find them.
The fix was to configure native languages and assign only synthetic products to
EN. No consumer filter, production language data or protection limit changed.

## Before and after

Before the MU plugin, a real authenticated POST using the selected synthetic
native credential changed the sentinel record (HTTP 200). After the scope was
installed and privately activated, that request returned HTTP 403 and the
sentinel response remained identical through every forbidden request. A separate
unrelated credential and native administrator cookie successfully performed
positive-control writes, proving that the native route was functional.

An intermediate native test also caught unrestricted non-PDF media reads.
Requiring the native PDF MIME filter closed that gap without changing the actual
consumer query.

Two real loopback HTTP servers independently reproduced the existing inventory
client forwarding its Basic authentication header after a cross-origin 302
(`received_auth` was true at the destination). With the dedicated redirect
handler, the destination receives no request and the client raises an explicit
origin error. Same-origin redirects still authenticate and return the expected
body/count headers. These tests use only a fixed synthetic credential.

## Native matrix

The JSON records every native case. The relevant groups are:

| Boundary | Observed result |
| --- | --- |
| File installed with no private binding | Status `unconfigured`; does not claim API protection |
| Explicit inactive binding | Status `inactive`; baseline reader completes |
| Valid exact native user/UUID binding | Status `active`; both collection reads succeed |
| Same UUID on a different synthetic user | Unchanged native behavior; user half of binding is enforced |
| Other credential on the same administrator | Native reads and positive-control write succeed |
| HEAD, POST, PUT, PATCH, DELETE, OPTIONS | Selected credential receives 403 |
| Query, JSON body and header method overrides | Selected credential receives 403, including GET aliases |
| Item routes, case aliases, other routes, missing/non-PDF MIME | Selected credential receives 403 |
| Batch, embedded author and native internal read/write/batch/alias subrequests | Child dispatch receives 403; canary stays zero until unrelated positive control |
| XML-RPC and a real non-REST application-auth probe | Selected credential refused; unrelated credential succeeds |
| Fake identity/binding headers | Cannot select another scope or authenticate |
| Invalid/unresolved active binding | Status `invalid`; all application-password authentication fails closed |
| Invalid binding with administrator/customer cookies | Existing cookie sessions still work |
| Parallel allowed/denied requests | Alternating expected 200/403; scope stays request-local |
| Anonymous site and native password/cookie login | Successful, with no MFA or customer step added |

Core normalizes one trailing slash to the same effective collection before
dispatch. That native equivalence is retained; it does not authorize item routes,
different case, methods or subrequest destinations.

## Actual consumer parity and side effects

The unchanged query/pagination code in `index.inventory.RestClient` reads the
native instance before and after activation. Each collection contains 201 complete
synthetic rows plus one additional row without document metadata. It must read
all three pages and match `X-WP-Total`; every returned row enters the canonical
response hash. The complete owned subset also proves the required PDF metadata,
product document links and publish/draft/private statuses. Existing rows from
other native tests, if present, remain in the full hash without being required to
have this fixture's metadata.

The final JSON supplies actual counts and before/after hashes. Equality means the
scope did not remove or alter a reader-visible row in this local fixture. It does
not prove current production counts or a hosted PDF binary download, parser,
embedding model or full index build; those were not called.

Native application-password usage metadata is intentionally separate from a
business mutation. In this run, three synthetic credentials changed from zero
to three having native `last_used` values after successful authentication. A later
REST refusal can follow that core usage recording. The denied sentinel writes
and child callbacks did not change business state. The runner finally reads zero
remaining owned users/posts, no fixture/binding/loader, and status `unconfigured`.

## Checks

- Native acceptance: all cases in the checked-in JSON pass, including cleanup.
- MU WPCS, PHPStan level 8 and PHPUnit: pass; PHPUnit has 12 tests/40 assertions.
- Genie Ruff and format for the full project, full mypy (185 source files): pass.
- Existing inventory tests plus native loopback redirect tests: 6 pass.
- Runner Ruff, format and strict mypy: pass.
- CI includes this native runner after its native EN/DE setup; hosted CI remains
  an independent gate after the fixed head is pushed.

## Review findings and defensive correction

Independent Standards review of `be262db2` found two defects. The fixes and
separate offline/native red-green evidence are summarized in
[evidence/review-fix.json](evidence/review-fix.json).

The first defect was a mutable second lookup of the credential between native
authentication hooks. The reviewer's isolated PHP doubles made the binding
disappear between callbacks and showed `forbidden_users_route_blocked=false`.
Replaying the same doubles against the correction produces true. This is an
offline reproduction, not WordPress HTTP acceptance.

The separate native local test revokes only the fixture-owned synthetic selected
credential at error-hook priority 20, after the scope callback at priority 10 and
before core's usage write and success action. It records both native deletion
and the later core success event. With the old MU implementation, those events
are true and the expected 403 assertion fails; the first runner did not retain
the exact response status. With the correction, both events remain true and
`GET /wp/v2/users/me` returns 403. The error hook now snapshots the matched binding
once, and the success hook validates the same trusted tuple against that snapshot
instead of querying mutable credential metadata again. Scope remains sticky for
the effective dispatch. This is deterministic native event-order injection,
not a claim of reproducing a concurrent production request.

The second defect was the fixture's unowned fixed upload path. A native ownership
assertion fails against the original fixture; its fixed path was absent in this
isolated instance, so the red run did not delete a preexisting upload. The new
fixture creates its own physical file in a durably recorded exclusive namespace.
The native regression checks every deletable attachment path belongs to that
file, then verifies native cleanup removed the file/directory and all owned
users/posts. It does not test deletion against a real existing customer upload.

The final expanded native matrix passes 62/62. It retains the original
administrator/customer/unrelated-credential, protocol, alias, concurrent-request
and full actual-consumer checks: both collections remain 202 rows across three
pages with equal complete-response hashes. Usage metadata (three credentials,
used 0 to 3) is sampled before the intentional synthetic revocation at the end.
This correction changes no customer-facing copy, client query or production
configuration. MU WPCS/PHPStan, PHPUnit 12 tests/40 assertions and runner
Ruff/format/strict mypy pass after the correction; earlier unchanged Genie and
transport checks remain as recorded above.

## Production handoff and rollback

The map owner must integrate this change with the current security release, not
deploy this old base as a complete site. Root MU PHP files are already discovered
by both local checkout and atomic deployment artifact enumeration; no separate
activation or copied plugin source is needed.

Before activation, the owner takes a fresh recoverable backup including private
configuration and verifies the already identified native credential tuple without
printing the credential, UUID or stored password hash. The file alone must read
`unconfigured` until a private constant is deliberately supplied.

Private configuration must contain an array named `LINKER_INVENTORY_ACCESS` with
`active=true`, the exact positive integer native `user_id`, and its existing
application-password `uuid`. No new user, password or application credential is
needed. Stage this configuration privately, verify that the tuple still resolves
through the native API, then atomically replace the private configuration and
read back only `InventoryAccess::status()`; it must equal `active`.

The owner then runs the real existing reader before/after with its existing
private config and records complete pagination counts and metadata hashes. This
is the missing production consumer proof. Production protocol/method refusal
readback belongs to that coordinated release, after review and backup; this
worker has made no such requests with the real credential.

Retain the exact previous private configuration and previous atomic code release.
Restore the prior binding atomically for rollback and read the resulting status
back. Removing the binding produces `unconfigured`, which restores the prior
broad native credential permission; that is a rollback boundary, not a protected
state. A damaged active binding deliberately blocks application-password logins
instead of silently broadening them, while cookie logins remain available.
Monitor that status explicitly. No DNS, external account, customer MFA, model
route or existing credential rotation is part of this change.
