# Sibling-site load mitigation 2026-11-06 (sunriver-inverter.com)

Executor: main session. Source: `docs/research/2026-11-04-load-governance-readback.md`
fix item 3 (P1). These sites share the Hostinger account LVE quota (CPU/IOPS)
with de-linker.com; their background write storms were root cause C of the
historical IOPS 512 saturation.

**Result: DONE on sunriver main + /stg. Deferred: metal-divider cron change
(no shared-host crontab available).**

## Before-state (read this session)

- Main: `xqs_download_log` **409,867 rows** (up from 387,214 on 11-04 —
  still growing ~1k/day), `xqs_sgs_log_events` 13,795 rows, `sg-security`
  1.6.2 active.
- /stg clone: `xqs_download_log` **266,099 rows**, `sg-security` active.
- Error log `~/.logs/error_log_sunriver-inverter_com` still recording the
  documented sg-security × TranslatePress `gettext` error-callback loop
  (last burst 2026-11-04 21:53 UTC: `Commands out of sync` SELECT/INSERT
  into `xqs_trp_gettext_original_strings` on every unknown-IP visit).

## Actions (with pre-change backup)

1. Table-level backup to local before any write:
   `~/de-linker-data/backups/sunriver-logs-20261106/{main,stg}-logs.sql.gz`
   (13 MB + 7.6 MB, `gunzip -t` verified; mysqldump --single-transaction of
   `xqs_download_log`, `xqs_sgs_log_events`, `xqs_sgs_log_visitors`).
   Recovery point for this change only; recycle after the next weekly
   full backup or 7 days, whichever comes first.
2. `wp plugin deactivate sg-security` on both sites (SiteGround-only plugin,
   non-functional on Hostinger; the deactivation also removes its weekly
   SiteGround report mail and every-visit log writes). Deactivate only —
   nothing deleted; reversible with one command.
3. `TRUNCATE` the three log tables on both sites.

## After-state (all read back)

- Both sites: `download_log` count = 0; combined size of the three tables
  **409,867+266,099 rows → 0**, table bytes → **0.11 MB** (frees ~215 MB of
  the shared MySQL; research doc's estimate confirmed).
- `sunriver-inverter.com/` → 200; `/stg/wp-login.php` → 200 (`/stg/` root
  404 is pre-existing behavior, unrelated to this change).
- `sg-security` inactive on both sites (`sg-cachepress` was already
  inactive). No new entries in the sunriver error log after deactivation —
  the `gettext` error-callback loop is starved of its trigger.

## Deferred with reason

- `metal-divider.com` `DISABLE_WP_CRON=true`: `crontab` does not exist on
  this Hostinger shared host (`bash: crontab: command not found`), so the
  every-minute `md_inquiry_mail_tick` / `action_scheduler_run_queue` hooks
  have no CLI-cron replacement path via SSH. Disabling visitor cron without
  a replacement would stop that site's inquiry mail sender. Blocked on an
  hPanel-panel cron entry (manual step), not on code.
- `staging.metal-divider.com` stale cron events: same constraint.
