# Production resource baseline (read-only, 2026-11-10 20:45 local)

Domain-E evidence: the "before" numbers every later resource mechanism must be
judged against. No cleanup was performed; nothing was written to production.

## Engine VPS (`linker-services`, 72.62.97.95)

| metric | value |
| --- | --- |
| uptime | 23 days |
| load average | 0.07 / 0.03 / 0.01 (1 core) |
| memory | 1118 MB used of 3915 MB, 2796 MB available, no swap |
| disk `/` | 5.4 G of 48 G (12%) |

Resident services (exactly one of each, no accumulation):
- `uvicorn linker_engine.application` port 8911 (planner, linker-* user, release 09f80a35)
- `worker_host serve` same release, one instance
- `uvicorn linker_engine.application` port 8901 (engine, root, /opt/linker-engine/current)
- `uvicorn linker_genie.app` port 8902 + `linker_genie.quality.worker` (genie)

Top CPU consumers are unrelated system agents (xray, monarx, qemu-ga).

## Hostinger shared host (`hostinger-de-linker`, 46.202.156.7)

- Node-wide load average 32.23 / 49.74 / 43.91. This is the whole shared
  node, not our container: our account runs 8 processes (7 lsphp), each at
  single-digit %CPU. No runaway process of ours.
- Account disk 11 G under `/home/u388076051`:
  - `domains/` 11 G — de-linker.com 4.6 G, sunriver-inverter.com 2.6 G,
    metal-divider.com 2.2 G, staging.metal-divider.com 1.2 G
  - de-linker.com: `wp-content/uploads` 4.0 G, of which `uploads/2026` 4.0 G
    (09: 1.3 G, 07: 1019 M, 08: 804 M, 10: 729 M) — 19,255 files against
    2,760 registered attachments (normal WP size-variant fan-out, not orphans)
  - `deploy-prev` 40 M with exactly one dated generation + `latest` — the
    "keep only the previous version" discipline holds
  - `backups` 284 K, `.dbdumps` 4 K, `logs` negligible — no backup hoarding

## Findings

1. No production resource emergency exists on either host; the shared-node
   load figure is other tenants' work, outside our control and below any
   action threshold for our account.
2. The only lifecycle item closed today is #1036 (local worker orphans,
   PR #1036): its "before" evidence is the 10-hour orphan on review;
   the "after" is the regression-tested reconciliation in `just down`/`serve`.
3. uploads growth (729 M in month 10) tracks the media library; retention of
   unattached media is a content decision, not a load defect — recorded, not
   actioned.
