# Sibling-site load mitigation 2026-11-06 (sunriver-inverter.com)

Executor: main session. Source: `docs/research/2026-11-04-load-governance-readback.md`
fix item 3 (P1). These sites share the Hostinger account LVE quota (CPU/IOPS)
with de-linker.com; their background write storms were root cause C of the
historical IOPS 512 saturation.

**Result: DONE on sunriver main + /stg and metal-divider production scheduling.
Staging metal-divider intentionally has neither visitor nor external cron.**

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

## Metal-divider cron closure

- Direct production readback found `DISABLE_WP_CRON=true` on both
  metal-divider instances. The production hooks `md_inquiry_mail_tick` and
  `action_scheduler_run_queue` were due every minute, but the Hostinger
  account cron list contained only de-linker. Thus visitor cron was already
  disabled and the missing piece was the external trigger, not another
  wp-config change.
- Used the official Hostinger API MCP with its existing OAuth credential
  store. The official API list/create contract was verified from Hostinger's
  current documentation. No credential content was read or logged.
- Created production cron UID `6BcO1VYuYC`, schedule `* * * * *`, command:
  `/usr/local/bin/wp --path=/home/u388076051/domains/metal-divider.com/public_html cron event run --due-now --quiet`.
  A subsequent account list returned this exact UID, schedule and command.
  Rollback is the official `hosting_cron-jobs_delete` operation for that UID.
- Actual scheduling proof, not merely creation: `md_inquiry_mail_tick`
  advanced from 20:22:32 to 20:24:32 and then 20:25:32 UTC;
  `action_scheduler_run_queue` advanced from 20:23:57 to 20:25:57 UTC.
  `https://metal-divider.com/` returned 200 after those runs. No test inquiry
  or test email was created.
- Staging remains `DISABLE_WP_CRON=true` with no external cron. Its 32 dormant
  events include update, external-analysis and notification hooks accumulated
  since October; enabling a blanket every-minute runner would replay that
  backlog. No such runner was created.
- The pre-existing `/home/u388076051/.api_token` file was not read; its mode
  was tightened from 0644 to 0600 and read back.
