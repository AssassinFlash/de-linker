"""The commands as `just pull …` runs them: arguments, exit statuses, what they print."""

from __future__ import annotations

import gzip
import json
import shutil
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from linker_pull import manifest
from linker_pull.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "live-dump.sql"


def write_manifest(directory: Path, files: dict[str, str], products: int) -> Path:
    directory.mkdir(parents=True)
    manifest.write(
        directory,
        {
            "format": manifest.FORMAT,
            "files": {
                path: {"sha256": digest * 64, "bytes": 1}
                for path, digest in files.items()
            },
            "database": {
                "tables": {
                    "wp_posts": {"rows": products, "sha256": str(products % 10) * 64}
                },
                "posts": {"product/publish": products},
            },
        },
    )
    return directory


@pytest.fixture
def data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "data"
    monkeypatch.setenv("LINKER_PULL_DATA", str(root))
    write_manifest(
        root / "20261009-2144", {"db.sql.gz": "a", "uploads/a.webp": "b"}, 106
    )
    write_manifest(
        root / "20261009-2210", {"db.sql.gz": "c", "uploads/a.webp": "b"}, 107
    )
    return root


def test_snapshots_are_named_by_path_by_name_or_latest(
    data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["diff", str(data / "20261009-2144"), "latest"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "files: 0 added, 0 removed, 1 changed, 1 unchanged",
        "  ~ db.sql.gz",
        "tables: 1 changed",
        "  ~ wp_posts: 106 -> 107 rows",
        "posts: 1 counts changed",
        "  ~ product/publish: 106 -> 107",
    ]
    assert main(["diff", "20261009-2144", "20261009-2210", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["posts"] == {
        "product/publish": {"before": 106, "after": 107}
    }


def test_an_unknown_snapshot_is_an_error_not_a_traceback(
    data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["diff", "20991231-2359", "latest"]) == 1
    assert "no snapshot 20991231-2359" in capsys.readouterr().err


def test_anonymize_writes_a_checked_dump(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "clean.sql.gz"

    assert main(["anonymize", str(FIXTURE), str(target)]) == 0

    printed = json.loads(capsys.readouterr().out)
    assert printed["check"]["clean"] is True
    assert printed["anonymization"]["rows_dropped"]["wp_actionscheduler_actions"] == 2
    with gzip.open(target, "rt") as dump:
        assert "jdoe@kunde.example" not in dump.read()


def test_anonymize_deletes_a_result_that_fails_its_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "leaky.sql"
    # "$P$" without a hash behind it is no hash to remove, but the check counts it.
    source.write_text(
        FIXTURE.read_text().replace("Hybrid inverter.", "Hybrid inverter $P$.")
    )
    target = tmp_path / "out.sql.gz"

    assert main(["anonymize", str(source), str(target)]) == 1

    assert json.loads(capsys.readouterr().out)["check"]["password_hashes"] == {"$P$": 1}
    assert not target.exists()


def test_scan_exits_1_on_a_leak(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.sql.gz"
    leaky = tmp_path / "leaky.sql.gz"
    main(["anonymize", str(FIXTURE), str(clean)])
    with gzip.open(leaky, "wb") as dump:
        dump.write(FIXTURE.read_bytes())
    capsys.readouterr()

    assert main(["scan", str(clean)]) == 0
    assert main(["scan", str(leaky)]) == 1


class Site(BaseHTTPRequestHandler):
    """A local instance that has /de/ and nothing else."""

    def do_GET(self) -> None:  # noqa: N802 (http.server's name)
        self.send_response(200 if self.path == "/de/" else 404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture
def site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Site)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def sitemap(*urls: str) -> bytes:
    entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
    return (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + entries
        + "</urlset>"
    ).encode()


def test_check_urls_requests_every_page_of_the_sitemap_from_the_instance(
    data: Path, site: str, capsys: pytest.CaptureFixture[str]
) -> None:
    sitemaps = data / "20261009-2210" / "site" / "sitemaps"
    sitemaps.mkdir(parents=True)
    (sitemaps / "de-sitemap.xml").write_bytes(
        sitemap("https://de-linker.com/de/", "https://de-linker.com/de/missing/")
    )
    (sitemaps / "page-sitemap1.xml").write_bytes(sitemap("https://de-linker.com/de/"))

    assert (
        main(["check-urls", "latest", "--base", site, "--sitemap", "de-sitemap.xml"])
        == 1
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed["statuses"] == {"200": 1, "404": 1}
    assert printed["not_200"] == ["404 /de/missing/"]

    assert (
        main(["check-urls", "latest", "--base", site, "--sitemap", "page-sitemap1.xml"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["statuses"] == {"200": 1}
    shutil.rmtree(sitemaps)
    assert main(["check-urls", "latest", "--base", site]) == 1


def test_local_load_holds_retirement_lock_from_lookup_through_all_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argparse import Namespace

    from linker_local import retirement
    from linker_local.instance import Instance

    from linker_pull import cli, load

    monkeypatch.setenv("LINKER_LOCAL_HOME", str(tmp_path))
    instance = Instance("owned", 19001, 19002, 19003, tmp_path)
    seen: list[str] = []

    def lookup(name: str, port: int | None) -> Instance:
        with pytest.raises(RuntimeError, match="already being managed"):
            retirement.retire(
                tmp_path, name, write=True, preserve=[], discard=[], preserve_to=None
            )
        seen.append("lookup")
        return instance

    def write(*args: object) -> dict[str, object]:
        with pytest.raises(RuntimeError, match="already being managed"):
            retirement.retire(
                tmp_path,
                instance.name,
                write=True,
                preserve=[],
                discard=[],
                preserve_to=None,
            )
        seen.append("write")
        return {"ok": True}

    monkeypatch.setattr(load, "instance", lookup)
    monkeypatch.setattr(load, "load", write)
    monkeypatch.setattr(cli, "_snapshot", lambda _: tmp_path)
    args = Namespace(name=instance.name, port=None, snapshot="fixture", live_code=False)
    assert cli.load_snapshot(args) == 0
    assert seen == ["lookup", "write"]
    retirement.marker_path(tmp_path, instance.name).write_text("{}")
    with pytest.raises(RuntimeError, match="retirement is incomplete"):
        cli.load_snapshot(args)
    assert seen == ["lookup", "write"]
