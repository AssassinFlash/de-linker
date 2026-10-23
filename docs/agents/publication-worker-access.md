# Publication worker credential scope

WooCommerce remains the product and publication authority. The engine and Genie
workers use native Application Password authentication to claim and acknowledge
jobs. A native application password otherwise inherits its user's capabilities;
WordPress does not assign a route scope to an individual key. This MU adapter
adds that missing boundary without a new account, role, secret binding or source.

`Linker\Mu\PublicationWorkerAccess::APP_ID` is the fixed, non-secret native
application purpose: `6c50fdd8-1640-4d5e-9ac8-05fefd9aa290`. Only the user/item
pair supplied by WordPress after successful native password verification can
select this purpose. The restriction is sticky from that verified pair even
when later authentication fails: Woo can resolve the user late, after core's
application-password error filter, and cookie initialization can turn the late
failure into anonymous access. Such a request must still be refused on public
routes. Only core's subsequent success hook can permit a jobs dispatch, and
native route permissions still decide its capabilities.
Query parameters, headers and JSON cannot select this purpose. Any
native application password created with this purpose receives the same scope.

The key permits exactly these top-level HTTP operations, subject to the existing
route's native capability and payload validation:

- `POST /linker/v1/publication/jobs/claim`
- `POST /linker/v1/publication/jobs/ack`

Every other route or method is refused, including source/manifest reads,
user/settings access, inventory/media reads, batch, embeds, method overrides and
internal `rest_do_request()` calls. A native HTTP authentication check permits
one dispatch only. The native root must have exactly one server `dispatch()` /
`serve_request()` pair in the call stack, with the native `serve_request()` on
the same server object directly calling `dispatch()`. An internal call before
the scope filter or during authentication is refused without consuming the
outer HTTP permission. A second server or nested `serve_request()` also fails.
This small structural check is necessary because core provides no dispatch-begin
hook that exposes the root request, and `is_dispatching()` is true for children
too. The trace explicitly excludes arguments; it is neither logged nor retained.
The restriction is applied at `rest_pre_dispatch` priority 20, after ACF's
priority-10 initialization that can return null. The MU registers when its file
loads, before regular plugins can determine the current user.

Other native credentials and cookie sessions retain their native behavior. The
adapter grants no capabilities, changes no roles or MFA policy, and stores no
binding. Native application-password creation and successful-use metadata are
retained. The existing inventory credential and its separately installed scope
MU remain in place.

## Provision and acceptance

1. Complete code review, local native fixture and deployment recovery-point
   gates. Deploy `mu-plugins/linker-publication-worker-access.php` as an MU entry
   before creating the new credential. Preserve the separately installed
   `linker-inventory-access.php` and its existing configuration.
2. Use `WP_Application_Passwords::create_new_application_password()` on the
   existing authorized administrator, with the exact `APP_ID` above. Keep the
   returned password and the native item UUID only in private deployment state.
   Record the user ID, item UUID and exact retirement command there. Do not
   print the password in a report, process argument, repository or issue.
3. Put the new native username/password into the private worker environment as
   `LINKER_PUBLICATION_USER` and `LINKER_PUBLICATION_PASSWORD`. Both workers use
   it only for the two jobs POSTs. Keep inventory's original read-only REST
   credential unchanged. Genie consumes `job.manifest`; protected publication
   PDFs use their current anonymous GET contract. The private REST JSON still
   supplies the authoritative site-origin comparison.
4. Verify the new key's jobs authentication and refusals before starting the
   workers. Non-job GET and POST canaries must show zero execution. Verify the
   original inventory credential still reads only its authorized collections.
   Then start both workers and read back actual claim, load and acknowledgement
   on the same current Woo source. Do not treat a created key or started process
   as runtime acceptance.

The local-only native fixture is included in `just mu-smoke <owned-instance>`.
For the narrow check, run from `mu-plugins`:

```sh
LINKER_MU_WP='just wp <owned-instance>' PHP=/opt/homebrew/opt/php@8.3/bin/php \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  --testsuite integration --filter PublicationWorkerAccessSmokeTest
```

It creates owned synthetic administrator/reader identities and native purpose
and ordinary keys. Temporary local-only callbacks provide native authenticated
receipts for the jobs routes and count non-job reads/writes without claiming or
acknowledging actual jobs. It checks concurrent credentials, cookie behavior,
method/route aliases, internal children before/after dispatch and during HTTP
authentication, other server instances, ACF initialization, late authentication
on a genuinely public WC canary and Store API paths, and precise key
retirement. It restores the exact previous MU files and removes its synthetic
users/options on completion. It never installs on a non-local site. A terminated
run can be cleaned with the fixture's `cleanup` argument before removing its
local loader; preserve any pre-existing MU file.

## Mandatory rollback order

This key belongs to an administrator. Removing its scope MU while leaving the
key valid restores the administrator's broad native REST authority. The rollback
order is therefore part of the credential contract:

1. Stop both automatic publication workers and prevent their automatic restart.
   Leave Woo pending jobs intact.
2. Revoke **only** the native item UUID recorded for this newly provisioned
   purpose, using `WP_Application_Passwords::delete_application_password()` or
   `wp user application-password delete <recorded-user-id> <recorded-item-uuid>`.
   Confirm the recorded item has this `APP_ID` before retirement. If multiple
   active keys were intentionally provisioned with this purpose, retire each
   recorded purpose UUID. Never revoke all of the user's application passwords.
3. Read back that the retired key no longer authenticates and that the old
   inventory key, user, roles and MFA remain intact. Remove the retired secret
   from the private worker environment; retain only the rollback metadata.
4. Only after retirement is proven, roll back or remove the publication scope
   MU and associated release code. Keep workers stopped until an accepted
   credential and compatible publication contract are installed again.

The production deployment owner records the private UUIDs and commands and
executes this order. The repository contains no production credential binding.
