"""Multi-endpoint proof against a real loopback HTTP server and temp filesystem."""

import json
import threading
from collections.abc import Iterator
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

    def deploy() -> int:
        receipt = atomic.publish(target, artifacts, deploy_id="20261018T000000Z-probe")
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

    def deploy() -> int:
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

    def deploy() -> int:
        receipt = atomic.publish(
            target, artifacts, deploy_id="20261018T000000Z-failed-probe"
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
