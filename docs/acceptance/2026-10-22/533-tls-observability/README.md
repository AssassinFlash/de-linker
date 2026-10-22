# Dedicated gateway logging — local/native evidence

Source base: `3c3c3c25fff1d6b6f1aed8a990a410cfd9149577`. No production activation.
The independent research commit927a4d20 is not part of this branch.

## Actual checks

- Before implementation, the new deployment tests failed2/5 because the helper
  was absent. Final dedicated helper plus existing network-boundary tests:
  **7 PASS**. Real temporary files/tar prove backup, original-hash refusal,
  syntax-failure refusal without reload, atomic installation/mode preservation,
  known-member-only rollback and no shared/backend service changes.
- Changed Python Ruff/type checks PASS; complete engine source mypy PASS29files;
  Bash syntax PASS. No broad paid/production/customer test was run.
- The exact unactivated candidate passed installed Nginx1.24 syntax checking.
  The native probe retained TLS1.2/1.3, trusted its temporary self-signed CA and
  used installed native Gate classes followed only by synthetic byte-count sinks.
- Against the deployed configuration, all9 request cases completed but access
  records were0: the probe failed `(0,9)`, rather than reporting zero attacks.
- Against candidate SHA256
  `a8ced23783a525371e8390c84cee9fef373b2878a8c1a185d712212a11d9e2dd`,
  **9 requests /9 actual native syslog records** passed: engine and Genie each
 200/401/413; real native engine slot429; unknown method/path200; stopped
  synthetic engine upstream502. Client-supplied request ID was overridden;
  response/upstream/log IDs matched, and query/body/header/path canaries did not
  appear anywhere in the new syslog messages.
- The private native error stream still contained oversized/connect diagnostics
  and synthetic query context. A missing TLS certificate failed native `nginx -t`
  with its diagnostic. This explicitly does not claim the whole journal is free
  of personal data. Removing only the owned syslog socket still allowed200 from
  the synthetic Genie upstream.
- All fixture processes/runtime trees and the owned uploaded source directory
  were removed. Production configuration remained SHA429b0505…d2eb; dedicated TLS
  MainPID731 was unchanged and engine/Genie/TLS were active. This does not infer
  unchanged backend PIDs without a matching before observation.

Raw native RED/GREEN, effective unit/retention and cleanup evidence remain
private under `incident-20261022/tls-observability-533/` and `attack-continuity/`.
The fixture deliberately sends no message to real `/dev/log`; its local Unix
datagram sink verifies native syslog output, not production journal attribution.

## Safe coordinator activation and rollback

Do not activate while this observability work is held behind attack blocking.
After reviews and release selection, use the helper from that reviewed release.
The commands name the dedicated gateway only; do not use the broader
`network-boundary.sh apply`, which also restarts the engine.

```sh
umask 077
mkdir -p /Users/chesterjohn/de-linker-data/tls-observability-533
ssh linker-services 'bash /opt/linker-engine/current/ops/gateway-logging.sh backup' > /Users/chesterjohn/de-linker-data/tls-observability-533/before.tar
tar -tf /Users/chesterjohn/de-linker-data/tls-observability-533/before.tar
tar -xOf /Users/chesterjohn/de-linker-data/tls-observability-533/before.tar etc/linker-engine-tls/nginx.conf | shasum -a 256
```

The archive must contain exactly the known configuration and the hash must match
the current effective source inspected for this release. The observed baseline
was429b0505…d2eb; stop and re-review if it drifted. Apply supplies that full
verified hash, not the abbreviated text. Rollback likewise supplies the actual
current installed candidate hash and streams this local archive to the helper.
Neither operation changes the unit, global journal, firewall or shared Nginx.
`apply` failures after replacement leave a validly tested candidate on disk;
they are not a successful activation or an automatic restoration. Read the
installed hash, keep the backup and explicitly restore on release failure.

Read back the effective dedicated configuration, service MainPID and active
state. Observe a harmless authorized health/private-version path using the
existing verified TLS channel; do not send an engineering/model/mail request.
Read actual journal JSON from `linker-engine-tls.service` with identifier
`linker_tls_access`, matching status and the returned generated request ID. Keep
the full journal private. Confirm attribution and that the receiver retained
the new schema, rather than crediting the isolated socket fixture as activation.
Record the activation time and any suppression/retention/socket errors before
using records to calculate an observation-window count. No hour of old traffic
can be reconstructed from access logging that was disabled then.

## Primary references

External documentation was fetched only through Apify. Run
`3wFuLGvOvCNoUcAdh`, dataset `V7kp2y2sNEahcGRNq`: native
[Nginx log format](https://nginx.org/en/docs/http/ngx_http_log_module.html),
[map](https://nginx.org/en/docs/http/ngx_http_map_module.html),
[systemd journal streams/rate behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html)
and [journal retention](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html).
Run `zNtU8CnPTqkealBY3`, dataset `zywXlUSIix5rEHQMi`: native
[Nginx local syslog](https://nginx.org/en/docs/syslog.html). The attempted raw
source URL produced no dataset item and is not used as evidence.

No customer UI/copy/CSS changed. Full-diff independent reviews, exact release
checks and coordinator-owned activation/readback remain pending; no production
defense or successful physical inbox claim is made here.
