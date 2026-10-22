# VPS service and network boundary

Task: [VPS 源站直达与资源预算边界加固](https://github.com/AssassinFlash/de-linker/issues/539), within the full security-upgrade map. This source is based on the deployed `dcd5560d` release. The inquiry incident used the shared-host contact form; these VPS findings do not identify an additional exploited entry or establish a host compromise.

## Observed boundary, before this change

The 2026-10-22 read-only inspection found Ubuntu 24.04 and Python services, not a PHP installation. The project has its own `linker-engine-tls.service`, using `/etc/linker-engine-tls/nginx.conf` on IPv4 8443. The separate shared `nginx.service`, 8444 and VPN/proxy processes are unrelated and remain untouched.

IPv4 INPUT permits loopback and Hostinger's outgoing address `46.202.156.7` to TCP 8443, then drops other 8443 connections and all direct 8901 connections. Engine bound 0.0.0.0:8901; Genie bound 127.0.0.1:8902. Thus the engine's wildcard binding is an unnecessary second boundary dependency, not proof of anonymous internet access. A global IPv6 address exists and IPv6 INPUT is ACCEPT, but the project engine, Genie and TLS listeners have no IPv6 wildcard socket. No firewall policy is changed here.

All five actual engine POST routes and all nine actual Genie POST routes returned 401 to unauthenticated malformed JSON, both directly on loopback and through the project TLS proxy. Private engine `GET /resource/version` returned 401 without the existing service token and 200 with it, yielding a 64-hex version. A trusted malformed turn returned 422 without work/model dispatch. Engine's trusted malformed request without a resource subject returned 400. No paid request or real mail was issued.

The complete route inventory is asserted against native FastAPI routes in both `test_service_boundary.py` suites. No costly anonymous GET was found: health is readiness only, postcode reads bundled data, and engine version requires the service token. CORS is not treated as authorization. Default `/docs`, `/redoc` and `/openapi.json` were present on both applications.

Runtime controls already in effect: engine gate enforce; Genie work enforce with subject1/site2 slots; private provider enforce. Provider/work ledgers are persistent outside release directories in 0700 directories and 0600 regular files. Engine slots are likewise private. This patch retains the existing model routes, capacities, token, work/journal accounting and all business routes.

## Small changes and rationale

1. Bind engine only to 127.0.0.1. Its authorized network consumer is the existing local project Nginx upstream. Preserve port, environment, working directory and restart policy.
2. Disable unused FastAPI schema/documentation routes in both applications. Actual health, postcode, private version and every business endpoint remain. This reduces incidental interface disclosure; authentication remains the protection.
3. Track the project-only Nginx configuration. Replace its former global 4MiB request cap with the existing engine6MiB / WordPress Genie30MiB raw-request bounds from spec521. The prior value could reject legitimate commercial inputs and attachments before the service saw them. These are not new increased product allowances. Genie's native schema-derived cap is33,659,180bytes (base64 files plus reading/thread headroom), larger than the WordPress30MiB envelope; it remains unchanged.
4. Use HTTP/1.1 and `proxy_request_buffering off` to let native token/body gates inspect headers before a full unauthenticated body is spooled by the proxy. Native counted-stream caps remain authoritative, including chunked input.

All changes are below the WordPress browser/client boundary. No customer-facing copy, page layout or interaction is changed. Existing EN/DE native tool/fixture tests establish ordinary behavior; the proxy fixture establishes ingress behavior separately. No new model, credential, DNS, global SSH setting, firewall rule or shared proxy is introduced.

## Installation and rollback

The operator must first deploy the reviewed code release (so schema routes are actually absent), then use `services/engine/ops/network-boundary.sh` against only the dedicated project's two configuration files. It never installs into `/etc/nginx/nginx.conf` or restarts `nginx.service`.

Before apply, capture the existing configuration over SSH to a private local archive and verify its contents/hash. No archive is stored on the VPS. The commands below use the script shipped in the reviewed current engine release. The ordinary service-release rollback remains separate from configuration rollback.

```sh
umask 077
mkdir -p /Users/chesterjohn/de-linker-data/security-539
ssh linker-services 'bash /opt/linker-engine/current/ops/network-boundary.sh backup' > /Users/chesterjohn/de-linker-data/security-539/vps-before.tar
tar -tf /Users/chesterjohn/de-linker-data/security-539/vps-before.tar
shasum -a 256 /Users/chesterjohn/de-linker-data/security-539/vps-before.tar
ssh linker-services 'bash /opt/linker-engine/current/ops/network-boundary.sh apply'
# If any health/private version/tool readback fails, restore configuration:
ssh linker-services 'bash /opt/linker-engine/current/ops/network-boundary.sh rollback' < /Users/chesterjohn/de-linker-data/security-539/vps-before.tar
```

`backup` streams exactly `/etc/linker-engine-tls/nginx.conf` and `/etc/systemd/system/linker-engine.service`, retaining modes. `apply` syntax-checks the candidate before installing either, then checks installed syntax, reloads systemd, restarts only `linker-engine.service`, and reloads only `linker-engine-tls.service`. It reports failure if either is not active. `rollback` restores those two exact archived paths and runs the same service readback sequence. On a failed apply do not claim automatic rollback: invoke rollback with the verified local archive. The fixture verifies byte/mode restoration and preservation of the unrelated shared Nginx configuration.

After activation, inspect actual sockets, systemd effective command and project Nginx configuration; verify health/postcode, token-required version and every anonymous POST refusal, absence of schema UIs, allowed trusted normal tool paths and correct 6/30MiB ingress. A source file or successful syntax check alone does not prove installed runtime. The engine source snapshot changes on release; the existing live-version handshake correctly invalidates any older cached calculation result.

## Separate operational findings

Effective SSH permits root login and password authentication, has IPv4/IPv6 listeners, and no active Fail2ban service was found. Root coordinates account/key inventory, recovery access and a separate SSH policy change; this ticket does not blindly disable access to a shared host. Unattended upgrades and its timer are enabled; no reboot-required marker was present. Installed package versions were captured, but this is not a claim that every package is free of vulnerabilities or that no security update remains. No apt upgrade was performed.

Read-only tests and configuration changes cannot prove absence of compromise. Current unauthorized refusals do not prove every historical request was refused. The complete security goal remains open until root's deployment/readback, normal customer acceptance, host/SSH recovery and other map requirements are separately satisfied.
