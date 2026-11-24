# Site outage alerting

The site probe records; this notifier speaks. They are two units on purpose:
the probe is the measurement and never sends, so a broken mail path cannot stop
the record, and the notifier can be replaced without touching the probe.

## Five-minute readings

Each completed cycle appends one line to `/opt/linker-engine/state/site-probe.log`:
`UTC_TIMESTAMP WORDPRESS ENGINE PLANNER GENIE`. The log keeps the last 2,016 cycles.
Older two-column lines remain WordPress observations. A connection failure is
`000`; a backend that sends HTTP 200 with an invalid health response is
`200/invalid`.

| Target | Request | Healthy result |
| --- | --- | --- |
| WordPress | `https://de-linker.com/wp-json/` | HTTP 200 from the database-backed site |
| Quick Engine | `http://127.0.0.1:8901/health` | HTTP 200 with `status: ok` |
| Planner HTTP and worker | `http://127.0.0.1:8911/health` | HTTP 200 with a readable SQLite schema and a live worker on the same runtime and workspace |
| Genie API | `http://127.0.0.1:8902/health` | HTTP 200 with `status: ok` |

The Planner worker holds a lock on the file it publishes after initialization and updates it at the configured heartbeat
interval while idle or executing a job. A missing worker, a heartbeat older than its lease, or an unreadable
workspace returns 503. The response includes the running computation version.
The probe uses the dedicated loopback listener; the public proxy keeps
`/planning/` behind the private project RPC boundary.

A backend opens its own incident after three consecutive failed readings
and sends one recovery on its first healthy reading. A second service can
therefore raise its own alert during an existing incident. The monitor
retains the WordPress outage state, the single whole-probe silence alarm,
and the single daily healthy heartbeat across the upgrade.

## Thresholds, and where each number comes from

- `FAILURES_BEFORE_ALERT = 3`. The outage ran about nine five-minute cycles.
  The probe's surviving record of it holds two failing cycles (01:10:03 and
  01:15:27, both `000`) because the probe was installed at 01:09 UTC, near the
  end. Across the 89 cycles recorded between 01:10 and 08:37 UTC the gap
  between readings has a median of 310 s, p95 of 332 s and a maximum of 340 s,
  so three consecutive failures always span at least ten minutes of wall clock
  and still fire inside one third of the smallest real incident on record.
- `SILENCE_AFTER_S = 1200` (20 minutes). 3.5× the worst measured gap: a late
  timer cannot fake silence, and three missed cycles cannot be lateness. A
  probe that dies writes nothing, which is indistinguishable from a quiet
  healthy log — the exact shape that hid the original outage.
- `HEARTBEAT_S = 86400`. One line a day while the site is healthy. It is the
  only watcher for this notifier: no second vantage exists, and the WP-side
  digest cannot report that the site is down.

## Channel

Authenticated SMTP submission from the engine host (`smtplib`, 465/SSL by
default). Measured 2026-11-11 on the VPS: no local MTA is installed at all
(sendmail, msmtp, mail, mailx, ssmtp all absent), while `smtp.hostinger.com:465`
accepts a connection. The site's PHP `mail()` is never used: the shared host is
the thing being watched, and its 10/minute and 100/24 h budget belongs to
customer mail (AGENTS.md §4).

Recipient: `sales@sunriverinverter.com`, the 2026-10-17 ruling that internal
notifications go there and not to `sales@de-linker.com`. `LINKER_ALERT_TO`
overrides it for a test address.

## States

`ok`, `down`, `silent`, kept in `state/site-alert.json`. A message is sent when
the state changes, never while it persists:

| From | To | Message |
| --- | --- | --- |
| ok / unknown | down | `SITE DOWN`, naming the first failure, the span and the codes |
| down | ok | `Site recovered after …` |
| ok / down | silent | `Site probe stopped reporting` |
| silent | ok | `Site probe reporting again` |
| ok (no change) | — | one heartbeat a day |

A failed delivery stays in the state file's `pending` list and is retried on the
next cycle; the flip is not re-detected, so a retry cannot duplicate an alert.
That list keeps the newest eight messages only: a site that flaps faster than the
mail channel recovers would otherwise grow the file without bound, and the
current state supersedes anything older. An unusable configuration holds the
message the same way and exits non-zero, so the journal shows it. Every run
prints its decision, which is what `journalctl -u linker-site-alert.service`
reads.

## First installation

Create `/etc/linker-site-alert.env` only if it is missing. Install the private
`LINKER_SMTP_*` values from the provisioned #297 credentials using the operator's
secret channel. The file belongs to root with mode 600.

```sh
if [ ! -e /etc/linker-site-alert.env ]; then
    (umask 077; set -C; : > /etc/linker-site-alert.env)
fi
```

Run the initial probe once and verify a healthy reading before enabling the
notifier. The first healthy installation sends its normal daily heartbeat.

## Updating an existing VPS

Stage the six reviewed files (both scripts and both service/timer pairs)
and `site-alert-install.sh` from the merged revision in a separate temporary
directory on the VPS. Keep the existing SMTP environment and notifier state.
Run the following from the operator machine, substituting the actual stage
path. The backup contains private SMTP configuration and belongs in restricted
recovery storage.

```sh
umask 077
stage=/absolute/path/to/reviewed/stage
ssh linker-services "bash '$stage/site-alert-install.sh' backup" > monitor-backup.tar
ssh linker-services "bash '$stage/site-alert-install.sh' apply"
ssh linker-services "bash '$stage/site-alert-install.sh' verify"
```

On rollback, use the **same staged installer**. It restores files and each
timer's recorded enabled and active settings. When the prior alert timer was
active, the restored probe records a fresh observation in its native format
before the restored notifier resumes. Archives from older installers have no
timer metadata; in that case rollback preserves the settings seen at entry.

```sh
ssh linker-services "bash '$stage/site-alert-install.sh' rollback" < monitor-backup.tar
```

## Verify

Dry run against the real record:

```sh
/usr/bin/python3 /opt/linker-engine/ops/site-alert.py --dry-run
systemctl list-timers linker-site-alert.timer
journalctl -u linker-site-alert.service -n 20
```

To read the latest real cycle and the notifier's verdict without sending mail:

```sh
tail -1 /opt/linker-engine/state/site-probe.log
/usr/bin/python3 /opt/linker-engine/ops/site-alert.py --dry-run
systemctl list-timers linker-site-probe.timer linker-site-alert.timer
```

## Recovery path

For a WordPress outage check the shared host’s MySQL and hPanel. For a named backend inspect its systemd service and the local health response. The recovery message arrives from the
next successful probe cycle and states the downtime the probe measured, not the
time the site was reported.
