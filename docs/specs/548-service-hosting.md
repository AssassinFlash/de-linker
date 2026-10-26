# Hosting the private planning protocol with the site engine

Date: 2026-10-23. This increment connects the reviewed private factory to a
deployable ASGI entry and the owned local runner. It does not establish the
WordPress identity/admission gateway or public application acceptance.

## Contract

1. `linker_engine.application:app` routes the bare `/planning` and every
   `/planning/…` request to the private app before the old engine's Gate or
   CORS middleware. Existing routes retain their application and lifespan.
   Authenticated planning calls do not acquire a legacy numerical slot.
   Private OPTIONS/HEAD/unknown paths cannot inherit public CORS or redirects.
2. Runtime settings come from the file named by `LINKER_PLANNER_CONFIG`.
   Its version, absolute private directory, all HTTP/CSV/page/depth/interval/
   attempt limits and arithmetic tolerances are mandatory, strict and finite.
   There is no credential in this file. The existing service environment
   supplies `GENIE_SERVICE_TOKEN`; no authentication-off mode is introduced.
3. Missing, invalid or failed private initialisation closes the private
   protocol with `503 service_unconfigured` and private cache headers, without
   consuming customer input or bringing down the existing site engine.
   Operational logs retain the failure; no raw configuration escapes in HTTP.
   Readiness must probe authenticated `/planning/version`, not only `/health`.
4. Version metadata includes the effective HTTP limits. `/identity/status`
   reports only whether the currently asserted principal is active or retired;
   it does not accept a different subject or reveal the claiming account.
   This enables a native gateway to rotate an obsolete guest session rather
   than continue advertising a retired owner. Project/run access remains denied.
5. `linker-local serve` creates each instance's private runtime file once,
   atomically, preserving an operator's subsequent values. It starts the
   combined entry on that instance's existing engine port and writes
   `linker_planner_url` only after authenticated readiness succeeds. No other
   instance's process, workspace or credential is used.
6. The managed planning HTTP/worker pair uses a separate loopback listener
   (8911 on the services host) and release namespace. The dedicated nginx
   planning location forwards the same private path to this pair. Existing
   engine/Genie listeners and public routes retain their current owner. The
   transport location sets private headers even on its own errors. Production
   changes still require backup, configuration validation, process draining
   and real readback; an isolated host review does not publish this routing.

## Paired release lifecycle

`services/engine/ops/planner_release.py` operates an explicitly prepared
namespace, independently of the generic engine/Genie deployment. Every retained
release contains its source and an environment built at that immutable path,
plus `.deploy/spec.json`, `runtime.json` and `worker.json`. The strict release
specification supplies schema version 1, absolute root/release paths, a
`linker-planner` service prefix matching the root name, explicit port, dedicated
non-root user and finite positive start/stop budgets. Operational budgets are
deployment policy, not engineering limits or production capacity evidence.

`prepare SPEC --source-environment ENV --publication-url URL` freezes both
policies, the service configuration and executable identity. It verifies that
the actual service UID can construct the site's source loader before admitting
the candidate. A root-readable source alone is insufficient. The publisher
exposes only the public Woo projection generation as directories `0755` and
files `0644`, including an initial retained rollback pair; private workspace,
cache and service credentials retain their separate permissions. No new fact
authority is created. The source paths still identify the current Woo-derived
feed/contract generation and the publication endpoint still validates current
permissions. Remote publication endpoints require credential-free HTTPS;
literal HTTP loopback is allowed for a private local authority.
If an owned local authority is reached through SSH forwarding, preserve its
original origin (including port). The existing exact-origin URL reconciliation
does not treat an arbitrary forward address as the authority's upload origin.

`activate SPEC` drains the current queue with its own retained executor, then
starts and verifies the matched HTTP/worker pair before reopening admission.
It checks live source paths, systemd fragment/override ownership, process cwd,
listener PID, invocation ID, runtime, execution and storage identity. Only the
owned loopback socket receives the HTTP service token. The numerical worker
receives public source settings without service, publication-writer, research
or model credentials. The two boot dependencies point through stable unit
links, so retiring a release cannot leave reboot wiring attached to its files.

`status SPEC`, `rollback SPEC` and `stop SPEC` use the same ownership and drain
boundaries. A stopped old worker recovers its own pending jobs before replacement;
failed activation restores the previous selector and matching pair. Successful
replacement retains the current release and one rollback. It refuses storage
schema changes that lack a separate migration plan. It never changes WordPress,
the public proxy, the existing engine/Genie service or product data.

## Explicit local policy

The owned development runner creates a 16 MiB JSON / 8 MiB CSV policy, page
ceiling 100, JSON nesting 32, 100,000 aligned intervals and two attempts.
These are adjustable development resource ceilings, not engineering rules,
an assertion of production capacity or a definition of commercial/European
scope. Base64 CSV plus provenance fits within the declared JSON headroom.
Production limits must be exercised with actual intended workload and matched
across WordPress, transport and the private app before release.

The arithmetic settings are the existing independently verified replay
settings: absolute energy 1e-7 kWh, absolute power 1e-7 kW and relative 1e-9.
Their role is floating-point checking, never an installation safety margin;
the handler freezes them into its manifest. No device efficiency, usable
capacity, physical clearance or country rule is defaulted by this config.

## Evidence required

Use the actual composed apps: private methods/paths/preflights fail before old
Gate/CORS; legitimate private create/read persists to the same CAS/SQLite;
legacy health, CORS and POST protection still execute. Test invalid config,
private initialisation failure, lifecycle forwarding, strict policy fields,
runtime-file privacy and preserved operator changes. Then verify the owned
local service's real HTTP readiness. None of these tests proves a browser's
native identity, public admission or a production deployment.

## Increment verification

The composed service and private HTTP tests pass (55 tests); the full engine
suite passes (406 tests). The local runner's seven service tests, Ruff and
strict mypy pass. `just serve p548` started the owned instance's combined
engine on port 9348 and its authenticated planning readiness succeeded before
the WordPress option was written. Its Genie remains on port 9349 with the
existing index; no shared instance was restarted.

The candidate nginx file passed `nginx -t` on the actual services host's
nginx 1.24.0. The file was supplied through an anonymous seekable file
descriptor; no installed configuration was overwritten or reloaded. A pipe
at `/dev/stdin` was unsuitable because nginx rereads the configuration. This
is syntax/host-path validation, not production installation or acceptance.
