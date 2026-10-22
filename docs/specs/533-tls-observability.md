# Dedicated TLS gateway access observations

Owner-authorized observability repair, 2026-10-23. This supplies evidence for the
larger attack-defense work; it does not block attacks or choose a new rate limit.

The dedicated `linker-engine-tls.service` uses
`/etc/linker-engine-tls/nginx.conf`, not the shared `nginx.service`. Read-only
evidence found its configuration byte-equal to deployed source `3c3c3c25`, SHA256
`429b0505e291fe79351ae6476120c73196c8d5c38a268d44e385741ca633d2eb`.
Access logging was off. An empty last-hour journal therefore cannot establish
zero401/413/429/5xx requests.

## Contract

- Add one native Nginx JSON access schema: fixed route class, fixed method class,
  status, request duration, numerical request/sent bytes, and server-generated
  request correlation. Never copy raw URI/query, IP, body, headers or a supplied
  correlation ID into this record. Unknown paths/methods use fixed `other`/`OTHER`.
- Forward/return the generated request ID for correlation, without using it for
  authorization, budgets, model routing or customer identity.
- Use Nginx's native local syslog writer to the existing `/dev/log` journal
  socket. Do not reopen `/dev/stderr`: the effective systemd journal stream is an
  AF_UNIX socket, not an ordinary file/pipe. No new collector/service.
- Retain the existing private `error_log stderr warn` diagnostics. They can
  contain IP/raw URI, including synthetic canaries in the fixture. Only the new
  access payload has the field/privacy guarantee; never call the whole journal
  PII-free. Preserve process/configuration/TLS/HTTP failure diagnostics.
- Reuse the read-back existing persistent journal policy: SystemMaxUse1G,
  SystemMaxFileSize100M, MaxRetentionSec7day, MaxFileSec1day, Compressyes. These are
  existing operational settings, not new per-unit reservations or guaranteed
  observation duration. Do not change global journald, the unit or rate limits.
- A missing/full logging destination must not become an application prerequisite.
  Logging can lose records. Report retention/suppression/destination failures and
  the actual observation window; never reinterpret missing data as zero traffic.
- No mail, model, permission, authentication, request cap, DNS, firewall or shared
  proxy change. Existing engine6MiB/Genie30MiB proxy bounds remain unchanged.

## Operations and acceptance

The dedicated helper streams only the one configuration as a backup to the
operator machine. Require a private verified backup and original-byte SHA guard;
syntax-check a same-directory candidate, atomically replace, verify installed
bytes/syntax, then gracefully reload only `linker-engine-tls.service`. Never run
the broader network-boundary apply, restart a backend/shared proxy, or leave a
server-side backup. Rollback consumes only that known archive member and also
requires a current-hash guard. Stop on drift. A failed reload is not automatic
rollback; restore from the verified local archive explicitly.

Use the original539 native Gate/sink pattern but retain real TLS, a trusted
temporary CA/certificate, random loopback listeners and an owned Unix datagram
log socket. Prove both upstreams200/401/413, native429, unknown classifications,
synthetic502, exact correlation and access-canary absence. Separately prove the
old private errors and invalid TLS configuration remain diagnosable, and a
missing owned syslog socket still permits a normal200. No production backend,
model, mailer, ledger or live gateway configuration participates.

The coordinator owns independent full-diff reviews, release selection, verified
backup/activation and actual `linker-engine-tls` journal/tag/correlation readback.
Local fixture records do not establish production logging or any attack block.
