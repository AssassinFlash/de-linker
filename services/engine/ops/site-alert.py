#!/usr/bin/env python3
"""Push the site probe's verdict to the team while the site stays down.

The probe (ops/site-probe.sh) writes one line per five-minute cycle and sends
nothing; the 2026-11-11 host MySQL outage proved that a record nobody reads is
not detection. The site was globally unreachable from ~00:35 to ~01:20 UTC, the
first automated trace was a feed-sync failure at 00:43:36, and the only
consumer of that trace was a human reading journal lines. This notifier is the
push side: it reads the probe record on the engine host and mails the team once
per incident, then once again when the site answers.

Channel independence. Mail leaves this VPS over authenticated SMTP
(smtp.hostinger.com:465 answers from here; the host has no MTA installed at
all, measured 2026-11-11). It never goes through the site's PHP mail(): the
shared host that serves the site is the thing being watched, and its 10/minute
and 100/24 h budget belongs to customer mail.

Threshold evidence (docs/acceptance/2026-11-10/goal-state-ledger.md, sections
"Outage timeline" and "Outage resolved by provider reboot"):
- the outage ran ~00:35–01:20 UTC, that is ~9 five-minute cycles;
- the probe's own record of it holds only 2 failing cycles because the probe
  was installed at 01:09 UTC, near the end (01:10:03 and 01:15:27, both 000);
- the 89 cycles recorded between 01:10 and 08:37 UTC have gaps of median
  310 s, p95 332 s, max 340 s.
FAILURES_BEFORE_ALERT = 3 therefore requires two whole gaps between the first
and the third failure — at least 10 minutes of wall clock at the measured
cadence — so no single late timer or one-off transient can trip it, and it
still fires inside one third of the smallest real incident on record.

Probe silence is its own alert. A probe that stops writing (timer disabled,
unit broken, log moved) looks exactly like a healthy quiet log to any reader
that only inspects failures, which is how the original gap stayed invisible.
The last reading's age is checked on every run against SILENCE_AFTER_S.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import smtplib
import socket
import ssl
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path

LOG_PATH = Path("/opt/linker-engine/state/site-probe.log")
STATE_PATH = Path("/opt/linker-engine/state/site-alert.json")
CONFIG_PATH = Path("/etc/linker-site-alert.env")

# Threshold evidence: see the module docstring (9 failing cycles, 340 s worst
# observed gap). Three failures are >= 10 minutes apart at that cadence.
FAILURES_BEFORE_ALERT = 3

# 20 minutes is 3.5 of the worst gap observed on the probe log (340 s), so a
# late timer cannot fake silence while three missed cycles cannot be lateness.
SILENCE_AFTER_S = 20 * 60

# One line a day while the site is healthy: if it stops arriving the monitor is
# dead, not the site. That is the only watcher for this notifier itself, since
# no second vantage exists and the WP-side digest dies with the site.
HEARTBEAT_S = 24 * 60 * 60

# The probe caps its log at 2016 lines (one week at five minutes); the same
# bound keeps this reader from loading an unbounded file after a bad deploy.
TAIL_LINES = 2016
TAIL_BYTES = 256 * 1024

SMTP_TIMEOUT_S = 20

# 2026-10-17 owner ruling: internal notifications go to this address only.
DEFAULT_RECIPIENT = "sales@sunriverinverter.com"

WITNESS_LINES = 8


@dataclass(frozen=True)
class Config:
    """SMTP identity and recipient read from the private environment file."""

    host: str
    port: int
    user: str
    password: str
    secure: str
    recipient: str


@dataclass(frozen=True)
class Reading:
    """One probe cycle as recorded by site-probe.sh."""

    when: dt.datetime
    code: str

    @property
    def healthy(self) -> bool:
        # The probe asks one fixed JSON endpoint; it answers 200 or the site is
        # not serving customers. Anything else (000, 500, 503, a redirect that
        # -o /dev/null reports as 301) is a failure worth paging for.
        return self.code == "200"


@dataclass
class State:
    """What the last run concluded, so a flip is mailed once and only once."""

    state: str = "unknown"
    since: str = ""
    failures: int = 0
    last_heartbeat: str = ""
    pending: list[dict[str, str]] = field(default_factory=list)


Deliver = Callable[[Config, str, str], None]


def iso(moment: dt.datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.UTC)
    except ValueError:
        return None


def duration(seconds: float) -> str:
    total = int(max(0, seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} h {minutes} min"
    if minutes:
        return f"{minutes} min {secs} s"
    return f"{secs} s"


def parse_reading(line: str) -> Reading | None:
    """One `TIMESTAMP CODE` line; anything else is ignored, not guessed at."""
    parts = line.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    try:
        when = dt.datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.UTC
        )
    except ValueError:
        return None
    return Reading(when, parts[1])


def read_tail(path: Path) -> list[Reading]:
    """Recent readings, oldest first, capped like the probe's own log."""
    try:
        with path.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            offset = max(0, size - TAIL_BYTES)
            handle.seek(offset)
            chunk = handle.read()
    except OSError:
        return []
    lines = chunk.decode("utf-8", "replace").splitlines()
    if offset > 0 and lines:
        lines = lines[1:]  # the first line may be a partial record.
    readings = [reading for reading in map(parse_reading, lines) if reading]
    return readings[-TAIL_LINES:]


def read_config(path: Path) -> Config | None:
    """Literal KEY=VALUE lines, the same shape as sunriver-smtp.env (#297).

    Unusable configuration returns None instead of a half-configured sender:
    the caller then holds the alert loudly rather than dropping it.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    env: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        env[key.strip()] = value
    for key in ("LINKER_SMTP_HOST", "LINKER_SMTP_PORT", "LINKER_SMTP_USER"):
        if not env.get(key, "").strip():
            return None
    # A password with a "=" inside is legal; only an empty one is unusable.
    if "LINKER_SMTP_PASS" not in env or env["LINKER_SMTP_PASS"] == "":
        return None
    try:
        port = int(env["LINKER_SMTP_PORT"])
    except ValueError:
        return None
    if not 1 <= port <= 65535:
        return None
    host = env["LINKER_SMTP_HOST"]
    if not host.replace(".", "").replace("-", "").isalnum():
        return None
    secure = env.get("LINKER_SMTP_SECURE", "ssl" if port == 465 else "tls")
    if secure not in ("", "ssl", "tls"):
        return None
    recipient = env.get("LINKER_ALERT_TO", "").strip() or DEFAULT_RECIPIENT
    return Config(
        host, port, env["LINKER_SMTP_USER"], env["LINKER_SMTP_PASS"], secure, recipient
    )


def load_state(path: Path) -> State:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return State()
    if not isinstance(raw, dict):
        return State()
    state = State()
    state.state = str(raw.get("state", "unknown"))
    state.since = str(raw.get("since", ""))
    failures = raw.get("failures", 0)
    state.failures = failures if isinstance(failures, int) else 0
    state.last_heartbeat = str(raw.get("last_heartbeat", ""))
    pending = raw.get("pending", [])
    if isinstance(pending, list):
        state.pending = [
            {str(key): str(value) for key, value in item.items()}
            for item in pending
            if isinstance(item, dict)
        ]
    return state


def save_state(path: Path, state: State) -> None:
    """Atomic replace: a crash mid-write must not forge a "delivered" state."""
    payload = json.dumps(
        {
            "state": state.state,
            "since": state.since,
            "failures": state.failures,
            "last_heartbeat": state.last_heartbeat,
            "pending": state.pending,
        },
        indent=1,
        sort_keys=True,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload + "\n", encoding="utf-8")
    os.replace(temporary, path)


def witness(readings: Sequence[Reading], count: int = WITNESS_LINES) -> str:
    tail = readings[-count:]
    return "\n".join(f"  {iso(reading.when)} {reading.code}" for reading in tail)


def describe(readings: Sequence[Reading], count: int) -> str:
    return ", ".join(reading.code for reading in readings[-count:]) or "none"


def trailer(now: dt.datetime) -> str:
    return (
        f"\n-- \nSent {iso(now)} by {socket.gethostname()} "
        "(engine VPS, the host that stays up when the website's shared host "
        "is down). Record: /opt/linker-engine/state/site-probe.log; "
        "unit: linker-site-alert.service.\n"
    )


def down_message(
    readings: Sequence[Reading], failures: int, now: dt.datetime
) -> tuple[str, str]:
    first = readings[-failures].when if failures <= len(readings) else now
    return (
        f"[de-linker] SITE DOWN: {failures} consecutive failed probes",
        "The public site has not answered the probe for "
        f"{failures} consecutive cycles ({duration((now - first).total_seconds())} "
        "and counting).\n\n"
        "Probe: https://de-linker.com/wp-json/ (database-backed; it failed "
        "with the host's MySQL on 2026-11-11).\n"
        f"First failure: {iso(first)}\n"
        f"Latest failure: {iso(readings[-1].when)}\n"
        f"Codes: {describe(readings, failures)}\n\n"
        "Recent readings:\n"
        f"{witness(readings)}\n\n"
        "No mail from this host is sent through the website, so this alert "
        "does not depend on the site being up. One message is sent per "
        "outage; the recovery message follows when the probe answers again. "
        "Check the shared host's MySQL and hPanel first.\n"
        f"{trailer(now)}",
    )


def recovered_message(
    state: State, readings: Sequence[Reading], now: dt.datetime
) -> tuple[str, str]:
    started = parse_iso(state.since)
    elapsed = (now - started).total_seconds() if started else 0.0
    return (
        f"[de-linker] Site recovered after {duration(elapsed)}",
        "The public site answers the probe again.\n\n"
        f"First failure: {state.since or 'unknown'}\n"
        f"Recovery seen: {iso(readings[-1].when)} (code {readings[-1].code})\n"
        f"Failed cycles before recovery: {state.failures}\n"
        f"Downtime as measured by the probe: {duration(elapsed)}\n\n"
        "Recent readings:\n"
        f"{witness(readings)}\n\n"
        "Confirm the site end-to-end (EN and DE pages, a database-backed "
        "endpoint) before treating the incident as closed.\n"
        f"{trailer(now)}",
    )


def silent_message(
    last: Reading | None, now: dt.datetime, log_path: Path, since: str
) -> tuple[str, str]:
    if last is None:
        detail = "The probe record holds no readable line at all."
        age = "unknown"
    else:
        detail = f"The last reading is {iso(last.when)} ({last.code})."
        age = duration((now - last.when).total_seconds())
    # A monitor that dies while the site is already down must not erase when
    # that outage started: this timestamp is the only record of it left.
    known = (
        f"\nThe site was already failing before the silence began; the first "
        f"failure seen was {since}.\n"
        if since
        else ""
    )
    return (
        "[de-linker] Site probe stopped reporting",
        "The site monitor has stopped writing, so nothing is watching the "
        "website right now.\n\n"
        f"{detail}\n"
        f"Age of that reading: {age}\n"
        f"Silence threshold: {duration(SILENCE_AFTER_S)} "
        f"({FAILURES_BEFORE_ALERT + 1} cycles at the measured 5-minute cadence).\n"
        f"Record: {log_path}\n"
        f"{known}\n"
        "This is the failure mode that hid the 2026-11-11 outage: a probe that "
        "dies looks exactly like a quiet healthy log. Check on the engine "
        "host: systemctl status linker-site-probe.timer, "
        "systemctl list-timers linker-site-probe.timer, then "
        "journalctl -u linker-site-probe.service.\n"
        f"{trailer(now)}",
    )


def resumed_message(
    readings: Sequence[Reading], now: dt.datetime, since: str
) -> tuple[str, str]:
    last_failure = (
        f"\nThe silence interrupted an outage that started at {since}; whether "
        f"the site recovered during the silence is unknown.\n"
        if since
        else ""
    )
    return (
        "[de-linker] Site probe reporting again",
        "The probe record is current, so the website is being watched again. "
        "An outage during the silence may have gone unreported.\n\n"
        f"Latest reading: {iso(readings[-1].when)} (code {readings[-1].code})\n"
        f"{last_failure}\n"
        "Recent readings:\n"
        f"{witness(readings)}\n"
        f"{trailer(now)}",
    )


def heartbeat_message(readings: Sequence[Reading], now: dt.datetime) -> tuple[str, str]:
    window = now - dt.timedelta(seconds=HEARTBEAT_S)
    recent = [reading for reading in readings if reading.when >= window]
    healthy = sum(1 for reading in recent if reading.healthy)
    failed = len(recent) - healthy
    latest = readings[-1] if readings else None
    lines = [
        "The engine host's site monitor is alive.",
        "",
        f"Probes recorded in the last 24 h: {len(recent)} "
        f"({healthy} answered 200, {failed} failed).",
        f"Latest reading: {iso(latest.when) if latest else 'none'} "
        f"({latest.code if latest else 'none'})",
        "",
        "This line is sent once a day while the site is healthy. If it stops "
        "arriving, the monitor itself is dead rather than the site, because "
        "nothing else watches this host.",
    ]
    return (
        f"[de-linker] Site monitor alive: {healthy}/{len(recent)} probes answered 200",
        "\n".join(lines) + "\n" + trailer(now),
    )


def advance(
    state: State, readings: Sequence[Reading], now: dt.datetime, log_path: Path
) -> list[tuple[str, str, str]]:
    """Fold one probe record into the state; return the messages to send."""
    events: list[tuple[str, str, str]] = []
    last = readings[-1] if readings else None
    silent = last is None or (now - last.when).total_seconds() > SILENCE_AFTER_S
    trailing = 0
    for reading in reversed(readings):
        if reading.healthy:
            break
        trailing += 1

    if silent:
        observed = "silent"
    elif trailing >= FAILURES_BEFORE_ALERT:
        observed = "down"
    elif last is not None and last.healthy:
        observed = "ok"
    else:
        # One or two failures: a debounce in progress, not a state change.
        observed = state.state

    previous = state.state
    if observed == "down":
        state.failures = trailing
    if observed != previous:
        if observed == "down":
            subject, body = down_message(readings, trailing, now)
            first = readings[-trailing].when if trailing <= len(readings) else now
            state.since = iso(first)
            events.append(("down", subject, body))
        elif observed == "silent":
            # `since` carries a running outage across the silence; when the
            # monitor dies on a healthy site it starts now.
            carried = state.since if previous == "down" else ""
            subject, body = silent_message(last, now, log_path, carried)
            state.since = carried or iso(now)
            state.failures = trailing
            events.append(("probe_silent", subject, body))
        elif observed == "ok":
            carried = state.since if previous == "silent" else ""
            if previous == "down":
                subject, body = recovered_message(state, readings, now)
                events.append(("recovered", subject, body))
            elif previous == "silent":
                subject, body = resumed_message(readings, now, carried)
                events.append(("probe_resumed", subject, body))
            state.since = iso(last.when if last else now)
            state.failures = 0
        state.state = observed

    # Any mail proves the channel is alive, so a state change also resets the
    # heartbeat clock: one message per run, never an alert plus a heartbeat.
    if events:
        state.last_heartbeat = iso(now)
    elif observed == "ok":
        previous_beat = parse_iso(state.last_heartbeat)
        if previous_beat is None or (now - previous_beat).total_seconds() >= (
            HEARTBEAT_S
        ):
            subject, body = heartbeat_message(readings, now)
            state.last_heartbeat = iso(now)
            events.append(("heartbeat", subject, body))
    return events


def deliver_smtp(config: Config, subject: str, body: str) -> None:
    """Authenticated submission from this host; the site's PHP mail is unused."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.user
    message["To"] = config.recipient
    message["Date"] = format_datetime(dt.datetime.now(dt.UTC))
    domain = config.user.rpartition("@")[2] or None
    message["Message-ID"] = make_msgid(domain=domain)
    message.set_content(body)

    context = ssl.create_default_context()
    # Protocol diagnostics stay off. smtplib's debuglevel prints the AUTH
    # argument, which is the password in base64 — a channel proof taken with
    # debuglevel=1 on 2026-11-11 put this mailbox's password in a transcript.
    # Errors are still raised and named by type; only the wire log is gone.
    client: smtplib.SMTP
    if config.secure == "ssl":
        client = smtplib.SMTP_SSL(
            config.host, config.port, timeout=SMTP_TIMEOUT_S, context=context
        )
    else:
        client = smtplib.SMTP(config.host, config.port, timeout=SMTP_TIMEOUT_S)
    client.set_debuglevel(0)
    try:
        if config.secure == "tls":
            client.starttls(context=context)
        # The bare AUTH LOGIN form, the same exchange this repository's SMTP
        # sink fixture and PHP transport use; the initial-response variant
        # loses the username challenge against a strict server.
        client.login(config.user, config.password, initial_response_ok=False)
        refused = client.send_message(message)
        if refused:
            # A refused recipient is not a delivery; keep the alert pending.
            raise smtplib.SMTPRecipientsRefused(refused)
    finally:
        try:
            client.quit()
        except smtplib.SMTPException:
            client.close()


def run(
    *,
    log_path: Path = LOG_PATH,
    state_path: Path = STATE_PATH,
    config_path: Path = CONFIG_PATH,
    now: dt.datetime | None = None,
    deliver: Deliver | None = None,
    emit: Callable[[str], None] = print,
    dry_run: bool = False,
) -> int:
    moment = now or dt.datetime.now(dt.UTC)
    state = load_state(state_path)
    readings = read_tail(log_path)
    events = advance(state, readings, moment, log_path)
    state.pending.extend(
        {"kind": kind, "subject": subject, "body": body}
        for kind, subject, body in events
    )
    for kind, subject, _ in events:
        emit(f"site-alert: queued {kind}: {subject}")
    if dry_run:
        emit(
            f"site-alert: dry run; state {state.state}, "
            f"{len(readings)} readings, {len(state.pending)} pending"
        )
        return 0
    if not state.pending:
        save_state(state_path, state)
        emit(f"site-alert: state {state.state}; nothing to send")
        return 0

    config = read_config(config_path)
    if config is None:
        save_state(state_path, state)
        emit(
            f"site-alert: no usable SMTP configuration at {config_path}; "
            f"{len(state.pending)} alert(s) held for the next run"
        )
        return 1

    sender = deliver or deliver_smtp
    delivered = 0
    while state.pending:
        message = state.pending[0]
        try:
            sender(config, message["subject"], message["body"])
        except (OSError, ValueError, smtplib.SMTPException) as error:
            emit(
                f"site-alert: delivery of {message['kind']} failed: "
                f"{type(error).__name__}: {error}; retrying next cycle"
            )
            break
        state.pending.pop(0)
        delivered += 1
        emit(f"site-alert: sent {message['kind']}: {message['subject']}")
    save_state(state_path, state)
    emit(
        f"site-alert: state {state.state}; sent {delivered}, "
        f"{len(state.pending)} still pending"
    )
    return 0 if not state.pending else 1


def check_config(config_path: Path, emit: Callable[[str], None]) -> int:
    config = read_config(config_path)
    if config is None:
        emit(f"site-alert: no usable SMTP configuration at {config_path}")
        return 1
    emit(
        f"site-alert: config ok; host {config.host}:{config.port} "
        f"secure={config.secure or 'none'} user {config.user} "
        f"to {config.recipient}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=LOG_PATH)
    parser.add_argument("--state", type=Path, default=STATE_PATH)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report the decision without sending or writing state",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="print the resolved SMTP identity (never the password) and exit",
    )
    options = parser.parse_args(argv)
    if options.check_config:
        return check_config(options.config, print)
    return run(
        log_path=options.log,
        state_path=options.state,
        config_path=options.config,
        dry_run=options.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
