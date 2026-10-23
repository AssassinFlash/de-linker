"""Offline regressions for bounded, private native MFA failure diagnostics."""

import importlib.util
import json
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from http.client import HTTPException, InvalidURL
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, BinaryIO

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    spec = importlib.util.spec_from_file_location(
        "admin_mfa_diagnostics", REPO / "tools/checks/admin-mfa.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    opened: list[BinaryIO] = []
    original = module._open_log

    @contextmanager
    def tracked(path: Path) -> Iterator[BinaryIO]:
        with original(path) as source:
            opened.append(source)
            yield source

    monkeypatch.setattr(module, "_open_log", tracked)
    monkeypatch.setattr(module, "opened_log_files", opened, raising=False)
    try:
        yield module
    finally:
        for source in opened:
            source.close()


@pytest.fixture
def wp(tmp_path: Path) -> Any:
    root = tmp_path / "wordpress"
    content = root / "wp-content"
    (content / "linker-errors").mkdir(parents=True)
    (root / "wp-includes").mkdir()
    (root / "wp-includes/failure.php").write_text("<?php // Known code.\n")
    return SimpleNamespace(
        instance=SimpleNamespace(
            docroot=root, wp_content=content, url="http://127.0.0.1:9999"
        )
    )


def log(wp: Any, name: str = "php.log") -> Path:
    return wp.instance.wp_content / "linker-errors" / name  # type: ignore[no-any-return]


def fatal(path: Path | str, line: int = 42, message: str = "failure") -> str:
    return (
        "[24-Oct-2026 01:02:03 UTC] PHP Fatal error:  Uncaught RuntimeException: "
        f"{message} in {path}:{line}\n"
        "Stack trace:\n"
        "#0 secret@example.test(9): fail('token-value', 'https://private.test/key')\n"
        f"  thrown in {path} on line {line}\n"
    )


def test_only_new_exception_class_and_trusted_location_are_reported(
    runner: ModuleType, wp: Any
) -> None:
    source = wp.instance.docroot / "wp-includes/failure.php"
    log(wp).write_text(fatal(source, 3, "old-fatal"))
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    secret = (
        "token=do-not-report https://secret.test/reset?key=hidden "
        "person@example.test argv=['password', 'hidden']"
    )
    with log(wp).open("a") as stream:
        stream.write(fatal(source, 42, secret))
    rows = window.collect()
    assert rows == [
        {
            "exception": "RuntimeException",
            "file": "wordpress/wp-includes/failure.php",
            "line": 42,
        }
    ]
    report = json.dumps(rows)
    for private in (secret, "hidden", "token", "https://", "@", "argv", str(source)):
        assert private not in report


def test_rotation_uses_inode_offsets_for_both_files(
    runner: ModuleType, wp: Any
) -> None:
    source = wp.instance.docroot / "wp-includes/failure.php"
    log(wp, "php.1.log").write_text(fatal(source, 1, "older"))
    log(wp).write_text(fatal(source, 2, "old"))
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    with log(wp).open("a") as stream:
        stream.write(fatal(source, 3))
    log(wp, "php.1.log").unlink()
    log(wp).rename(log(wp, "php.1.log"))
    log(wp).write_text(fatal(source, 4))
    assert sorted(row["line"] for row in window.collect()) == [3, 4]


def test_snapshot_pins_deleted_inode_until_explicit_close(
    runner: ModuleType, wp: Any
) -> None:
    source = wp.instance.docroot / "wp-includes/failure.php"
    log(wp).write_text(fatal(source, 1))
    log(wp, "php.1.log").write_text(fatal(source, 2))
    previous = log(wp, "php.1.log").stat()
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    pinned = list(runner.opened_log_files)
    assert len(pinned) == 2
    assert all(not stream.closed for stream in pinned)
    log(wp, "php.1.log").unlink()
    held = os.fstat(pinned[1].fileno())
    assert (held.st_dev, held.st_ino) == (previous.st_dev, previous.st_ino)
    assert held.st_nlink == 0
    replacement = log(wp, "php.1.log")
    replacement.write_text(fatal(source, 3))
    allocated = replacement.stat()
    assert (allocated.st_dev, allocated.st_ino) != (held.st_dev, held.st_ino)
    assert [row["line"] for row in window.collect()] == [3]
    window.close()
    assert all(stream.closed for stream in pinned)
    window.close()  # Closing again is harmless, including from main's finally.


def test_partial_snapshot_failure_closes_every_open_log(
    runner: ModuleType, wp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = wp.instance.docroot / "wp-includes/failure.php"
    for name in ("php.log", "php.1.log"):
        log(wp, name).write_text(fatal(source))
    original = runner._read_log_bytes
    reads = 0

    def fail_second(stream: BinaryIO, count: int) -> bytes:
        nonlocal reads
        reads += 1
        if reads == 2:
            raise PermissionError("secret-token person@example.test")
        result: bytes = original(stream, count)
        return result

    monkeypatch.setattr(runner, "_read_log_bytes", fail_second)
    assert runner.FatalLogWindow.capture(wp) is None
    assert len(runner.opened_log_files) == 2
    assert all(stream.closed for stream in runner.opened_log_files)


def test_disposal_error_still_closes_all_pins_without_output(
    runner: ModuleType, wp: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in ("php.log", "php.1.log"):
        log(wp, name).write_text(fatal(wp.instance.docroot / "wp-includes/failure.php"))
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None

    def failed_close() -> None:
        raise OSError("secret-token person@example.test https://private.test")

    window._pins.callback(failed_close)
    window.close()
    assert len(runner.opened_log_files) == 2
    assert all(stream.closed for stream in runner.opened_log_files)
    assert capsys.readouterr() == ("", "")


def test_initially_missing_logs_and_deleted_logs_are_safe(
    runner: ModuleType, wp: Any
) -> None:
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    assert window.collect() == []
    log(wp).write_text(fatal(wp.instance.docroot / "wp-includes/failure.php"))
    assert len(window.collect()) == 1
    log(wp).unlink()
    assert window.collect() == []


def test_partial_old_line_and_copy_truncation_do_not_repeat_old_fatals(
    runner: ModuleType, wp: Any
) -> None:
    source = wp.instance.docroot / "wp-includes/failure.php"
    log(wp).write_text("old unterminated message ")
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    with log(wp).open("a") as stream:
        stream.write(fatal(source, 1) + fatal(source, 2))
    assert [row["line"] for row in window.collect()] == [2]
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    log(wp).write_text(fatal(source, 1))
    assert window.collect() == []


def test_unknown_paths_and_unterminated_or_forged_records_are_omitted(
    runner: ModuleType, wp: Any, tmp_path: Path
) -> None:
    outside = tmp_path / "token-person@example.test.php"
    outside.write_text("<?php\n")
    upload = wp.instance.wp_content / "uploads"
    upload.mkdir()
    (upload / "secret.php").write_text("<?php\n")
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    source = wp.instance.docroot / "wp-includes/failure.php"
    log(wp).write_text(
        fatal(outside)
        + fatal(upload / "secret.php")
        + fatal("https://private.test/key")
        + fatal("tests/e2e/fixtures/admin-mfa.php")
        + fatal(source).replace("PHP Fatal error:", "PHP Warning:")
        + fatal(source).splitlines()[0]
    )
    assert window.collect() == []


def test_repo_and_eval_wrapper_have_safe_location_names(
    runner: ModuleType, wp: Any
) -> None:
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    wrapper = (
        "phar:///private/person@example.test/wp/vendor/wp-cli/eval-command/"
        "src/EvalFile_Command.php(85) : eval()'d code"
    )
    log(wp).write_text(
        fatal(REPO / "tests/e2e/fixtures/admin-mfa.php", 245) + fatal(wrapper, 7)
    )
    assert window.collect() == [
        {
            "exception": "RuntimeException",
            "file": "repo/tests/e2e/fixtures/admin-mfa.php",
            "line": 245,
        },
        {"exception": "RuntimeException", "file": "wp-cli/eval-file", "line": 7},
    ]


def test_total_read_budget_and_fatal_row_count_are_bounded(
    runner: ModuleType, wp: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    source = wp.instance.docroot / "wp-includes/failure.php"
    for name in ("php.log", "php.1.log"):
        log(wp, name).write_text(
            "x" * 150_000 + "\n" + "".join(fatal(source, i) for i in range(1, 9))
        )
    reads: list[int] = []
    original = runner._read_log_bytes

    def read(source: Any, count: int) -> bytes:
        reads.append(count)
        data: bytes = original(source, count)
        return data

    monkeypatch.setattr(runner, "_read_log_bytes", read)
    assert [row["line"] for row in window.collect()] == [4, 5, 6, 7, 8]
    assert sum(reads) <= 128 * 1024


def test_read_errors_and_symlinks_cannot_expose_or_mask_failure(
    runner: ModuleType, wp: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    window = runner.FatalLogWindow.capture(wp)
    assert window is not None
    private = tmp_path / "private.log"
    private.write_text(fatal(wp.instance.docroot / "wp-includes/failure.php"))
    log(wp).symlink_to(private)
    assert window.collect() == []

    def denied(_: Path) -> Any:
        raise PermissionError("token=hidden person@example.test https://secret.test")

    monkeypatch.setattr(runner, "_open_log", denied)
    report = {"passed": False, "failure": "original"}
    runner.attach_fatal_diagnostics(report, window)
    assert report == {"passed": False, "failure": "original"}
    assert runner.FatalLogWindow.capture(wp) is None


@pytest.mark.parametrize(
    ("error", "failure"),
    [
        (RuntimeError("Original fixed failure"), "Original fixed failure"),
        (
            InvalidURL("https://secret.test/?key=hidden person@example.test\x12"),
            "Native MFA HTTP transport failed: InvalidURL.",
        ),
        (
            HTTPException("token=hidden argv=['password']"),
            "Native MFA HTTP transport failed: HTTPException.",
        ),
    ],
)
@pytest.mark.parametrize("diagnostic_failure", [False, True])
def test_failure_report_keeps_checks_exit_and_cleanup_without_http_secrets(
    runner: ModuleType,
    wp: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    error: Exception,
    failure: str,
    diagnostic_failure: bool,
) -> None:
    events: list[str] = []
    wp.run = lambda *_: "true"
    monkeypatch.setattr(runner, "WpCli", lambda *_: wp)
    monkeypatch.setattr(
        runner, "Registry", lambda *_: SimpleNamespace(get=lambda _: object())
    )
    monkeypatch.setattr(runner, "require_php", lambda: Path("unused"))
    monkeypatch.setattr(runner, "verify_dependency", lambda _: {})

    def run(test: Any) -> None:
        test.owns_fixture = True
        test.results.append({"case": "original-check", "passed": True})
        log(wp).write_text(
            fatal(wp.instance.docroot / "wp-includes/failure.php", 9, "secret-token")
        )
        events.append("run")
        raise error

    original = runner.FatalLogWindow.collect

    def collect(window: Any) -> Any:
        events.append("diagnostic")
        if diagnostic_failure:
            raise OSError("token=hidden")
        return original(window)

    def cleanup(_: Any, action: str) -> str:
        assert action == "cleanup"
        assert events == ["run", "diagnostic"]
        events.append("cleanup")
        return ""

    monkeypatch.setattr(runner.Acceptance, "run", run)
    monkeypatch.setattr(runner.Acceptance, "fixture", cleanup)
    monkeypatch.setattr(runner.FatalLogWindow, "collect", collect)
    evidence = tmp_path / "report.json"
    monkeypatch.setattr(
        sys, "argv", ["admin-mfa", "offline", "--evidence", str(evidence)]
    )
    assert runner.main() == 1
    report = json.loads(evidence.read_text())
    assert report["passed"] is False
    assert report["failure"] == failure
    assert report["checks"] == [{"case": "original-check", "passed": True}]
    assert ("php_fatals" in report) is not diagnostic_failure
    assert events == ["run", "diagnostic", "cleanup"]
    assert evidence.stat().st_mode & 0o777 == 0o600
    for output in (evidence.read_text(), capsys.readouterr().out):
        for private in (
            "hidden",
            "secret-token",
            "https://",
            "@",
            "argv",
            str(wp.instance.docroot),
        ):
            assert private not in output


@pytest.mark.parametrize(
    "outcome",
    ["success", "failure", "diagnostic-error", "uncaught", "cleanup-error", "keep"],
)
def test_main_releases_pins_on_every_exit_including_cleanup_failure(
    runner: ModuleType,
    wp: Any,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    for name in ("php.log", "php.1.log"):
        log(wp, name).write_text(fatal(wp.instance.docroot / "wp-includes/failure.php"))
    wp.run = lambda *_: "true"
    monkeypatch.setattr(runner, "WpCli", lambda *_: wp)
    monkeypatch.setattr(
        runner, "Registry", lambda *_: SimpleNamespace(get=lambda _: object())
    )
    monkeypatch.setattr(runner, "require_php", lambda: Path("unused"))
    monkeypatch.setattr(runner, "verify_dependency", lambda _: {})
    cleaned: list[str] = []

    def run(test: Any) -> None:
        test.owns_fixture = True
        assert len(runner.opened_log_files) == 2
        assert all(not stream.closed for stream in runner.opened_log_files)
        if outcome in {"failure", "diagnostic-error"}:
            raise RuntimeError("Original acceptance failure")
        if outcome == "uncaught":
            raise TypeError("Original uncaught failure")

    def collect(_: Any) -> Any:
        raise ValueError("secret-token person@example.test")

    def cleanup(_: Any, action: str) -> str:
        cleaned.append(action)
        if outcome == "cleanup-error":
            raise OSError("Original cleanup failure")
        return ""

    monkeypatch.setattr(runner.Acceptance, "run", run)
    monkeypatch.setattr(runner.Acceptance, "fixture", cleanup)
    if outcome == "diagnostic-error":
        monkeypatch.setattr(runner.FatalLogWindow, "collect", collect)
    monkeypatch.setattr(
        sys,
        "argv",
        ["admin-mfa", "offline"] + (["--keep-fixture"] if outcome == "keep" else []),
    )
    if outcome in {"uncaught", "cleanup-error"}:
        with pytest.raises(
            TypeError if outcome == "uncaught" else OSError, match="Original"
        ):
            runner.main()
    else:
        assert runner.main() == (1 if outcome in {"failure", "diagnostic-error"} else 0)
    assert cleaned == ([] if outcome == "keep" else ["cleanup"])
    assert all(stream.closed for stream in runner.opened_log_files)
