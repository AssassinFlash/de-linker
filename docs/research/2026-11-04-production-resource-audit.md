# Production resource & load audit — root-cause diagnosis (read-only)

Date: 2026-11-04. Base: `main` @ `8c9e6d809`.
Method: read-only SSH diagnostics only (`ps/df/du/sar/journalctl/systemctl`, WP-CLI reads, SQL `SELECT`). No restarts, no writes, no deletes on either host. The Genie publish scheduler on `releases/8c9e6d809eec` (VPS current release `20261104T094242259491Z-8c9e6d80`) was not touched. Temp artifacts: one git worktree under `/tmp` (this branch), removed after push.

**Every item below states: measured magnitude → root cause → reaper status → growing or bounded.** Confirmed = directly measured or read in code/script on the host; Hypothesis = inferred, marked as such.

---

## 0. Executive summary

| # | Accumulator | Where | Magnitude | Root cause | Reaper | Verdict |
|---|---|---|---|---|---|---|
| 1 | Genie service release dirs | VPS `/opt/linker-genie` | 8 dirs, ~1.1 GB | `release.sh` retention regex `[0-9]{8}T[0-9]{12}Z` (fullmatch) no longer matches actual dir names `<timestamp>Z-<sha>` produced by the paired-release/publication-worker flow | Exists (`KEEP=3`) but **dead** — matches 0 dirs | **Growing, unbounded** |
| 2 | wp_options tablespace | Hostinger DB | 929 live rows / 8.1 MB data / **407 MB Data_free**, AUTO_INCREMENT 391,233 | High-frequency option churn: `RateLimit::take()` DELETE+INSERT IGNORE+UPDATE per Genie entry; per-entry browser-claim rows (leaked until #906 today); 1-minute cron/AS transient pairs; third-party transient rewrites. InnoDB never returns freed pages | Churn sources now individually bounded (hourly claim sweep live today; RateLimit self-purges; daily transient delete); **nothing reclaims the 407 MB tablespace** | Table growing? No — **bounded live**; tablespace static-bloated |
| 3 | Local index builds | Mac `~/de-linker-data/index` | 5.9 GB (builds 4.2 GB = 7 dirs; `embedding-cache.sqlite` 1.5 GB) | New ledger retention (`retain_builds`, keep current+1) only knows builds recorded in `publication-worker-releases.json`; 5 pre-/untracked build dirs never qualify for deletion | Exists, works for ledger-tracked builds only; **no backfill of orphans** | **Growing until orphans reclaimed; then bounded** |
| 4 | Planner releases | VPS `/opt/linker-planner/releases` | 348 MB stale (`.venv` 344 MB) + 34 MB current | Content-hash release names; planner deploy path has no retention at all (regex-based `release.sh` also wouldn't match) | **None** | **Growing with every planner deploy** |
| 5 | uv/pip package caches | VPS `/root/.cache` | 536 MB + 137 MB | Every release build runs `uv sync` into a fresh `.venv`; `uv cache prune` never run | **None** | Slow-growing |
| 6 | systemd journal | VPS | 403 MB | Dominated by xray per-connection access logs (11,081 msgs by 11:36 today); rsyslog additionally duplicates into `/var/log/syslog*` (syslog.1 = 107 MB) | Bounded by config (`SystemMaxUse=1G`, 1-day files, 7-day retention) — **working** | **Bounded at 1 GB** (proxy-driven, not de-linker) |
| 7 | Action Scheduler tables | Hostinger DB | 2,962 actions (2,908 complete), logs 8,582 rows / 1.5 MB | ~3,000 completed actions/month from 1-min recurring loop (`linker_i18n_translate`, AS queue runner) | WooCommerce default 30-day retention expected to engage now (oldest complete = Oct 4, day 31 today) — **pruning not yet observed** | Likely bounded; **verify in 2 days** |
| 8 | Local evidence/snapshot dirs | Mac `~/de-linker-data` | 36 GB total (see §4) | One-off incident/audit/cutover captures with no recorded retention bound | **None** | Static, unbounded by policy |
| 9 | Legacy personal files | VPS `/root` | `delta-main.bundle` 132 MB + small backup dirs | Pre-project proxy/infra leftovers | **None** | Static |

**Immediate danger: none found.** VPS disk 13% used (42 GB free), memory 2.7 GB available; Mac 1.2 TB free; Hostinger account 11 GB across 4 domains (plan quota not readable over SSH — unmeasured). The only quota-relevant bloat is the 407 MB wp_options tablespace.

**The load question:** the VPS is not under load (sar average 0.06 today on 1 vCPU; load 0.00 at measurement). The "high load" the owner saw is the **Hostinger shared node** (uptime load 33.79/56.30/57.77 over 55 days) — node-wide, shared with other tenants. Our account showed 2 idle `lsphp` workers at measurement time; **no evidence our site drives node load** (attribution beyond that is not possible from inside a shared host). Our constant contributor is the ~1/minute wp-cron/AS loop (see §3.4).

---

## 1. VPS `linker-services` — load, memory, IO: healthy

Measured 11:34–11:42 UTC:

- **CPU/load**: `uptime` 0.00/0.00/0.00 (1 vCPU, `nproc=1`). sysstat (collected every 10 min, files back to Oct 27): today's average load **0.06**, yesterday **0.05**, no sample above 0.33. Confirmed: no load problem on the VPS, at least since Oct 27 (owner's suspicion of "same origin as disk exhaustion" is **not confirmed for the VPS** — no resource pressure exists there now).
- **Memory**: 1.1 GiB used / 2.7 GiB available / **no swap configured**. Services: genie app 205 MB RSS, engine 208 MB, planner http 213 MB, planner worker 204 MB, judge worker 55 MB — ~890 MB total, stable since their Nov 4 restarts. Not a leak picture; processes restart on each release (genie started 10:00 today). No swap = OOM-kill risk if all services + a large index publish coincide; note, not measured as a failure.
- **IO** (confirmed, `/proc/diskstats` 168 s apart): +5,208 written sectors (≈2.6 MB) ≈ **16 KB/s**; reads negligible. PSI: no pressure lines for cpu/memory/io (all zero at sample).
- **Open FDs** (confirmed): genie 17, engine 8, planner http 8, planner worker 5, judge 5. No FD leak (the browser_claim leak class is not present at the process level).
- **Services/timers**: linker-engine, genie (+judge), planner-http/worker running; `linker-engine-feed-sync.timer` every ~15 min (last 11:28); `linker-engine-cache-clean.timer` weekly (Nov 2 last run — this is the existing cache reaper and it runs). No runaway cron loops; root crontab empty.
- **Journald** (confirmed): 402.9 MB used; config `SystemMaxUse=1G, MaxFileSec=1day, MaxRetentionSec=7day, Compress=yes` → bounded. Top writer today = **xray** (11,081 of ~20k messages by 11:36; per-connection access lines for the owner's personal proxy, unrelated to de-linker). rsyslog duplicates to `/var/log/syslog*` (syslog.1 = 107 MB, rotated by logrotate). `/var/log` total 590 MB.

### 1.1 Genie releases — reaper exists but is dead (root cause: name mismatch)

- Measured: 8 release dirs = 103+30+103+267+267+261+34+34 MB ≈ **1.1 GB**, created Nov 2–4 (≈2–3/day). `current -> 20261104T094242259491Z-8c9e6d80`.
- Root cause (confirmed, code read on host): `/root/linker-release/release.sh` prunes to `KEEP=3`, but `list_versions()` uses `re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", name)`; every actual dir carries a `-<gitsha>` suffix from the newer paired-release flow (`services/genie/ops/paired_release.py`), so **zero dirs ever match and nothing is ever deleted**. 8 > 3 proves the reaper is inert.
- Growth rate: every publish adds 34 MB (slim packaging) to 267 MB (fat packaging); ~0.1–0.5 GB/day at current publish tempo. Unbounded.
- Side note: several release dirs are owned by `501:staff` (Mac uid preserved by the uploader) — cosmetic, but consistent with the retention script never having governed these dirs.

### 1.2 Index generations — properly bounded (reaper working)

- Measured: `/opt/linker-genie/index/` = 3 dirs × ~283 MB = **847 MB** (Nov 3 20:36, Nov 4 08:51, Nov 4 10:00), `current -> 20261104T095926Z-546140000`, activation epoch 92.
- Root cause/design (confirmed, `services/genie/ops/index_release.py`): `KEEP=3` — "current one, the one a rollback returns to, and one [spare]" — enforced on every release (`for old in releases(root)[:-KEEP]: shutil.rmtree`). Expired half-uploaded leases also pruned (`_prune_expired_uploads`).
- Verdict: **bounded at ≈850 MB by design; currently exactly at bound. No action needed.**

### 1.3 Planner — no release retention; stale 348 MB

- Measured: `releases/08256b93…` = **348 MB** (344 MB `.venv`) vs current `releases/ae5e37e…` = 34 MB; systemd units symlink into the current release; the running worker pins expected runtime/execution/storage hashes to the current selection, so the old release is dead weight.
- Root cause (confirmed): planner releases use content-hash names and their deploy path has no retention mechanism at all.
- Also: `/opt/linker-planner/state/workspace/blobs` = **391 MB** — planner-owned permanent assets (`retention: "permanent"` validated in code); business data, **protect**, growth bounded by asset uploads.
- Genie/engine state SQLite: work.sqlite 16 KB, provider.sqlite 28 KB, engine state ≈5.5 MB — **no queue/retry accumulation on the VPS**. Genie turns live in WP postmeta (§3.3), not on the VPS.

### 1.4 VPS misc

- `/root/.cache`: uv 536 MB + pip 137 MB — grows with every release build (`uv sync` per release); `uv cache prune` never run. Semi-bounded, reclaimer absent.
- `/root` legacy (not de-linker): `delta-main.bundle` 132 MB (Jul 23), `codex-node-backups`, `hysteria-backups`, `nginx-backups` (KBs). Owner decision; outside this project's data.
- `/var/log/linker-engine-feed-sync.log` 2.1 MB, last write Nov 1 (service moved to timer+journal; log static). No logrotate entry for linker logs — currently irrelevant since new logs go to journald.
- `linker-wordpress-cron.timer` (unit file present, Oct 22): **disabled + inactive**; journal shows it ran ~every minute Oct 28 14:35 → Oct 31 12:29 (12,588 lines since Oct 25). Relevance to Hostinger cron in §3.4.

---

## 2. Hostinger `hostinger-de-linker` — the churn story

### 2.1 Load picture (confirmed measurement, unattributable node)

- `uptime` (shared node): load **33.79 / 56.30 / 57.77**, node up 55 days. This is the whole shared server, not our account.
- Our processes at measurement: **2 idle `lsphp` workers** (~52 MB each), 0% CPU. Node disk 21 TB / 62% used.
- Verdict: no evidence de-linker drives node load. Cannot be proven from inside a shared host (per-account LVE/CPU stats not exposed via SSH — unmeasured). Our floor contribution is the ~1/minute cron loop (§3.4): ≈1,440 PHP spawns/day ≈ 1 request/minute — modest next to a 30–50 load average.

### 2.2 wp_options — 407 MB of churn residue (root cause confirmed at mechanism level)

- Measured: **929 live rows** (exact `COUNT(*)`; the parent's "924" this morning is consistent), Data_length 8.1 MB, **Data_free 407 MB**, AUTO_INCREMENT 391,233 (parent's morning reading 390,875 → ≈350 rows inserted today by 11:42).
- Live churn measured: MAX(option_id) 391,226 → 391,228 (87 s) → 391,233 — ≈3–5 rows/min at a quiet late-morning window.
- Writers observed live in `option_id > 385000` (confirmed — these are rows written in the last hours):
  - `linker_genie_browser_claim_<md5>` — one row per cookieless Genie entry; **leaked until today's #906 fix**; hourly sweep + cursor now live (cron event `linker_tools_browser_claim_sweep` hourly; 2 live claim rows at check).
  - `linker_tools_limit_genie_entry_context.<hash>.<window>` — `RateLimit::take()` writes; the class DELETEs earlier windows on every take and re-INSERTs the current row (`INSERT IGNORE` — which consumes auto-increment space even when the row exists). Live rows self-purge; only 6 limit/claim rows live. Bounded by design, but each take is 3 statements of page churn.
  - 1-minute cron/AS pairs: `_transient_as_is_ensure_recurring_actions_scheduled` + timeout (rewritten every runner pass), `_site_transient_theme_roots`, `wp_theme_files_patterns-*`, `available_translations` (50 KB), `_transient_pll_languages_list`.
  - Third-party rewrites: `seopress_instant_indexing_log_option_name`, `_transient_seopress_results_page_speed*`, `_transient_windpress_scanned_apis/integrations_3.2.88`, `cky_banner_template` (57 KB), `_transient__woocommerce_helper_subscriptions`, big-value `_transient_dirsize_cache` (482 KB) and `_site_transient_feed_*` (425 KB / 105 KB).
- Historical magnitude (hypothesis, arithmetic only): AUTO_INCREMENT ≈391k over the site's ~31-day life ≈ **12–13k option-row inserts/day average**, vs ≈100k/day traffic peaks implied by the Oct 22 attack and the pre-#906 claim leak; exact decomposition is impossible without binlogs (unmeasured).
- Root cause of the 407 MB: InnoDB never returns freed pages to the OS; every insert/delete/rewrite cycle leaves the tablespace at its high-water mark. The table's *data* is 8 MB.
- Reaper status: all live-row sources are now individually bounded (claims hourly sweep — new today; RateLimit self-purge; `delete_expired_transients` daily — 20 expired lingering; Woo sessions 63 rows). **No reaper exists for the tablespace itself** (would need `ALTER TABLE … ENGINE=InnoDB` / optimize — a write, out of scope here).
- Same-pattern residue elsewhere: `wp_posts` 58 MB data + **83 MB free** (site-rebuild churn), `wp_woocommerce_sessions` 5 MB free, AS tables 4 MB free each. Cosmetically large, functionally re-used.

### 2.3 wp_postmeta — growing with Genie turns, reapers exist

- Measured: **37,694 rows / 41.8 MB**. Top: `_wp_attachment_metadata` 4.2 MB; `_linker_de_acf_json` 2.7 MB (+`_tv_legacy_acf_json` 2.6 MB + `_linker_de_source_acf_json` 2.6 MB — i18n per-post source snapshots); `linker_genie_quality` 689 rows / 1.1 MB; `linker_genie_turn` 676 rows / 1.0 MB; genie/browser-family rows total **6,311**.
- Reaper status (confirmed in cron): `linker_tools_conversation_sweep` (daily), `linker_tools_reply_cleanup` (hourly), `linker_tools_browser_claim_sweep` (hourly, new), `linker_tools_planner_claim_sweep` (hourly). Genie turn/quality growth ≈2k rows/month — modest; whether conversation sweep's bound matches retention intent for turn history is a business question, not a defect finding.

### 2.4 Action Scheduler & cron

- Measured: `wp_actionscheduler_actions` 2,962 rows (2,908 complete / 14 pending / 0 failed / 1 canceled), `wp_actionscheduler_logs` 8,582 rows / 1.5 MB. Oldest complete 2026-10-04 — exactly the site relaunch, i.e. **no pruning has occurred yet** (day 31 today). Woo's default 30-day retention should start deleting Oct-4 rows on the next passes — reaper *presumed present but not yet observed*; verify in 1–2 days (unmeasured).
- `wp cron event list`: **46 events, all with sane future next-runs** — nothing stuck rescheduling into the far future, no backlog pile.
- The 1-minute loop: `action_scheduler_run_queue` (1 min) and `linker_inquiry_assessment_recover` (1 min); the observed most-frequent completer is **`linker_i18n_translate`** (completions at 11:38:00, 11:39:06, 11:40:04) — the German auto-translation loop runs per-minute actions. This is the single largest *deliberate* driver of both PHP executions and option churn.
- Cron driver (partially confirmed): `DISABLE_WP_CRON=true` in wp-config; no user crontab over SSH; the VPS-side `linker-wordpress-cron.timer` that used to curl `wp-cron.php` every minute was disabled Oct 31 12:29 — **yet AS actions still complete every minute**, so another driver exists, almost certainly an hPanel cron job (not readable over SSH — unmeasured). Recommend confirming in hPanel.

### 2.5 Files, caches, logs, other domains

- `wp-content`: uploads **4.0 GB** (2026/05 208 M, 07 1.0 G, 08 804 M, 09 1.3 G, 10 729 M, 11 1.5 M — product/blog media, business data, protect); plugins 458 MB; languages 27 MB; themes 18 MB.
- LiteSpeed cache: **96 KB / 12 files** — a non-factor. `redis-cache` plugin is active **but `object-cache.php` is disabled** → no object cache in front of the churning options reads; its `rediscache_discard_metrics` cron still runs hourly. Not a resource leak; noted as config inconsistency.
- Logs: `wc-logs` 956 KB (dated files, rotated naturally), `linker-errors` 480 KB + `linker-fatals-*` 440 KB (7 files), no `*.log` >2 MB anywhere under the domain. All bounded.
- i18n/outbox queues: no outbox or i18n-queue options/tables found beyond `litespeed.purge.queue2` (len 2) and static one-time `linker_i18n_*_backup` options (≈1.8 MB total, permanent restore points). No retry accumulation.
- Account total 11 GB: de-linker.com 4.6 GB, sunriver-inverter.com 2.6 GB, metal-divider.com 2.2 GB, staging.metal-divider.com 1.2 GB, ~70 MB of stray pre/post-deploy backups in `~/` (`deploy-prev` 40 MB, several `.sql.gz`/`.tgz`). Hostinger plan quota could not be read over SSH (unmeasured).

---

## 3. Local Mac

Disk: 1.2 TB free of 3.6 TB — no danger. Accumulators per §0 table items 3 & 8:

- `~/de-linker-data` **36 GB**: `privacy-visual-20261021` 6.4 G (audit scripts/artifacts), `index` 5.9 G (§ item 3), `incident-20261022` 5.2 G (**unique attack-forensics evidence — protect**), `judge-models` 4.6 G (weights in use), `cutover-20261021-2259` 4.2 G + `20261021-1023` 4.2 G (**recovery points / unique evidence — protect until superseded**), `pdf` 2.0 G (**knowledge-base source PDFs — protect**), `vps-recovery-*` **2 × 454 MB (duplicates — keep one after verify)**, `apify-oem` 508 M, `planner-production` 401 M, `parsed` 300 M, small recent dirs.
- `~/de-linker-ops` 1.7 G: essentially `knowledge-worker/releases` 1.7 G — worker release artifacts; check retention with the worker's own ledger policy (same class as item 3).
- Repo `.scratch` **3.5 GB**: `wt-matrix` 3.0 G (a full working-tree matrix incl. 2.4 G docs copy — reclaimable when the matrix effort closes), `t16-*` ≈450 M (Oct session artifacts; only referenced by historical acceptance records such as `docs/acceptance/2026-10-16/a3-final/README.md` and closed debt registries — no code dependency), `m2`/`m2b`/`a3-final` <0.5 M (same historical references).

---

## 4. Prioritized remediation proposal (nothing executed — all need owner write approval)

Bounds follow AGENTS §0: reapers must have an explicit retention number; recovery points and unique evidence are protected.

**P1 — Fix Genie release retention (stops the only unbounded VPS growth).** Change `release.sh` (and/or its repo copy `services/genie/ops/release.sh`) to accept the `-<sha>` suffix, or move retention into the paired-release flow that creates the names. Bound: keep current + 1 rollback (KEEP=2 suffices given slim 34 MB releases). Reclaims ≈0.8–1.0 GB immediately and caps the dir at ≈70–600 MB. Protect: `current` (8c9e6d80) and the release the live publish scheduler pins.
**P2 — Planner release retention.** Delete stale `08256b93…` (348 MB) after confirming units/pins all resolve to `ae5e37e…` (verified true at audit time); add "keep current only" to the planner deploy (its releases are content-addressed; no rollback-by-name exists anyway).
**P3 — Local Mac reclamation (~13–16 GB).** One-time backfill sweep of pre-ledger index builds (keep the two ledger builds; delete `20261016*`, `20261018*` and today's superseded 4 → ≈2.9 G); dedupe `vps-recovery-*` (454 M); review/archive `privacy-visual-20261021` (6.4 G) to compressed evidence storage; reclaim `wt-matrix` (3.0 G) and `t16-*` (450 M) per §0 with the referenced acceptance docs updated to point at retained evidence. Protect: `pdf`, `incident-20261022`, both cutover recovery points, `judge-models`.
**P4 — uv/pip cache prune** (`uv cache prune`, ≈400–600 MB) + add to the release script cadence.
**P5 — wp_options tablespace rebuild (one write op, quiet window).** Only after 1–2 weeks of post-#906 churn observation; `ALTER TABLE wp_options ENGINE=InnoDB` (or `wp db optimize`) with the §5 pre-backup; reclaims ≈400 MB of quota. Not urgent: freed pages are re-used by new churn.
**P6 — AS retention check (2 days later).** If Oct-4 completed actions are still present after Nov 6, Woo's 30-day pruning isn't active — configure `action_scheduler_retention_period` explicitly. Expected bound: ≈1 month of actions ≈ 3–5 MB.
**P7 — Journal bound (owner call — proxy-related).** `SystemMaxUse=1G` is generous for a 1-CPU box whose journal is 95% xray access lines; 200–250 MB would hold all Linker service history comfortably. Alternatively silence xray access logging.
**P8 — Cron hygiene (verify, then maybe tune).** Confirm in hPanel what calls wp-cron now; record it in ops docs. The `linker_i18n_translate` per-minute cadence is the main deliberate churn/load floor — if business-acceptable, batching to 5-minute intervals cuts AS option churn and PHP spawns ~5×. Optional: reconcile `redis-cache` plugin active vs `object-cache.php.disabled`.

**Config risks flagged, not fixed:** no swap on the VPS (OOM exposure during concurrent publish + traffic); release dirs owned by uid 501.

---

## 5. Could not measure (honest list)

- Hostinger per-account CPU/EP/LVE usage and plan quota; hPanel cron definition (not exposed via SSH) — the current wp-cron driver is inferred, not proven.
- MySQL binlogs / historical query mix → the decomposition of the 390k option-row churn across writers is a mechanism-level confirmation with an arithmetic-only magnitude split.
- Whether Woo's 30-day AS retention actually fires (needs a re-check after Nov 6).
- VPS sar history before Oct 27 (sysstat files start Oct 27) — cannot rule out earlier load spikes.
- Node-load attribution on the shared host (other tenants dominate; our floor is one PHP spawn/minute).

## 6. Resource report (AGENTS §0)

Read-only on both production hosts; nothing created, restarted, or deleted there. Locally: one git worktree `/tmp/audit-wt` (this branch, removed after push) — sole artifact of this audit, removed on completion. No processes left running; no browser instances opened. Disk impact of the audit itself: this report file only.
