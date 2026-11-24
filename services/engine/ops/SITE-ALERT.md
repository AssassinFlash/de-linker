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

The Planner worker updates its readiness file at the configured heartbeat
interval while idle or executing a job. Its process owns the readiness lock.
A missing worker, a heartbeat older than its lease, or an unreadable
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

## Install

The private SMTP block already exists on the shared host at
`~/.config/terravolt-builder/sunriver-smtp.env` (mode 600, PHP transport of
#297). Copy the four `LINKER_SMTP_*` lines to `/etc/linker-site-alert.env` on
the engine host, mode 600, and add `LINKER_ALERT_TO` only if it differs from the
ruling:

```sh
ssh linker-services
umask 077 && install -m 600 /dev/null /etc/linker-site-alert.env
# paste LINKER_SMTP_HOST/PORT/USER/PASS; never echo the file back
/opt/linker-engine/ops/site-alert-install.sh verify   # identity + decision, no send
/opt/linker-engine/ops/site-alert-install.sh apply
```

`verify` runs `--check-config` (prints the host, port, TLS mode, user and
recipient, never the password) and `--dry-run` (prints the decision for the
current record without sending or writing state). `install.sh backup` before
apply streams the managed paths to the operator machine; `rollback` stops the
timer and restores that archive.

The first run after install sends one message and it is not silent: either the
daily heartbeat (the record is healthy) or a "stopped reporting" alert (the
probe has never written here). The heartbeat is deliberate — it proves the
channel works before anyone depends on it, and a notifier that only spoke during
outages could never tell anyone it had stopped working. The silence alert is
equally deliberate: an empty record means nothing is watching, which on a fresh
host is true until the probe's first cycle lands.

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
