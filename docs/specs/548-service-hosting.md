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
6. The production service entry and dedicated nginx planning location carry
   the same path. The transport location sets private headers even on its own
   errors and preserves all other routes. Production changes still require
   backup, configuration validation, process draining and real readback.

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
