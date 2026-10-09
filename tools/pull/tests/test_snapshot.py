"""Taking a snapshot, with the host replaced by a local directory and the fixture dump.

rsync is the real one (macOS openrsync here, rsync 3 in CI) copying from a
local tree shaped like the live wp-content of 2026-10-09; the dump is
tests/fixtures/live-dump.sql; every other host call answers what the live
host answered.
"""

from __future__ import annotations

import fcntl
import gzip
import json
import shutil
import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from typing import IO

import jsonschema
import pytest

from linker_pull import live, manifest, snapshot
from linker_pull.anonymize import accounts_from_dump

FIXTURE = Path(__file__).parent / "fixtures" / "live-dump.sql"
SCHEMA = Path(__file__).parent.parent / "manifest.schema.json"

LIVE_FILES = {
    "wp-content/uploads/2026/07/logo.webp": "image",
    "wp-content/uploads/2026/07/logo-150x150.webp": "thumbnail",
    "wp-content/uploads/woocommerce-placeholder.webp": "placeholder",
    "wp-content/uploads/windpress/cache/tailwind.css": "css",
    "wp-content/uploads/wc-logs/transactional-emails.log": "jdoe@kunde.example",
    "wp-content/uploads/tv-b2b-private/business-document-18.pdf": "private",
    "wp-content/uploads/woocommerce_uploads/.htaccess": "deny from all",
    "wp-content/plugins/index.php": "<?php // Silence is golden.",
    "wp-content/plugins/livecanvas/livecanvas.php": "<?php",
    "wp-content/plugins/wp-seopress/seopress.php": "<?php",
    "wp-content/plugins/wp-seopress-pro/seopress-pro.php": "<?php",
    "wp-content/plugins/windpress/windpress.php": "<?php",
    "wp-content/plugins/terravolt-b2b-core/terravolt-b2b-core.php": "<?php",
    "wp-content/plugins/linker-i18n/linker-i18n.php": "<?php",
    "wp-content/mu-plugins/linker-i18n-mu-loader.php": "<?php",
    "wp-content/mu-plugins/hostinger-auto-updates.php": "<?php",
    "wp-content/themes/picostrap5/style.css": "/* parent */",
    "wp-content/themes/picostrap5-child-base/style.css": "/* child */",
    "wp-content/themes/twentytwentyfive/style.css": "/* inactive */",
}
PLUGINS = [
    {
        "name": "livecanvas",
        "status": "active",
        "version": "4.9.3",
        "file": "livecanvas/livecanvas.php",
    },
    {
        "name": "terravolt-b2b-core",
        "status": "active",
        "version": "0.12.413",
        "file": "terravolt-b2b-core/terravolt-b2b-core.php",
    },
]
THEMES = [
    {"name": "picostrap5-child-base", "status": "active", "version": "3.1.4"},
    {"name": "picostrap5", "status": "parent", "version": "3.5.0"},
    {"name": "twentytwentyfive", "status": "inactive", "version": "1.5"},
]
SITEMAP = (
    b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    b"<url><loc>https://de-linker.com/de/</loc></url></urlset>"
)


class Clock:
    """datetime for snapshot.py: a minute later on every call, so names differ."""

    current = datetime(2026, 10, 9, 21, 0)

    @classmethod
    def now(cls, tz: object = None) -> datetime:
        cls.current += timedelta(minutes=1)
        return cls.current


@pytest.fixture
def host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "host"
    for relative, content in LIVE_FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    dump = tmp_path / "dump.sql"
    shutil.copy(FIXTURE, dump)

    def wp(*args: str) -> str:
        assert args == ("core", "version")
        return "7.1.3\n"

    def wp_json(*args: str) -> object:
        return {"plugin": PLUGINS, "theme": THEMES}[args[0]]

    monkeypatch.setattr(live, "ORIGIN", str(root))
    monkeypatch.setattr(live, "wp", wp)
    monkeypatch.setattr(live, "wp_json", wp_json)
    monkeypatch.setattr(
        live,
        "accounts",
        lambda: accounts_from_dump(iter(dump.read_text().splitlines(True))),
    )
    monkeypatch.setattr(live, "dump", dumping(dump))
    monkeypatch.setattr(live, "sitemaps", lambda: {"de-sitemap.xml": SITEMAP})
    monkeypatch.setattr(snapshot, "datetime", Clock)
    monkeypatch.setattr(Clock, "current", datetime(2026, 10, 9, 21, 0))
    yield root


def dumping(sql: Path) -> Callable[[IO[bytes]], subprocess.Popen[bytes]]:
    """A stand-in for live.dump(): the file, gzip-compressed, on standard output."""

    def dump(stderr: IO[bytes]) -> subprocess.Popen[bytes]:
        return subprocess.Popen(
            ["gzip", "-c", str(sql)], stdout=subprocess.PIPE, stderr=stderr
        )

    return dump


def files_under(path: Path) -> set[str]:
    return {
        entry.relative_to(path).as_posix()
        for entry in path.rglob("*")
        if entry.is_file()
    }


def test_a_snapshot_holds_the_pseudonymized_database_and_the_files_it_needs(
    host: Path, tmp_path: Path
) -> None:
    data = tmp_path / "data"

    taken = snapshot.take(data, lambda message: None)

    assert taken == data / "20261009-2101"
    assert sorted(path.name for path in data.iterdir()) == [
        ".snapshot.lock",
        "20261009-2101",
    ]
    assert files_under(taken / "uploads") == {
        "2026/07/logo.webp",
        "2026/07/logo-150x150.webp",
        "woocommerce-placeholder.webp",
        "windpress/cache/tailwind.css",
    }
    assert files_under(taken / "plugins") == {
        "livecanvas/livecanvas.php",
        "wp-seopress/seopress.php",
        "wp-seopress-pro/seopress-pro.php",
        "windpress/windpress.php",
    }
    assert files_under(taken / "themes") == {
        "picostrap5/style.css",
        "picostrap5-child-base/style.css",
    }
    assert files_under(taken / "live") == {
        "plugins/index.php",
        "plugins/terravolt-b2b-core/terravolt-b2b-core.php",
        "plugins/linker-i18n/linker-i18n.php",
        "mu-plugins/linker-i18n-mu-loader.php",
    }
    with gzip.open(taken / "db.sql.gz", "rt") as dump:
        text = dump.read()
    assert "jdoe@kunde.example" not in text and "$wp$" not in text
    options = json.loads((taken / "site" / "options.json").read_text())
    names = {entry["option_name"] for entry in options}
    assert (
        "siteurl" in names
        and "lc_apikey" not in names
        and "_transient_feed_abc" not in names
    )
    assert json.loads((taken / "site" / "themes.json").read_text()) == THEMES
    assert (taken / "site" / "sitemaps" / "de-sitemap.xml").read_bytes() == SITEMAP

    written = manifest.read(taken)
    jsonschema.validate(written, json.loads(SCHEMA.read_text()))
    assert written["source"] == {
        "host": "hostinger-de-linker",
        "url": "https://de-linker.com",
        "wordpress": "7.1.3",
    }
    assert written["database"]["posts"]["product/publish"] == 1
    assert written["database"]["check"]["clean"] is True
    assert set(written["files"]) == files_under(taken) - {"manifest.json"}


def test_the_next_snapshot_links_what_did_not_change_and_the_manifests_say_what_did(
    host: Path, tmp_path: Path
) -> None:
    data = tmp_path / "data"
    first = snapshot.take(data, lambda message: None)
    (host / "wp-content/uploads/2026/07/logo.webp").write_text("image, edited")
    (host / "wp-content/uploads/2026/07/new.pdf").write_text("datasheet")
    (host / "wp-content/uploads/2026/07/logo-150x150.webp").unlink()

    second = snapshot.take(data, lambda message: None)

    assert snapshot.latest(data) == second
    css = "uploads/windpress/cache/tailwind.css"
    assert (first / css).stat().st_ino == (second / css).stat().st_ino
    changes = manifest.diff(manifest.read(first), manifest.read(second))
    assert changes.added == ["uploads/2026/07/new.pdf"]
    assert changes.removed == ["uploads/2026/07/logo-150x150.webp"]
    assert changes.changed == ["uploads/2026/07/logo.webp"]
    assert changes.tables == {}  # the same dump pseudonymizes to the same rows


def test_a_dump_that_fails_its_check_leaves_no_snapshot_and_no_sql(
    host: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leaky = tmp_path / "leaky.sql"
    leaky.write_text(
        FIXTURE.read_text().replace(
            "Hybrid inverter.", "Hybrid inverter, old hash $P$."
        )
    )
    monkeypatch.setattr(live, "dump", dumping(leaky))
    data = tmp_path / "data"

    with pytest.raises(snapshot.SnapshotError, match="failed its check"):
        snapshot.take(data, lambda message: None)

    assert snapshot.latest(data) is None
    assert not list(data.rglob("*.sql.gz"))


def test_a_dump_cut_short_fails_with_what_the_host_said(
    host: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def cut(stderr: IO[bytes]) -> subprocess.Popen[bytes]:
        script = f"gzip -c {FIXTURE} | head -c 2000; echo 'mysqldump: Lost connection' >&2; exit 2"
        return subprocess.Popen(
            ["bash", "-c", script], stdout=subprocess.PIPE, stderr=stderr
        )

    monkeypatch.setattr(live, "dump", cut)
    data = tmp_path / "data"

    with pytest.raises(snapshot.SnapshotError, match="Lost connection"):
        snapshot.take(data, lambda message: None)

    assert not list(data.rglob("*.sql.gz"))


def test_one_snapshot_at_a_time(host: Path, tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    with (data / snapshot.LOCK).open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        with pytest.raises(snapshot.SnapshotError, match="another snapshot"):
            snapshot.take(data, lambda message: None)

    assert snapshot.take(data, lambda message: None) == data / "20261009-2101"
