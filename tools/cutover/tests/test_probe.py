"""Multi-endpoint proof against a real loopback HTTP server and temp filesystem."""

import json
import sys
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from linker_cutover import atomic, plan, probe
from linker_cutover.target import Target


@pytest.fixture
def proof_site(tmp_path: Path) -> Iterator[tuple[Target, dict[str, str]]]:
    replies: dict[str, str] = {}

    class Site(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in replies:
                body = replies[path]
            elif path.endswith("catalog-search"):
                body = '{"items":[]}'
            elif path == "/wp-json/wp/v2/pages":
                body = json.dumps(
                    [
                        {
                            "id": 1,
                            "link": f"http://127.0.0.1:{server.server_port}/de/test/",
                        }
                    ]
                )
            elif path.endswith("conversation"):
                body = '{"conversation_id":0,"messages":[]}'
            else:
                body = '<html lang="en"><body>fixture</body></html>'
            self.send_response(200)
            if body == "truncated-response":
                replies.pop(path)  # One failed HTTP response; readback can run.
                self.send_header("Content-Length", str(len(body) + 1))
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    root = tmp_path / "site"
    (root / "wp-content/uploads/wc-logs").mkdir(parents=True)
    try:
        yield (
            Target(
                "fixture",
                str(root),
                f"http://127.0.0.1:{server.server_port}",
                (),
                None,
                None,
            ),
            replies,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_probe_hits_required_pages_and_each_plugin_during_real_local_switch(
    proof_site: tuple[Target, dict[str, str]], tmp_path: Path
) -> None:
    target, _ = proof_site
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    artifacts = []
    for slug in plan.NEW_PLUGINS:
        relative = f"{plan.PLUGINS_DIR}/{slug}"
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
        artifacts.append(atomic.Artifact(source, relative))

    def deploy(switch_started: Callable[[], None]) -> int:
        receipt = atomic.publish(
            target,
            artifacts,
            deploy_id="20261018T000000Z-probe",
            on_switch=switch_started,
        )
        atomic.archive(target, receipt)
        return 0

    result = probe.observe(target, deploy, evidence=tmp_path / "evidence")

    assert result.successful
    assert {
        sample.endpoint for sample in result.samples if sample.phase == "during"
    } == {
        "home",
        "contact",
        "proforma",
        "product",
        "commerce-rest",
        "i18n-rest",
        "tools-rest",
    }
    assert result.fatal_logs_unchanged
    assert result.directory_rename_proved
    assert (tmp_path / "evidence/proof.json").is_file()


def test_invalid_rest_baseline_does_not_start_deploy(
    proof_site: tuple[Target, dict[str, str]], tmp_path: Path
) -> None:
    target, replies = proof_site
    replies["/wp-json/linker-ai/v1/genie/conversation"] = "{}"
    started = []

    def deploy(switch_started: Callable[[], None]) -> int:
        started.append(True)
        return 0

    with pytest.raises(RuntimeError, match="baseline.*tools-rest"):
        probe.observe(target, deploy, evidence=tmp_path / "evidence")
    assert not started


@pytest.mark.parametrize("failure", ["fatal-log", "rest-body"])
def test_probe_fails_on_new_fatal_or_invalid_endpoint_even_when_rename_succeeds(
    proof_site: tuple[Target, dict[str, str]], tmp_path: Path, failure: str
) -> None:
    target, replies = proof_site
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    artifacts = []
    for slug in plan.NEW_PLUGINS:
        relative = f"{plan.PLUGINS_DIR}/{slug}"
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
        artifacts.append(atomic.Artifact(source, relative))

    def deploy(switch_started: Callable[[], None]) -> int:
        receipt = atomic.publish(
            target,
            artifacts,
            deploy_id="20261018T000000Z-failed-probe",
            on_switch=switch_started,
        )
        atomic.archive(target, receipt)
        if failure == "fatal-log":
            Path(
                target.path_of("wp-content/uploads/wc-logs/fatal-errors-fixture.log")
            ).write_text("fixture fatal\n")
        else:
            replies["/wp-json/linker-ai/v1/genie/conversation"] = "{}"
        return 0

    result = probe.observe(target, deploy, evidence=tmp_path / "evidence")
    assert not result.successful
    assert result.directory_rename_proved
    assert result.deploy_exit == 0
    assert result.fatal_logs_unchanged == (failure != "fatal-log")
    if failure == "rest-body":
        assert any(
            sample.endpoint == "tools-rest" and not sample.valid
            for sample in result.samples
        )


def test_probe_samples_slowly_until_switch_then_densely_through_readback(
    proof_site: tuple[Target, dict[str, str]], tmp_path: Path
) -> None:
    """Round 3's lighter probe uses one aggregate stream, not one per endpoint."""
    site, _ = proof_site
    active, peak = 0, 0
    request_lock = threading.Lock()

    class ObservedTarget(Target):
        def http(
            self, path: str, *, cache_buster: str | None = None
        ) -> tuple[int, str]:
            nonlocal active, peak
            with request_lock:
                active += 1
                peak = max(peak, active)
            try:
                return super().http(path, cache_buster=cache_buster)
            finally:
                with request_lock:
                    active -= 1

    target = ObservedTarget(site.label, site.root, site.base_url, (), None, None)
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    artifacts = []
    for slug in plan.NEW_PLUGINS:
        relative = f"{plan.PLUGINS_DIR}/{slug}"
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
        artifacts.append(atomic.Artifact(source, relative))

    def deploy(switch_started: Callable[[], None]) -> int:
        # At one request/s, this build/upload stand-in admits at most starts
        # at 0, 1, 2 s; the old per-endpoint 0.1 s loop floods this interval.
        time.sleep(2.2)
        receipt = atomic.publish(
            target,
            artifacts,
            deploy_id="20261018T000000Z-cadence",
            on_switch=switch_started,
        )
        # At 0.1 s aggregate spacing, a full seven-endpoint sweep fits before
        # this verify/readback stand-in ends, even with local HTTP overhead.
        time.sleep(1.2)
        atomic.archive(target, receipt)
        return 0

    result = probe.observe(target, deploy, evidence=tmp_path / "cadence-proof")

    assert result.successful
    during = [sample for sample in result.samples if sample.phase == "during"]
    steady = [sample for sample in during if sample.cadence == "steady"]
    dense = [sample for sample in during if sample.cadence == "dense"]
    assert 1 <= len(steady) <= 3
    assert {sample.endpoint for sample in dense} == {
        endpoint.name for endpoint in plan.DEPLOY_PROBE_ENDPOINTS
    }
    assert len(dense) > len(steady)
    assert peak == 1  # Round 3 load cap: one outstanding probe GET.


def test_deployment_process_signals_switch_before_it_finishes(tmp_path: Path) -> None:
    """The actual child-process pipe must notify the observer before readback."""
    acknowledgement = tmp_path / "observer-saw-switch"
    # The child waits for an acknowledgement: a buffered/late callback cannot
    # masquerade as a switch-time notification. Five seconds bounds the fixture.
    script = (
        "import pathlib, time\n"
        f"ack = pathlib.Path({str(acknowledgement)!r})\n"
        "print('build/upload', flush=True)\n"
        "print('LINKER_CUTOVER_SWITCH_START', flush=True)\n"
        "deadline = time.monotonic() + 5\n"
        "while not ack.exists() and time.monotonic() < deadline: time.sleep(0.01)\n"
        "print('readback', flush=True)\n"
        "raise SystemExit(0 if ack.exists() else 1)\n"
    )
    log = tmp_path / "deploy.log"

    status = probe.run_deployment(
        [sys.executable, "-c", script],
        repository=tmp_path,
        log=log,
        on_switch=lambda: acknowledgement.touch(),
    )

    assert status == 0
    assert log.read_text().splitlines() == [
        "build/upload",
        "LINKER_CUTOVER_SWITCH_START",
        "readback",
    ]


def test_probe_reports_failed_worker_instead_of_waiting_forever(
    proof_site: tuple[Target, dict[str, str]], tmp_path: Path
) -> None:
    """A real truncated response ends the observer with failed proof evidence."""
    target, replies = proof_site
    source = tmp_path / "release"
    source.mkdir()
    (source / "plugin.php").write_text("new")
    artifacts = []
    for slug in plan.NEW_PLUGINS:
        relative = f"{plan.PLUGINS_DIR}/{slug}"
        live = Path(target.path_of(relative))
        live.mkdir(parents=True)
        (live / "plugin.php").write_text("old")
        artifacts.append(atomic.Artifact(source, relative))

    def deploy(switch_started: Callable[[], None]) -> int:
        replies["/"] = "truncated-response"
        receipt = atomic.publish(
            target,
            artifacts,
            deploy_id="20261018T000000Z-worker-failure",
            on_switch=switch_started,
        )
        atomic.archive(target, receipt)
        return 0

    results: list[probe.Proof] = []
    evidence = tmp_path / "failed-worker-proof"
    observer = threading.Thread(
        target=lambda: results.append(probe.observe(target, deploy, evidence=evidence)),
        daemon=True,
    )
    observer.start()
    # A dense seven-endpoint loopback sweep takes under a second. Five seconds
    # bounds this regression so a dead watcher cannot hang the whole suite.
    observer.join(timeout=5)

    assert not observer.is_alive(), "probe hung after its sampling worker exited"
    assert not results[0].successful
    assert "IncompleteRead" in " ".join(results[0].notes)
    assert (evidence / "proof.json").is_file()
