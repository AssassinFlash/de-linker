#!/usr/bin/env python3
"""First-page thumbnails of the document register (/faq-download/).

The register lists whatever the products state (docs/specs/176-faq-download.md);
each document row shows page 1 of its PDF, 52x72 CSS pixels. Rendering those on
request would fetch and rasterise the live uploads for every visitor, so the
thumbnails are built once, here, and shipped with the plugin
(`plugins/linker-commerce/assets/faq-thumbs/`), where DocumentThumbnails reads
them.

Pipeline: read the register's URLs from an instance (WP-CLI, the plugin's own
DocumentLibrary) -> HEAD each URL for its size -> download into a cache ->
`pdftoppm` page 1 -> shrink to 3x the display box and encode WebP -> write
`<sha1 of the URL path>.webp` plus `manifest.json` (URL path -> file, width,
height). A document over the per-file cap, or one whose download or render
fails, gets no entry: the row falls back to its type tile, which is what the
design shows for a document without a thumbnail.

Usage:
  # The instance whose register the thumbnails cover (uploads = the live files).
  python3 tools/faq/thumbs.py --wp 'just wp a176' --base http://127.0.0.1:9018

  # Which files the run would touch, and what they weigh; no downloads.
  python3 tools/faq/thumbs.py --wp 'just wp a176' --probe-only

  # Write into the plugin's asset directory (the default target).
  python3 tools/faq/thumbs.py --wp 'just wp a176' --out plugins/linker-commerce/assets/faq-thumbs

The cache (`--cache`, default ~/.cache/de-linker-faq-thumbs) keeps the PDFs, so
a second run resumes instead of re-downloading. Rendering needs `pdftoppm`
(poppler) and ImageMagick's `magick`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wpcli import wp_eval  # noqa: E402

# 3x the 52x72 CSS box the row draws (prototype: variant 5's document rows).
HEIGHT = 216
QUALITY = 80
BUDGET = 500 * 1024 * 1024
WORKERS = 4
HEAD_TIMEOUT = 25
DOWNLOAD_TIMEOUT = 120
RENDER_TIMEOUT = 120
USER_AGENT = "de-linker-faq-thumbs/1.0"


def key(url: str) -> str:
    """The manifest key of a document: its URL path.

    Not the whole URL: the same file is served by the live host and by a local
    instance, and a thumbnail belongs to the file, not to the host that served
    it.
    """
    path = urlsplit(url).path
    return path if path else url


def file_name(url: str) -> str:
    return hashlib.sha1(key(url).encode("utf-8")).hexdigest() + ".webp"


def pdf_name(url: str) -> str:
    return hashlib.sha1(key(url).encode("utf-8")).hexdigest() + ".pdf"


def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, text=True, capture_output=True, timeout=timeout, check=False
    )


def select(
    urls: list[str], probes: dict[str, dict[str, Any]], cap: int
) -> tuple[set[str], list[str]]:
    """The cap's decision: the URLs it defers, and the ones to download.

    A file is deferred when the cap is set and the HEAD's Content-Length is
    strictly over it; a URL whose HEAD was not a 200 is never downloaded (the
    file is not there to render). The order of `urls` is kept, so a run's
    output reads the same on a second pass.
    """
    deferred = {
        url
        for url in urls
        if cap
        and isinstance(probes[url].get("length"), int)
        and int(probes[url]["length"]) > cap
    }
    targets = [url for url in urls if url not in deferred and probes[url]["ok"]]
    return deferred, targets


def last_line(text: str | None) -> str:
    """The last non-empty line of a command's output, for a failure's reason."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return lines[-1] if lines else ""


def register_urls(wp: str) -> list[dict[str, str]]:
    """The register's documents from the instance: url and type."""
    payload = wp_eval(wp, {"action": "documents"})
    documents = payload.get("documents")
    if not isinstance(documents, list):
        sys.exit("thumbs: the instance did not return a documents list")
    rows: list[dict[str, str]] = []
    for entry in documents:
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("url"), str)
            and entry["url"]
        ):
            rows.append({"url": entry["url"], "type": str(entry.get("type") or "")})
    return rows


def probe(url: str) -> dict[str, Any]:
    proc = run(
        [
            "curl",
            "-sI",
            "-L",
            "--max-redirs",
            "5",
            "--connect-timeout",
            "12",
            "--max-time",
            str(HEAD_TIMEOUT),
            "-A",
            USER_AGENT,
            "-w",
            "\n__META__ %{http_code}",
            url,
        ],
        HEAD_TIMEOUT + 5,
    )
    text = proc.stdout or ""
    code = 0
    length: int | None = None
    if "__META__" in text:
        head, _, meta = text.rpartition("__META__")
        parts = meta.split()
        if parts and parts[0].isdigit():
            code = int(parts[0])
        text = head
    for line in text.splitlines():
        if line.lower().startswith("content-length:"):
            raw = line.split(":", 1)[1].strip()
            if raw.isdigit():
                length = int(raw)
    error = (
        ""
        if code == 200
        else f"HTTP {code}"
        if code
        else (proc.stderr or "").strip()[:200]
    )
    return {"url": url, "ok": code == 200, "length": length, "error": error}


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-" and path.stat().st_size > 64
    except OSError:
        return False


def download(url: str, dest: Path) -> tuple[bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if is_pdf(dest):
        return True, "cached"
    part = dest.with_suffix(".part")
    part.unlink(missing_ok=True)
    proc = run(
        [
            "curl",
            "-fsSL",
            "--retry",
            "2",
            "--retry-delay",
            "1",
            "--connect-timeout",
            "15",
            "--max-time",
            str(DOWNLOAD_TIMEOUT),
            "-A",
            USER_AGENT,
            "-o",
            str(part),
            url,
        ],
        DOWNLOAD_TIMEOUT + 15,
    )
    if proc.returncode != 0 or not part.exists():
        part.unlink(missing_ok=True)
        return False, last_line(proc.stderr) or f"curl exit {proc.returncode}"
    if not is_pdf(part):
        part.unlink(missing_ok=True)
        return False, "response was not a PDF"
    part.replace(dest)
    return True, "downloaded"


def webp_size(path: Path) -> tuple[int, int]:
    """A WebP's width and height, from its RIFF header."""
    data = path.read_bytes()[:64]
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ValueError("not a webp")
    if data[12:16] == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height
    if data[12:16] == b"VP8 ":
        # Lossy: 3-byte width and height after the start code, 14 bits each.
        return (
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )
    raise ValueError("unsupported webp variant")


def render(
    pdf: Path, png: Path, webp: Path
) -> tuple[bool, str, tuple[int, int] | None]:
    if webp.exists() and webp.stat().st_size > 64:
        try:
            return True, "cached", webp_size(webp)
        except ValueError:
            webp.unlink()
    png.unlink(missing_ok=True)
    proc = run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-l",
            "1",
            "-png",
            "-singlefile",
            str(pdf),
            str(png.with_suffix("")),
        ],
        RENDER_TIMEOUT,
    )
    if proc.returncode != 0 or not png.exists():
        return False, last_line(proc.stderr or proc.stdout) or "pdftoppm failed", None
    webp.parent.mkdir(parents=True, exist_ok=True)
    proc = run(
        [
            "magick",
            str(png),
            "-resize",
            f"x{HEIGHT}",
            "-quality",
            str(QUALITY),
            str(webp),
        ],
        RENDER_TIMEOUT,
    )
    png.unlink(missing_ok=True)
    if proc.returncode != 0 or not webp.exists():
        webp.unlink(missing_ok=True)
        return False, "magick failed to encode the page", None
    try:
        return True, "rendered", webp_size(webp)
    except ValueError as exc:
        webp.unlink(missing_ok=True)
        return False, str(exc), None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the register's page-1 thumbnails."
    )
    parser.add_argument(
        "--wp",
        required=True,
        help="WP-CLI invocation of the instance, e.g. 'just wp a176'",
    )
    parser.add_argument(
        "--base",
        default="",
        help="Base URL to download from; the instance's own default",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("plugins/linker-commerce/assets/faq-thumbs")
    )
    parser.add_argument(
        "--cache", type=Path, default=Path.home() / ".cache" / "de-linker-faq-thumbs"
    )
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=15.0,
        help="Skip PDFs over this size (0 = no cap)",
    )
    parser.add_argument(
        "--probe-only", action="store_true", help="Report sizes; download nothing"
    )
    args = parser.parse_args()

    documents = register_urls(args.wp)
    # One entry per file: the register lists a file once, and the two pages
    # (EN/DE) share it.
    by_url = {row["url"]: row for row in documents}
    print(f"register: {len(documents)} rows, {len(by_url)} URLs", flush=True)

    urls = sorted(by_url)
    cap = int(args.max_file_mb * 1024 * 1024) if args.max_file_mb > 0 else 0
    print(f"probing {len(urls)} URLs ({WORKERS}-way)…", flush=True)
    probes: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        probes_started = {pool.submit(probe, url): url for url in urls}
        for done, probe_future in enumerate(as_completed(probes_started), start=1):
            url = probes_started[probe_future]
            try:
                probes[url] = probe_future.result()
            except Exception as exc:  # noqa: BLE001 — one bad HEAD must not abort the probe
                probes[url] = {
                    "url": url,
                    "ok": False,
                    "length": None,
                    "error": str(exc),
                }
            if done % 25 == 0 or done == len(urls):
                print(f"  probed {done}/{len(urls)}", flush=True)

    known = sum(
        int(p["length"]) for p in probes.values() if isinstance(p.get("length"), int)
    )
    bad = [url for url, p in probes.items() if not p["ok"]]
    deferred, targets = select(urls, probes, cap)
    print(
        f"known size {known / 1024 / 1024:.1f} MB; HEAD not 200: {len(bad)}; "
        f"over {args.max_file_mb:g} MB: {len(deferred)}",
        flush=True,
    )
    for url in bad[:10]:
        print(f"  HEAD fail  {probes[url]['error']}  {url}", flush=True)
    for url in sorted(deferred):
        print(
            f"  skip (over cap)  {int(probes[url]['length']) / 1024 / 1024:.1f} MB  {url}",
            flush=True,
        )
    if args.probe_only:
        return 0

    args.cache.mkdir(parents=True, exist_ok=True)
    print(f"downloading into {args.cache} ({WORKERS}-way, skip cached)…", flush=True)
    downloaded: dict[str, tuple[bool, str]] = {}
    fetched = 0
    lock = threading.Lock()

    def fetch(url: str) -> tuple[str, bool, str]:
        nonlocal fetched
        ok, reason = download(url, args.cache / pdf_name(url))
        if ok and reason == "downloaded":
            with lock:
                fetched += 1
        return url, ok, reason

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        downloads = [pool.submit(fetch, url) for url in targets]
        for done, download_future in enumerate(as_completed(downloads), start=1):
            url, ok, reason = download_future.result()
            downloaded[url] = (ok, reason)
            if done % 10 == 0 or done == len(targets) or not ok:
                size = args.cache / pdf_name(url)
                print(
                    f"  [{done}/{len(targets)}] {'ok' if ok else 'FAIL'} {reason} {size.stat().st_size if ok else 0}  {url.split('/')[-1]}",
                    flush=True,
                )

    print("rendering page 1 and encoding…", flush=True)
    args.out.mkdir(parents=True, exist_ok=True)
    scratch = args.cache / "page"
    manifest: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    for index, url in enumerate(urls, start=1):
        if url in deferred:
            continue
        if not downloaded.get(url, (False, "not downloaded"))[0]:
            reason = downloaded.get(url, (False, "not downloaded"))[1]
            failures.append({"url": url, "reason": reason})
            print(
                f"  [{index}/{len(urls)}] FAIL {reason}  {url.split('/')[-1]}",
                flush=True,
            )
            continue
        try:
            rendered, why, size = render(
                args.cache / pdf_name(url),
                scratch.with_name(f"{file_name(url)}.png"),
                args.out / file_name(url),
            )
        except subprocess.TimeoutExpired:
            rendered, why, size = False, f"timed out after {RENDER_TIMEOUT}s", None
        except Exception as exc:  # noqa: BLE001 — one bad PDF must not abort the build
            rendered, why, size = False, str(exc), None
        if not rendered or size is None:
            failures.append({"url": url, "reason": why})
            print(
                f"  [{index}/{len(urls)}] FAIL {why}  {url.split('/')[-1]}", flush=True
            )
            continue
        manifest[key(url)] = {
            "file": file_name(url),
            "width": size[0],
            "height": size[1],
        }
        if index % 20 == 0 or index == len(urls) or why != "cached":
            print(
                f"  [{index}/{len(urls)}] {why} {size[0]}x{size[1]}  {url.split('/')[-1]}",
                flush=True,
            )

    # Only files the manifest names stay; the target is a published asset.
    keep = {entry["file"] for entry in manifest.values()}
    for path in args.out.glob("*.webp"):
        if path.name not in keep:
            path.unlink()
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    bytes_out = sum(
        (args.out / name).stat().st_size for name in keep if (args.out / name).exists()
    )
    print(
        f"thumbnails: {len(manifest)}/{len(by_url)} files, {bytes_out / 1024:.0f} KB -> {manifest_path}",
        flush=True,
    )
    print(f"skipped over the cap: {len(deferred)}; failed: {len(failures)}", flush=True)
    for failure in failures:
        print(f"  {failure['reason']}  {failure['url']}", flush=True)
    if fetched:
        print(f"downloaded this run: {fetched} files", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130) from None
