"""The site alert pushes once per outage and never repeats itself.

Every case drives the real notifier over a temporary probe log and state file;
delivery is either observed through the recording double or through the
repository's loopback SMTP sink, so the sending path is exercised rather than
mocked. Thresholds are asserted at their exact value and one step below, the
same rule the digest's health block follows.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import smtplib
import subprocess
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

OPS = Path(__file__).resolve().parents[1] / "ops"
SINK = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "linker-commerce"
    / "tests"
    / "fixtures"
    / "smtp_sink.py"
)
SITE_ALERT = OPS / "site-alert.py"

NOW = dt.datetime(2026, 11, 11, 12, 0, tzinfo=dt.UTC)
CYCLE = 300


def load() -> ModuleType:
    """Import the deployed script as a module, the way `python3 site-alert.py`
    runs it: registered in sys.modules so dataclass annotations resolve."""
    spec = importlib.util.spec_from_file_location("site_alert", SITE_ALERT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def alert() -> ModuleType:
    return load()


def line(moment: dt.datetime, code: str) -> str:
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%SZ')} {code}\n"


def record(codes: Sequence[str], end: dt.datetime = NOW) -> str:
    """A probe record whose last line lands at `end`."""
    start = end - dt.timedelta(seconds=CYCLE * (len(codes) - 1))
    return "".join(
        line(start + dt.timedelta(seconds=CYCLE * index), code)
        for index, code in enumerate(codes)
    )


def config_file(tmp_path: Path, **overrides: str) -> Path:
    values = {
        "LINKER_SMTP_HOST": "smtp.example.test",
        "LINKER_SMTP_PORT": "465",
        "LINKER_SMTP_USER": "sales@sunriverinverter.com",
        "LINKER_SMTP_PASS": "fake-password",
    }
    values.update(overrides)
    path = tmp_path / "site-alert.env"
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in values.items() if value),
        encoding="utf-8",
    )
    return path


class Recorder:
    """Records deliveries and can refuse them the way SMTP does."""

    def __init__(self, failures: int = 0) -> None:
        self.sent: list[tuple[str, str]] = []
        self.failures = failures
        self.attempts = 0

    def __call__(self, config: object, subject: str, body: str) -> None:
        self.attempts += 1
        if self.failures:
            self.failures -= 1
            raise OSError("connection refused")
        self.sent.append((subject, body))

    @property
    def kinds(self) -> list[str]:
        return [subject.split("] ")[1].split(":")[0] for subject, _ in self.sent]


def run_alert(
    alert: ModuleType,
    tmp_path: Path,
    log: str,
    now: dt.datetime = NOW,
    deliver: Recorder | None = None,
    config: Path | None = None,
) -> tuple[int, Recorder, list[str]]:
    log_path = tmp_path / "site-probe.log"
    log_path.write_text(log, encoding="utf-8")
    state_path = tmp_path / "site-alert.json"
    recorder = deliver or Recorder()
    emitted: list[str] = []
    status = alert.run(
        log_path=log_path,
        state_path=state_path,
        config_path=config or config_file(tmp_path),
        now=now,
        deliver=recorder,
        emit=emitted.append,
    )
    return status, recorder, emitted


def state_of(tmp_path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (tmp_path / "site-alert.json").read_text(encoding="utf-8")
    )
    return loaded


def test_parse_reading_ignores_malformed_lines(alert: ModuleType) -> None:
    assert alert.parse_reading("2026-11-11T01:10:03Z 000") is not None
    assert alert.parse_reading("2026-11-11T01:10:03Z 000").code == "000"
    assert alert.parse_reading("2026-11-11T01:10:03Z 000000").code == "000000"
    assert alert.parse_reading("2026-11-11 01:10:03 000") is None
    assert alert.parse_reading("2026-11-11T01:10:03Z") is None
    assert alert.parse_reading("") is None


def test_only_200_is_healthy(alert: ModuleType) -> None:
    assert alert.Reading(NOW, "200").healthy
    for code in ("000", "500", "503", "301", "000000"):
        assert not alert.Reading(NOW, code).healthy


def test_two_failures_do_not_alert(alert: ModuleType, tmp_path: Path) -> None:
    """One step below the threshold stays quiet: the 2026-11-11 record itself
    holds only two failing cycles before recovery."""
    status, recorder, _ = run_alert(alert, tmp_path, record(["200", "000", "000"]))

    assert recorder.sent == []
    assert status == 0
    assert state_of(tmp_path)["state"] == "unknown"


def test_three_failures_alert_once(alert: ModuleType, tmp_path: Path) -> None:
    status, recorder, _ = run_alert(
        alert, tmp_path, record(["200", "200", "000", "000", "000"])
    )

    assert len(recorder.sent) == 1
    subject, body = recorder.sent[0]
    assert "SITE DOWN" in subject
    assert "3 consecutive" in subject
    # The first failure and the measured span, not a rounded guess.
    assert "2026-11-11T11:50:00Z" in body
    assert "10 min" in body
    assert "000, 000, 000" in body
    assert status == 0
    assert state_of(tmp_path)["state"] == "down"
    assert state_of(tmp_path)["failures"] == 3


def test_persistent_outage_does_not_repeat(alert: ModuleType, tmp_path: Path) -> None:
    """Nine failing cycles — the recorded incident's shape — still send once."""
    run_alert(alert, tmp_path, record(["200", "000", "000", "000"]))
    later = NOW + dt.timedelta(seconds=CYCLE * 6)
    status, recorder, _ = run_alert(
        alert, tmp_path, record(["000"] * 9, end=later), now=later
    )

    assert recorder.sent == []
    assert status == 0
    assert state_of(tmp_path)["state"] == "down"
    assert state_of(tmp_path)["failures"] == 9


def test_recovery_is_sent_once(alert: ModuleType, tmp_path: Path) -> None:
    run_alert(alert, tmp_path, record(["200", "000", "000", "000"]))
    recovered = NOW + dt.timedelta(seconds=CYCLE * 4)
    _, recorder, _ = run_alert(
        alert, tmp_path, record(["000", "200"], end=recovered), now=recovered
    )

    assert len(recorder.sent) == 1
    subject, body = recorder.sent[0]
    assert "recovered" in subject
    assert "First failure: 2026-11-11T11:50:00Z" in body
    assert "Failed cycles before recovery: 3" in body

    # A second healthy cycle sends nothing: the flip already happened.
    steady = recovered + dt.timedelta(seconds=CYCLE)
    _, quiet, _ = run_alert(
        alert, tmp_path, record(["200", "200"], end=steady), now=steady
    )
    assert quiet.sent == []


def test_silent_probe_alerts_and_resumes(alert: ModuleType, tmp_path: Path) -> None:
    """A dead probe writes nothing; a stale last line is the only evidence."""
    stale = NOW - dt.timedelta(seconds=alert.SILENCE_AFTER_S + CYCLE)
    _, recorder, _ = run_alert(alert, tmp_path, record(["200"], end=stale))

    assert len(recorder.sent) == 1
    assert "stopped reporting" in recorder.sent[0][0]
    assert "25 min" in recorder.sent[0][1]
    assert state_of(tmp_path)["state"] == "silent"

    _, again, _ = run_alert(
        alert, tmp_path, record(["200"], end=stale), now=NOW + dt.timedelta(hours=1)
    )
    assert again.sent == []

    fresh = NOW + dt.timedelta(seconds=CYCLE)
    _, resumed, _ = run_alert(
        alert, tmp_path, record(["200", "200"], end=fresh), now=fresh
    )
    assert len(resumed.sent) == 1
    assert "reporting again" in resumed.sent[0][0]


def test_empty_record_is_silence(alert: ModuleType, tmp_path: Path) -> None:
    _, recorder, _ = run_alert(alert, tmp_path, "")

    assert len(recorder.sent) == 1
    assert "no readable line" in recorder.sent[0][1]


def test_heartbeat_is_daily_and_proves_the_channel(
    alert: ModuleType, tmp_path: Path
) -> None:
    """Install sends one heartbeat, then one a day: a missing line is the only
    signal that the monitor itself died."""
    _, first, _ = run_alert(alert, tmp_path, record(["200"]))
    assert len(first.sent) == 1
    assert "monitor alive" in first.sent[0][0]
    assert "1 (1 answered 200, 0 failed)" in first.sent[0][1]

    # 23 h 55 min later — the next cycle — is still inside the day.
    soon = NOW + dt.timedelta(seconds=CYCLE)
    _, quiet, _ = run_alert(alert, tmp_path, record(["200"], end=soon), now=soon)
    assert quiet.sent == []

    beat = NOW + dt.timedelta(seconds=alert.HEARTBEAT_S)
    _, second, _ = run_alert(alert, tmp_path, record(["200"], end=beat), now=beat)
    assert len(second.sent) == 1
    assert "monitor alive" in second.sent[0][0]


def test_failed_delivery_is_retried_without_duplicating(
    alert: ModuleType, tmp_path: Path
) -> None:
    failing = Recorder(failures=1)
    status, recorder, _ = run_alert(
        alert, tmp_path, record(["200", "000", "000", "000"]), deliver=failing
    )

    assert status == 1
    assert recorder.sent == []
    assert len(state_of(tmp_path)["pending"]) == 1

    later = NOW + dt.timedelta(seconds=CYCLE)
    _, retry, _ = run_alert(
        alert, tmp_path, record(["000", "000", "000"], end=later), now=later
    )
    assert len(retry.sent) == 1
    assert "SITE DOWN" in retry.sent[0][0]
    assert state_of(tmp_path)["pending"] == []

    _, third, _ = run_alert(
        alert,
        tmp_path,
        record(["000", "000", "000"], end=later + dt.timedelta(seconds=CYCLE)),
        now=later + dt.timedelta(seconds=CYCLE),
    )
    assert third.sent == []


def test_missing_configuration_holds_the_alert_loudly(
    alert: ModuleType, tmp_path: Path
) -> None:
    empty = tmp_path / "missing.env"
    status, recorder, emitted = run_alert(
        alert, tmp_path, record(["200", "000", "000", "000"]), config=empty
    )

    assert status == 1
    assert recorder.sent == []
    assert any("no usable SMTP configuration" in message for message in emitted)
    assert len(state_of(tmp_path)["pending"]) == 1


def test_config_requires_password_and_reads_overrides(
    alert: ModuleType, tmp_path: Path
) -> None:
    assert alert.read_config(config_file(tmp_path, LINKER_SMTP_PASS="")) is None
    assert (
        alert.read_config(config_file(tmp_path, LINKER_SMTP_PORT="not-a-port")) is None
    )
    assert (
        alert.read_config(config_file(tmp_path, LINKER_SMTP_HOST="evil host/x")) is None
    )

    quoted = tmp_path / "quoted.env"
    quoted.write_text(
        "LINKER_SMTP_HOST=smtp.example.test\n"
        "LINKER_SMTP_PORT='587'\n"
        'LINKER_SMTP_USER="sales@sunriverinverter.com"\n'
        "LINKER_SMTP_PASS=has=equals\n"
        "LINKER_ALERT_TO=ops@example.test\n",
        encoding="utf-8",
    )
    config = alert.read_config(quoted)
    assert config is not None
    assert (config.port, config.secure) == (587, "tls")
    assert config.password == "has=equals"
    assert config.recipient == "ops@example.test"


def test_recipient_defaults_to_the_internal_address(
    alert: ModuleType, tmp_path: Path
) -> None:
    """2026-10-17 owner ruling: internal notifications go to this address."""
    config = alert.read_config(config_file(tmp_path))

    assert config is not None
    assert config.recipient == "sales@sunriverinverter.com"


def test_corrupt_state_is_tolerated(alert: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "site-alert.json").write_text("{not json", encoding="utf-8")
    status, recorder, _ = run_alert(alert, tmp_path, record(["200"]))

    assert status == 0
    assert len(recorder.sent) == 1
    assert "monitor alive" in recorder.sent[0][0]
    assert state_of(tmp_path)["state"] == "ok"


@pytest.fixture
def sink() -> Iterator[tuple[int, Path]]:
    """The repository's loopback SMTP sink, the same one PHP's tests use."""
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        capture = Path(directory) / "smtp.jsonl"
        process = subprocess.Popen(
            [sys.executable, str(SINK), str(capture), "fake-password"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        assert process.stdout is not None
        port = int(process.stdout.readline().strip())
        process.stdout.close()
        try:
            yield port, capture
        finally:
            process.terminate()
            process.wait(timeout=10)


def test_deliver_smtp_reaches_a_real_sink(
    alert: ModuleType, tmp_path: Path, sink: tuple[int, Path]
) -> None:
    port, capture = sink
    config = alert.Config(
        host="127.0.0.1",
        port=port,
        user="sales@sunriverinverter.com",
        password="fake-password",
        secure="",
        recipient="sales@sunriverinverter.com",
    )

    alert.deliver_smtp(config, "[de-linker] SITE DOWN: test", "body text\n")

    records = [json.loads(line) for line in capture.read_text().splitlines()]
    assert len(records) == 1
    assert [item.lower() for item in records[0]["recipients"]] == [
        "rcpt to:<sales@sunriverinverter.com>"
    ]
    assert "Subject: [de-linker] SITE DOWN: test" in records[0]["message"]
    assert "body text" in records[0]["message"]


def test_deliver_smtp_refuses_a_bad_password(
    alert: ModuleType, sink: tuple[int, Path]
) -> None:
    port, capture = sink
    config = alert.Config(
        host="127.0.0.1",
        port=port,
        user="sales@sunriverinverter.com",
        password="wrong-password",
        secure="",
        recipient="sales@sunriverinverter.com",
    )

    with pytest.raises(smtplib.SMTPAuthenticationError):
        alert.deliver_smtp(config, "subject", "body")
    assert not capture.exists()


def test_end_to_end_outage_and_recovery_over_smtp(
    alert: ModuleType, tmp_path: Path, sink: tuple[int, Path]
) -> None:
    """The full path: probe record in, two mails out, nothing in between."""
    port, capture = sink
    config = tmp_path / "site-alert.env"
    config.write_text(
        "LINKER_SMTP_HOST=127.0.0.1\n"
        f"LINKER_SMTP_PORT={port}\n"
        "LINKER_SMTP_USER=sales@sunriverinverter.com\n"
        "LINKER_SMTP_PASS=fake-password\n"
        "LINKER_SMTP_SECURE=\n",
        encoding="utf-8",
    )
    log_path = tmp_path / "site-probe.log"
    state_path = tmp_path / "site-alert.json"

    def cycle(codes: Sequence[str], end: dt.datetime) -> int:
        log_path.write_text(record(codes, end=end), encoding="utf-8")
        status: int = alert.run(
            log_path=log_path,
            state_path=state_path,
            config_path=config,
            now=end,
            emit=lambda _message: None,
        )
        return status

    # The install run sends one heartbeat, which is the proof that this channel
    # works before anyone depends on it.
    assert cycle(["200"], NOW) == 0
    assert cycle(["000", "000"], NOW + dt.timedelta(seconds=CYCLE * 2)) == 0
    assert len(capture.read_text().splitlines()) == 1

    down_at = NOW + dt.timedelta(seconds=CYCLE * 3)
    assert cycle(["000", "000", "000"], down_at) == 0
    up_at = NOW + dt.timedelta(seconds=CYCLE * 4)
    assert cycle(["000", "200"], up_at) == 0

    subjects = [
        next(
            line.removeprefix("Subject: ")
            for line in json.loads(entry)["message"].splitlines()
            if line.startswith("Subject: ")
        )
        for entry in capture.read_text().splitlines()
    ]
    assert len(subjects) == 3
    assert "monitor alive" in subjects[0]
    assert "SITE DOWN" in subjects[1]
    assert "recovered" in subjects[2]


def test_delivery_never_prints_the_credential(
    alert: ModuleType, sink: tuple[int, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A channel proof taken with smtplib's debug log on 2026-11-11 put this
    mailbox's password into a transcript (the AUTH argument is the password in
    base64). Delivering must stay silent on both streams."""
    port, _ = sink
    config = alert.Config(
        host="127.0.0.1",
        port=port,
        user="sales@sunriverinverter.com",
        password="fake-password",
        secure="",
        recipient="sales@sunriverinverter.com",
    )

    alert.deliver_smtp(config, "subject", "body")
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""
    for marker in ("AUTH", "ZkFrzS1wYXNzd29yZA==", "fake-password"):
        assert marker not in captured.out + captured.err
