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

## Metal-divider orphan Action Scheduler cleanup (2026-11-07)

- Production readback found 14 failed actions: one 2026-10-25
  `action_scheduler/migration_hook` and thirteen daily
  `hostinger-reach/jobs/cleanup_carts/start` occurrences. The logs named the
  exact cause on the newest and oldest entries: no callback is registered for
  that hook. No copy of the hook exists in the active plugin tree, and one
  future occurrence was still pending, so the schedule was orphaned and would
  continue accumulating one failed row per day.
- Before the write, a full metal-divider database export was taken through
  WP-CLI: 42,923,382 SQL bytes, locally compressed to 7,242,691 bytes, SHA256
  `1b9d577bd1b6679e8ccec51bbc504f15c12c9397757b4d1cc8ba57fd421b7ad9`. The
  temporary remote export and this single recovery copy were removed only after
  the queue and site readbacks below passed.
- Hostinger disables PHP `exec()`, which made the stock WP-CLI 2.12 `db export`
  command exit 255 silently because its option probe calls `exec()` before
  starting `mysqldump`. A temporary `/tmp` copy of the official phar changed
  only that probe to `false`; passing the documented `--no-tablespaces` flag a
  second time was also refused by MariaDB, so the export used the command's own
  default. The patched phar, remote SQL file, and local WP-CLI source scratch
  file were all deleted and verified absent. No database credential was read or
  logged.
- The orphan hook's scheduled actions were cancelled with Action Scheduler's
  native CLI, and the 14 backed-up failed rows were deleted
  (`Deleted 14 actions, 0 failures`).
- After-state: failed = 0 and pending occurrences of the orphan hook = 0. The
  remaining 13 pending actions are ordinary future WooCommerce/Action Scheduler
  jobs (first at 02:26 UTC); `https://metal-divider.com/` returned 200 in
  5.35 s. The production cron logs remain empty and no test inquiry or email
  was created.
