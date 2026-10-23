# Existing inventory application credential

Issue [574](https://github.com/AssassinFlash/de-linker/issues/574), child of 533.
Current integration baseline is `38ef4825f121107be6a42662d9e41c129a2d96e0`. The previously reviewed candidate `29e6df6c` originated from `3bb95556`; its changes are selectively ported, not deployed as an older complete site. No production activation here.

## Consumer and native boundary

`services/genie/index/inventory.py` is the only repository credential consumer;
`index/build.py` calls its `run()`. The actual client reads all pages of
`GET /wp/v2/media?mime_type=application/pdf` with the fields
`id,source_url,title,modified_gmt,media_details`, and `GET /wc/v3/products?status=any`.
Product attributes and document metadata must remain byte-equivalent after
canonical JSON serialization. Every collection count must match X-WP-Total;
synthetic native coverage uses 201 complete records to exercise three pages.

WordPress 7.1.3 verifies the password before
`wp_authenticate_application_password_errors`; rejection there precedes native
usage recording. `application_password_did_authenticate` supplies the trusted
user and native credential UUID only after successful authentication. These
native hooks identify the selected credential; no request parameter/header
chooses the binding. The error hook reads the binding once and retains a
request-local candidate after core validates the password. The success hook
matches the trusted user/UUID against that candidate without another mutable
credential lookup. A revoke between those callbacks cannot discard the scope
and restore broad access for the already-authenticated request.
`rest_pre_dispatch` runs at priority20, after the installed ACF6.3.1 initialization callback at10. That initializer returns null and otherwise erases an earlier refusal. The existing native users guard stays at20; it is not replaced or moved. The inventory guard checks each effective request, including
internal dispatch and batch subrequests. The raw HTTP method and method override
parameters/headers are also checked; HEAD/POST-to-GET aliases do not become GET
permission. Exact effective collection routes only; media requires the native
PDF MIME filter. WordPress's own trailing-slash normalization still refers to
that same collection and does not grant a different route. No individual item,
write or batch is allowed.

The new repository MU plugin is one class in one deployment-named PHP file.
`Checkout.production_mu_plugins()` and cutover `steps.deployment_artifacts()` both discover
root `mu-plugins/*.php`; no deployment allowlist expansion is needed. No regular
plugin activation, customer UI, capability/role rewrite or Code Snippets.

## Private binding and status

Private server configuration defines `LINKER_INVENTORY_ACCESS` as an array:
`active` boolean, positive integer `user_id`, native application-password `uuid`.
Actual values never enter source, documentation or evidence. The active binding
must resolve to an existing native credential for that user. A missing constant
is explicitly `unconfigured`; explicit `active=false` is `inactive`. A defined
malformed binding, or active binding that no longer resolves, is `invalid` and
rejects application-password authentication rather than restoring broad access.
In that invalid state all application-password logins are refused because the
selected identity cannot safely be determined. Cookie/password web logins are
untouched. With a valid active binding unrelated credentials are untouched.

Status is available through `Linker\Mu\InventoryAccess::status()` without
printing the user, UUID or secret. Installing the file is not activation.
Only the map owner may activate production after full review, exact CI and a
fresh recoverable backup. Retain the prior private binding for rollback.
Native valid-auth usage metadata can update even if a later REST dispatch is
refused; this is recorded separately from business mutations.

## Agreed acceptance seams

The issue/coordinator already chose these seams; no new owner decision is needed.

- Real native HTTP authentication and effective REST dispatch: selected read
  succeeds, writes/other routes/XML-RPC/non-REST/aliases/subrequests fail, no
  business mutation, malformed binding fails closed. This does not prove a
  production credential or production deployment.
- Real existing RestClient against synthetic local native collections: complete
  pagination, full required metadata and canonical hashes equal before/after.
  Real production counts remain the coordinator's post-review readback.
- Native cookie administrator/customer login and unrelated application password:
  behavior preserved; no customer MFA, role or inquiry mechanism changes.

All synthetic resources have immediately persisted cleanup ownership, and private
directories/files use 0700/0600. No production key use, new production credential, real mail,
paid model, global config change, merge or deployment is authorized to this worker.
The media fixture exclusively creates a unique upload directory, persists that
namespace and its intended file before writing bytes or attachment metadata,
and registers only that owned path. Cleanup removes the owned file and empty
directory; it never reuses a fixed potentially existing upload path.

## Authenticated redirect boundary

Two real local HTTP servers reproduced the existing `urllib` opener forwarding
the synthetic Basic authentication header to a different origin after a 302.
`RestClient` now uses a dedicated `SameOriginRedirect` handler. It compares scheme,
hostname and effective port before the standard handler can copy authentication
headers. A changed origin fails visibly; a same-origin redirect retains the
authenticated read. This changes neither the two collection queries nor their
pagination or metadata. No production credential was used to demonstrate it.

## Native fixture and CI boundary

`just inventory-access INSTANCE` accepts only a registered local instance using
this checkout with both native local HTTP and mail guards. EN/DE must already be
configured with `linker-i18n setup`; the CI step follows the existing page-cache
setup that supplies that prerequisite. Only owned synthetic products are assigned
EN; the actual consumer's query and native language behavior remain unchanged.

The fixture creates 201 complete records per collection and an additional record
per collection lacking document metadata. The latter models data from another
smoke test: all returned rows still enter the full-response hash, while required
field completeness is checked against the 201 explicitly owned complete rows.
The actual `RestClient` is used before and after activation, including every page
and the native count headers. This is API mechanism acceptance, not UI or hosted
binary PDF/index-build acceptance.

## Current-base ordering regression

The local native fixture uses the installed snapshot ACF initializer when present, records its actual priority and the current users-guard priority, then compares the selected credential's settings read against an unrelated credential on the same administrator. The old inventory priority10 returned200; priority20 returns403 while the positive control stays200 and anonymous users stays403. Authentication is real native HTTP; no reflected selected flag is used in this acceptance. On bare CI only, the local fixture supplies the same initialization-only null-return contract after MU loading; this is reported separately rather than called actual ACF. Native collection, alias, subrequest, malformed-binding, revocation and cookie controls remain unchanged. The local loader is removed after acceptance and never deployed.
