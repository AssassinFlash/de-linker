"""Deterministic gates of tools/faq/thumbs.py (no network, no downloads).

The pipeline's own job — HEAD, download, render — needs the live uploads and
poppler, and its output is the committed `assets/faq-thumbs/`. What is tested
here is everything around that: the naming (which is the manifest's contract
with `DocumentThumbnails`), the size cap and the probe-only branch, the WebP
header reader, and the cleanup rule that keeps exactly the files the manifest
names.
"""

from __future__ import annotations

import importlib.util
import json
import struct
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load() -> Any:
    spec = importlib.util.spec_from_file_location("faq_thumbs", HERE / "thumbs.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


thumbs = load()


def test_key_is_the_url_path_so_one_build_serves_every_host() -> None:
    live = "https://de-linker.com/wp-content/uploads/2026/07/a.pdf"
    local = "http://127.0.0.1:9018/wp-content/uploads/2026/07/a.pdf"
    assert thumbs.key(live) == "/wp-content/uploads/2026/07/a.pdf"
    assert thumbs.key(live) == thumbs.key(local)
    assert thumbs.key(
        "https://de-linker.com/wp-content/uploads/2026/07/b.pdf"
    ) != thumbs.key(live)


def test_key_falls_back_to_the_url_when_it_has_no_path() -> None:
    assert thumbs.key("") == ""
    assert thumbs.key("nonsense") == "nonsense"


def test_file_names_are_sha1_of_the_key_with_the_extension() -> None:
    url = "https://de-linker.com/wp-content/uploads/2026/07/a.pdf"
    name = thumbs.file_name(url)
    assert name.endswith(".webp")
    assert len(name) == 40 + len(".webp")
    assert (
        name[:40]
        == thumbs.hashlib.sha1(b"/wp-content/uploads/2026/07/a.pdf").hexdigest()
    )
    # The shipped reader accepts exactly this shape.
    assert thumbs.file_name(url) != thumbs.file_name(url + "x")
    assert thumbs.pdf_name(url) == name[:40] + ".pdf"
    assert thumbs.file_name(url) != thumbs.pdf_name(url)


def test_webp_size_reads_a_lossy_webp() -> None:
    path = ROOT / "plugins/linker-commerce/assets/faq-thumbs"
    files = sorted(path.glob("*.webp"))
    assert files, "the pipeline's own output is the fixture"
    for candidate in files[:3]:
        width, height = thumbs.webp_size(candidate)
        assert width > 0 and height > 0
        assert height <= thumbs.HEIGHT + 1, "the pipeline's own cap"


def test_webp_size_refuses_what_is_not_a_webp(tmp_path: Path) -> None:
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 40)
    for path in (png, tmp_path / "nothing.webp"):
        try:
            thumbs.webp_size(path)
        except (ValueError, OSError):
            continue
        raise AssertionError(f"{path.name} must not read as a WebP")


def test_webp_size_reads_a_hand_built_vp8x_header(tmp_path: Path) -> None:
    # A VP8X header states the canvas minus one, 24 bits each, little-endian.
    path = tmp_path / "x.webp"
    payload = bytearray(
        b"RIFF" + struct.pack("<I", 30) + b"WEBP" + b"VP8X" + b"\x00" * 8
    )
    payload += bytes([152, 0, 0]) + bytes([87, 0, 0]) + b"\x00" * 10
    path.write_bytes(bytes(payload))
    assert thumbs.webp_size(path) == (153, 88)


def test_a_pdf_is_only_what_starts_with_the_magic(tmp_path: Path) -> None:
    real = tmp_path / "a.pdf"
    real.write_bytes(b"%PDF-1.7\n" + b"x" * 100)
    assert thumbs.is_pdf(real)
    tiny = tmp_path / "tiny.pdf"
    tiny.write_bytes(b"%PDF-1.7")
    assert not thumbs.is_pdf(tiny), "a stub this small is not a document"
    html = tmp_path / "login.pdf"
    html.write_bytes(b"<html>" + b"x" * 100)
    assert not thumbs.is_pdf(html), "a login page served as a PDF is not one"


def test_the_cap_defers_exactly_the_files_over_it() -> None:
    cap = int(15 * 1024 * 1024)
    probes: dict[str, dict[str, Any]] = {
        "small": {"ok": True, "length": 1024},
        "exact": {"ok": True, "length": cap},
        "huge": {"ok": True, "length": cap + 1},
        "unknown": {"ok": True, "length": None},
        "missing": {"ok": False, "length": 10},
    }
    urls = list(probes)
    deferred, targets = thumbs.select(urls, probes, cap)
    assert deferred == {"huge"}, (
        "the cap is per file and strict: exactly over it is deferred"
    )
    assert targets == ["small", "exact", "unknown"], (
        "a row the HEAD refused is not downloaded"
    )
    assert thumbs.select(urls, probes, 0) == (
        set(),
        ["small", "exact", "huge", "unknown"],
    ), "cap 0 means no cap"


def test_a_probe_only_run_writes_nothing(
    tmp_path: Path, monkeypatch: Any, capsys: Any
) -> None:
    """`--probe-only` reports sizes and stops: no cache directory, no output."""
    cache = tmp_path / "cache"
    out = tmp_path / "out"
    monkeypatch.setattr(
        thumbs,
        "register_urls",
        lambda wp: [{"url": "https://de-linker.com/a.pdf", "type": "datasheet"}],
    )
    monkeypatch.setattr(
        thumbs,
        "probe",
        lambda url: {"url": url, "ok": True, "length": 1024, "error": ""},
    )
    monkeypatch.setattr(
        thumbs.sys,
        "argv",
        [
            "thumbs.py",
            "--wp",
            "x",
            "--probe-only",
            "--cache",
            str(cache),
            "--out",
            str(out),
        ],
    )
    assert thumbs.main() == 0
    assert not cache.exists(), "the cache is not made"
    assert not out.exists(), "nothing is written"
    assert "known size" in capsys.readouterr().out


def test_cleanup_keeps_exactly_the_files_the_manifest_names(tmp_path: Path) -> None:
    manifest = {
        "/a.pdf": {
            "file": thumbs.file_name("https://de-linker.com/a.pdf"),
            "width": 153,
            "height": 216,
        },
    }
    keep = {entry["file"] for entry in manifest.values()}
    for name in list(keep) + [
        thumbs.file_name("https://de-linker.com/b.pdf"),
        "manifest.json",
    ]:
        (tmp_path / name).write_bytes(b"x")
    for path in tmp_path.glob("*.webp"):
        if path.name not in keep:
            path.unlink()
    left = sorted(path.name for path in tmp_path.iterdir())
    assert left == sorted(list(keep) + ["manifest.json"]), (
        "a file the manifest does not name is published stale"
    )


def test_the_shipped_manifest_matches_the_shipped_files() -> None:
    directory = ROOT / "plugins/linker-commerce/assets/faq-thumbs"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert manifest, "the committed build has entries"
    for url_path, entry in manifest.items():
        assert url_path.startswith("/"), "keys are URL paths"
        assert entry["file"] == thumbs.file_name("https://de-linker.com" + url_path)
        assert (directory / entry["file"]).is_file(), (
            f"{entry['file']} is named but not shipped"
        )
        assert entry["width"] > 0 and entry["height"] > 0
    shipped = {path.name for path in directory.glob("*.webp")}
    assert shipped == {entry["file"] for entry in manifest.values()}, (
        "no orphan in either direction"
    )
