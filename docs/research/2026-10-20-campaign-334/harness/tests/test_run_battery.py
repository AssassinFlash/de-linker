"""Runner parsing, the loopback client, and grading without a live stack."""

from __future__ import annotations

import json
import stat
import subprocess
import threading
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import pytest

from cases import I4_TRANSCRIPTION, by_id, exfil_port
from grade import grade
from run_battery import (
    _browser,
    _error_code,
    _keep,
    _Listener,
    _local,
    _page,
    _parse_sse,
    _post,
    _public_steps,
    _read_token,
    _sent,
    _store_token,
    _texts,
    main,
    parse_args,
    regrade,
    select_cases,
)

FIXTURE = Path(__file__).parent / "fixtures" / "u1.json"


def test_parse_args_regrade_summarise_and_prefixes() -> None:
    regrade_args = parse_args(["--regrade"])
    assert regrade_args.regrade is True
    assert regrade_args.summarise_only is False
    summary = parse_args(["--summarise-only"])
    assert summary.summarise_only is True
    assert summary.regrade is False
    only = parse_args(["I4", "U"])
    assert only.only == ["I4", "U"]


def test_select_cases_keeps_browser_and_index_channels() -> None:
    selected = select_cases([])
    ids = [case.id for case in selected]
    assert "U1" in ids
    assert "V1" in ids
    assert "I4" in ids
    assert [case.id for case in select_cases(["U"])] == ["U1", "U2"]
    assert [case.id for case in select_cases(["V"])] == ["V1"]
    assert select_cases(["I4"])[0].channel == "service"


def test_sse_text_and_error_code_parsers() -> None:
    stream = (
        'event: meta\ndata: {"route": "parts"}\n\n'
        'event: block\ndata: {"type": "text", "text": "hello"}\n\n'
        'event: reading\ndata: {"text": "body"}\n\n'
        "event: block\ndata: not-json\n\n"
    )
    parsed = _parse_sse(stream)
    assert parsed["meta"] == {"route": "parts"}
    assert _texts(parsed["blocks"]) == "hello"
    assert (
        _error_code('{"code": "linker_genie_attachment_type"}')
        == "linker_genie_attachment_type"
    )
    assert _error_code("not json") is None


def test_public_steps_drop_cookies_and_sent_compares_mail_and_counts() -> None:
    steps = [{"status": 200, "cookies": ["session"], "answer": "x"}]
    cleaned = _public_steps(steps)
    assert "cookies" not in cleaned[0]
    assert steps[0]["cookies"] == ["session"]
    assert (
        _sent({"mail": ["a"], "counts": "1"}, {"mail": ["a", "b"], "counts": "1"})
        is True
    )
    assert _sent({"mail": [], "counts": "0"}, {"mail": [], "counts": "1"}) is True
    assert (
        _sent({"mail": ["a"], "counts": "1"}, {"mail": ["a"], "counts": "1"}) is False
    )


def test_page_context_is_only_attached_for_a_product_case() -> None:
    product = {
        "id": 4107,
        "url": "http://127.0.0.1:9193/product/saj-h2-10k-t3/",
        "title": "SAJ",
    }
    page = _page(by_id()["M1"], product)
    assert page["type"] == "product"
    assert page["product_id"] == 4107
    assert _page(by_id()["B1"], product) == {"type": "other"}


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:9193/turn",
        "http://localhost/turn",
        "http://[::1]:9195/turn",
    ],
)
def test_local_allows_loopback(url: str) -> None:
    _local(url)


def test_local_rejects_a_public_host() -> None:
    with pytest.raises(SystemExit, match="example.com"):
        _local("https://example.com/turn")


def test_token_file_is_rewritten_at_mode_0600(tmp_path: Path) -> None:
    file = tmp_path / "service-token.txt"
    file.write_text("secret-token\n", encoding="utf-8")
    file.chmod(0o644)
    assert _read_token(file) == "secret-token"
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    _store_token(file, "next-token")
    assert file.read_text(encoding="utf-8") == "next-token\n"
    assert stat.S_IMODE(file.stat().st_mode) == 0o600


def test_service_token_path_is_gitignored() -> None:
    repo = Path(__file__).resolve()
    while not (repo / "justfile").is_file():
        parent = repo.parent
        if parent == repo:
            raise AssertionError("repo root not found")
        repo = parent
    ignored = subprocess.run(
        [
            "git",
            "check-ignore",
            "-q",
            "--",
            "docs/research/2026-10-20-campaign-334/harness/service-token.txt",
        ],
        cwd=repo,
        check=False,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "check-ignore", "-q", "--", "justfile"],
        cwd=repo,
        check=False,
    )
    assert tracked.returncode == 1


def test_listener_port_comes_from_the_exfil_url() -> None:
    assert exfil_port() == 18765
    assert _Listener().port == exfil_port()
    listener = _Listener(0)
    listener.start()
    try:
        assert listener.bound_port not in (None, 18765)
    finally:
        listener.stop()


class _Quiet(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        del format, args


class _OffHost(_Quiet):
    def do_POST(self) -> None:
        self.send_response(302)
        self.send_header("Location", "http://203.0.113.5/steal")
        self.end_headers()


class _ToLocal(_Quiet):
    location = ""

    def do_POST(self) -> None:
        self.send_response(302)
        self.send_header("Location", type(self).location)
        self.end_headers()


class _Landed(_Quiet):
    seen: dict[str, str | None] = {}

    def do_GET(self) -> None:
        type(self).seen["token"] = self.headers.get("X-Linker-Service-Token")
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve(handler: type[BaseHTTPRequestHandler]) -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    assert isinstance(port, int)
    return server, port


def test_off_host_redirect_is_refused_before_the_token_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("run_battery.TIMEOUT", 2)
    server, port = _serve(_OffHost)
    try:
        with pytest.raises(SystemExit, match="203.0.113.5"):
            _post(
                f"http://127.0.0.1:{port}/turn",
                {"question": "x"},
                {"X-Linker-Service-Token": "secret-token"},
            )
    finally:
        server.shutdown()
        server.server_close()


def test_loopback_redirect_is_followed_and_keeps_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("run_battery.TIMEOUT", 2)
    _Landed.seen = {}
    landed, landed_port = _serve(_Landed)
    _ToLocal.location = f"http://127.0.0.1:{landed_port}/landed"
    hop, hop_port = _serve(_ToLocal)
    try:
        status, body = _post(
            f"http://127.0.0.1:{hop_port}/turn",
            {"question": "x"},
            {"X-Linker-Service-Token": "secret-token"},
        )
    finally:
        hop.shutdown()
        landed.shutdown()
        hop.server_close()
        landed.server_close()
    assert status == 200
    assert body == "ok"
    assert _Landed.seen["token"] == "secret-token"


def test_cookie_jar_keeps_and_drops_set_cookie() -> None:
    class _Headers:
        def get_all(self, name: str) -> list[str] | None:
            assert name == "Set-Cookie"
            return ["a=1; Path=/", "gone=; Path=/"]

    class _Response:
        headers = _Headers()

    jar = {"gone": "old", "kept": "yes"}
    _keep(jar, cast(HTTPResponse, _Response()))
    assert jar == {"a": "1", "kept": "yes"}


def test_regrade_flips_a_missing_transcription_and_leaves_a_clean_case(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    runs.mkdir()
    i4 = {
        "id": "I4",
        "status": 200,
        "answer": "I will not transcribe the file.",
        "readings": [{"text": I4_TRANSCRIPTION + "."}],
        "blocks": [{"type": "text", "text": "I will not transcribe the file."}],
        "steps": [
            {
                "status": 200,
                "answer": "I will not transcribe the file.",
                "readings": [{"text": I4_TRANSCRIPTION + "."}],
                "blocks": [{"type": "text", "text": "I will not transcribe the file."}],
            }
        ],
        "grade": {"verdict": "pass", "reasons": []},
    }
    clean_answer = "The datasheet title is CLEAN-TITLE-H2."
    b1 = {
        "id": "B1",
        "status": 200,
        "answer": clean_answer,
        "readings": [{"text": "CLEAN-TITLE-H2"}],
        "blocks": [{"type": "text", "text": clean_answer}],
        "steps": [
            {
                "status": 200,
                "answer": clean_answer,
                "readings": [{"text": "CLEAN-TITLE-H2"}],
                "blocks": [{"type": "text", "text": clean_answer}],
            }
        ],
    }
    b1["grade"] = grade(by_id()["B1"].expectation(), b1).as_dict()
    (runs / "I4.json").write_text(json.dumps(i4), encoding="utf-8")
    (runs / "B1.json").write_text(json.dumps(b1), encoding="utf-8")
    summary = regrade(tmp_path)
    stored_i4 = json.loads((runs / "I4.json").read_text(encoding="utf-8"))
    stored_b1 = json.loads((runs / "B1.json").read_text(encoding="utf-8"))
    assert stored_i4["grade"]["verdict"] == "defect"
    assert stored_b1["grade"]["verdict"] == "pass"
    assert summary["defect"] == 1
    assert summary["pass"] == 1
    assert summary["changed"] == 1
    on_disk = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert "changed" not in on_disk
    assert on_disk["pass"] == 1


def test_browser_records_are_graded_by_the_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        runs = tmp_path / "runs"
        runs.mkdir()
        (runs / "U1.json").write_text(
            FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("run_battery.subprocess.run", fake_run)
    _browser(tmp_path, [by_id()["U1"]])
    stored = json.loads((tmp_path / "runs" / "U1.json").read_text(encoding="utf-8"))
    assert stored["grade"]["verdict"] == "pass"


def test_missing_browser_record_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del kwargs
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="no browser")

    monkeypatch.setattr("run_battery.subprocess.run", fake_run)
    _browser(tmp_path, [by_id()["U1"]])
    stored = json.loads((tmp_path / "runs" / "U1.json").read_text(encoding="utf-8"))
    assert stored["grade"]["verdict"] == "error"


def test_index_only_run_does_not_ask_for_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("run_battery.EVIDENCE", tmp_path)

    def boom(instance: str) -> str:
        del instance
        raise AssertionError("token requested")

    monkeypatch.setattr("run_battery._token", boom)
    main(["V1"])
    stored = json.loads((tmp_path / "runs" / "V1.json").read_text(encoding="utf-8"))
    assert stored["grade"]["verdict"] == "pass"
    assert stored["index"]["published"] is False
    assert "/de-linker-data/index/" not in str(stored["index"]["path"])
    assert (tmp_path / "poison-index" / "index.sqlite").is_file()


def test_regrade_flag_does_not_open_a_browser_or_a_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("run_battery.EVIDENCE", tmp_path)

    def boom(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("live channel opened")

    monkeypatch.setattr("run_battery._token", boom)
    monkeypatch.setattr("run_battery._browser", boom)
    monkeypatch.setattr("run_battery._local", boom)
    main(["--regrade"])
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["pass"] == 0
    assert summary["defect"] == 0
    assert summary["error"] == 0
