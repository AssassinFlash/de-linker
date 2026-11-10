# Resource-load baseline (2026-11-11)

Domain-E evidence for the completion criterion "资源负载机制有前后实测数据证明有效".
Read-only: nothing was cleaned, restarted, or written to production.

Raw numbers: [`baseline.json`](baseline.json).

## Headline

**PR #1063 was merged into `main` with a net diff of zero lines.** Its own second
commit removed the fix the first commit added, leaving only test deletions. The
mail-throttle budget leak it claimed to fix is therefore still live, and it has
been reproduced today on a local instance at the exact saturation threshold the
PR described.

Two consequences for how this baseline must be read:

1. The `+21.43 h → 0 s` pair in the PR description is **not** a before/after
   measurement of working code. The "after" describes functions that do not
   exist in `main`.
2. `main` and production run the *same* mail files, byte for byte. Production is
   not behind: production is at the unfixed state because `main` is.

## What was measured, and where

| layer | source | captured (UTC) |
| --- | --- | --- |
| Hostinger shared host | `hostinger-de-linker`, read-only SSH | 2026-11-10 20:31 |
| Production WordPress | `wp` CLI + direct DB reads | 2026-11-10 20:34 |
| Engine VPS | `linker-services` (72.62.97.95), read-only SSH | 2026-11-10 20:34 |
| Local instances | `~/de-linker-local` + local MySQL | 2026-11-10 20:35 |
| Snapshots and backups | `~/de-linker-data` | 2026-11-10 20:35 |
| CI | `gh run list/view`, Actions cache API | 2026-11-10 20:38 |

## Mechanisms proven effective

- **M2 · Worker-orphan reconciliation (PR #1036, issue #1030).** `just down` now
  also stops a live `worker_host serve` bound to the instance. Checked today:
  **3 workers, 3 distinct live instances, 0 orphans** — each worker's
  `LINKER_PLANNER_CONFIG` points at an instance whose PHP, engine and genie
  ports all still listen (`review` 8889/8890/8891, `c222` 8925/8926/8927,
  `c332` 9187/9188/9189). Binding each worker to a live instance is a stronger
  check than counting processes, and it is the exact mechanism #1036 keyed on.
- **M3 · Production queue health.** Action Scheduler: 2807 complete, 17 pending,
  **0 overdue, 0 failed, 0 claims**; `linker_commerce_mail_attempt` has 130
  complete, 1 canceled, **0 pending**. The one-minute recovery heartbeat
  (`linker_inquiry_assessment_recover`) is scheduled and firing.
- **M4 · Deploy retention.** `deploy-prev` holds exactly one generation
  (`20261109T012936497720Z-2937f6347`); no `deploy` accumulation.
- **M7 · CI cache retention.** 7 cache entries / 798 MB, with
  `cache-retirement.yml` retiring caches of idle closed PRs.

## Mechanism proven ineffective

**M1 · Mail budget release.** `Throttle::release()` does not exist in `main`.
Neither does the timed-out `NativeAttempt` reclaim or the terminal-state
unscheduling the PR described.

Proof, reproducible from any checkout of `main`:

```
git diff 521843db8~1 985bf4c0d   # empty — the whole branch nets to nothing
git diff e26263441^1 e26263441   # empty — the merge adds nothing either
git show 521843db8 -- .../Throttle.php | grep -c release          # 1  (added)
git show 985bf4c0d -- .../Throttle.php | grep -c '^-.*release'    # 1  (removed)
```

Commit `521843db8` advertises the fix; commit `985bf4c0d`, titled "align
InternalSmtpTest expectations with the terminated-job lifecycle", deletes 459
lines across the same 14 files and reverts it. The resulting PR body still
quotes the fix's measurements.

### The reproduction

`linker_c222` carries exactly **64** PHP entries in
`linker_commerce_mail_transport_sends` — the same
`PER_DAY 80 − PHP_RESERVE 16 = 64` threshold the PR reported. Applying the
live `Throttle::slot()` formula from `main` to that ledger:

| quantity | value |
| --- | --- |
| entries in the PHP ledger | 64 (saturated) |
| oldest entry | 2026-11-10T10:08:19Z |
| computed `next_slot` | 2026-11-11T10:08:19Z |
| offset from now | **+13.51 h** |
| stalled `mail_attempt` actions pending | 62 |
| oldest of those pending | 2026-11-10 16:53:43 |

This is the defect the PR claimed to close, present in `main` and reproduced
from the shipped formula. `linker_c332` (21 entries) and `linker_review`
(12 entries) have not saturated yet, which shows the condition is
volume-dependent rather than permanent.

### Why production looks clean anyway

Production holds 38 `linker_mail_job` posts, all created in a 21-minute window on
2026-10-22 and all carrying `_linker_incident_hold`. They are deliberate incident
holds preserved by `NotificationHold`, not new accumulation, and they never
re-enter the throttle. Production's inquiry volume has not reached 64 PHP sends
in 24 hours, so the saturated branch has not been exercised there.

The risk is real and unmitigated: any burst reaching 64 PHP sends inside a
rolling day pushes `next_slot` a full day forward, exactly as `c222` shows.

## Still observational

- **M5 · Local instances: over limit.** 58 instance directories, 179 GB, 55
  registry entries — but only **3 instances actually running** (`review`,
  `c222`, `c332`), holding 28 PHP workers between them.
  `docs/agents/local-storage.md` allows one instance per in-progress task, plus
  one for baseline comparison, so 58 resident copies for 3 running instances is
  far past the boundary. Three directories are not even in the registry
  (`t113` empty, `t7` 183 MB, `t9-pre-stack-backup` 200 MB, both idle since
  2026-10-09). Local MySQL holds 55 `linker_*` schemas at roughly 76–89 MB each.
- **M6 · Local snapshots: over limit.** 18 database snapshots spanning eight
  days against a "3 recent + last 1 per day for 7 days + 1 baseline" rule; four
  each on 2026-11-06 and 2026-11-08. `~/de-linker-data` is 39 GB, including five
  finished-task site copies of 4–6 GB apiece.
- **M8 · Shared-node load attribution.** Node load is 38.68 / 74.22 / 71.02 on
  64 cores, but this account runs 6 `lsphp` processes at 0.0 % CPU each. That
  matches the 2026-11-10 baseline: the figure is other tenants' work.

Neither over-limit finding was remediated. This session is evidence-only, and
reclamation of a month of finished-task copies is the owner's call.

## Honest gaps

- M1 has no valid before/after pair. Its only "before" is a PR description of
  code that was removed before merge.
- The saturation reproduction is local. Production saturation is a hypothesis
  built on an identical formula and an identical 64-entry ledger shape, not a
  production observation.
- The 38 held production jobs were neither released nor deleted.
- One sample per host; no time series.
- A first pass of this document reported zero running local instances, because
  the process filter misspelled the real command line. The corrected figures
  come from reading `LINKER_PLANNER_CONFIG` per worker and matching listening
  ports against the registry. The wrong version never left this branch.

## Recommendation

Re-land the #1063 fix on a fresh branch with the revert commit dropped, and add
a regression test that fails when `Throttle` has no release path — the current
suite passes on a zero-line change, which is why this went unnoticed.
