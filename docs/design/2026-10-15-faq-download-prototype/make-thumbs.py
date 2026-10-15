#!/usr/bin/env python3
"""First-page thumbnails for the FAQ prototype document rows.

Reads documents[].docs[].url from data.en.json and data.de.json, downloads
each PDF into a resumable cache, renders page 1, and writes:

  thumbs/<sha1 of the URL>.png
  thumbs/manifest.json    URL -> {file, width, height}
  thumbs/failures.json    URLs that could not be rendered, with a reason

Usage:
  python3 make-thumbs.py                 # probe, download, render
  python3 make-thumbs.py --probe-only    # size estimate only; no downloads
  python3 make-thumbs.py --max-file-mb 15
      # defer PDFs over 15 MB, then download the rest if it fits in 400 MB

Cache (not in the prototype dir, safe to delete):
  <repo>/.scratch/faq-pdf-cache/

Stops before downloading if the summed Content-Length is over 400MB.
Already-cached PDFs and PNGs are skipped, so a second run resumes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
CACHE = REPO / ".scratch" / "faq-pdf-cache"
THUMBS = ROOT / "thumbs"
BUDGET = 400 * 1024 * 1024
WORKERS = 4
HEAD_TIMEOUT = 25
DOWNLOAD_TIMEOUT = 120
RENDER_TIMEOUT = 60
SCALE_TO = 448


def load_urls() -> dict[str, list[dict[str, str]]]:
    """URL -> [{lang, brand, title, type}, ...] from both catalogues."""
    found: dict[str, list[dict[str, str]]] = defaultdict(list)
    for lang in ("en", "de"):
        data = json.loads((ROOT / f"data.{lang}.json").read_text())
        for block in data.get("documents") or []:
            brand = block.get("brand") or ""
            for doc in block.get("docs") or []:
                url = doc.get("url") or ""
                if not url:
                    continue
                found[url].append(
                    {
                        "lang": lang,
                        "brand": brand,
                        "title": doc.get("title") or "",
                        "type": doc.get("type") or "",
                    }
                )
    return found


def sha_name(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest() + ".png"


def cache_path(url: str) -> Path:
    host = urlsplit(url).netloc.replace(":", "_") or "file"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return CACHE / host / f"{digest}.pdf"


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        sig = handle.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a png")
        handle.read(4)
        if handle.read(4) != b"IHDR":
            raise ValueError("missing IHDR")
        width = int.from_bytes(handle.read(4), "big")
        height = int.from_bytes(handle.read(4), "big")
    if width < 1 or height < 1:
        raise ValueError("empty png")
    return width, height


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-" and path.stat().st_size > 64
    except OSError:
        return False


def curl(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["curl", *args],
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def probe(url: str) -> dict[str, object]:
    proc = curl(
        [
            "-sI",
            "-L",
            "--max-redirs",
            "5",
            "--connect-timeout",
            "12",
            "--max-time",
            str(HEAD_TIMEOUT),
            "-A",
            "de-linker-faq-prototype/1.0",
            "-w",
            "\n__META__ %{http_code} %{size_download}",
            url,
        ],
        HEAD_TIMEOUT + 5,
    )
    text = proc.stdout or ""
    code = 0
    length = None
    if "__META__" in text:
        head, _, meta = text.rpartition("__META__")
        parts = meta.split()
        if parts:
            code = int(parts[0]) if parts[0].isdigit() else 0
        text = head
    for line in text.splitlines():
        if line.lower().startswith("content-length:"):
            raw = line.split(":", 1)[1].strip()
            if raw.isdigit():
                length = int(raw)
    if proc.returncode != 0 and code == 0:
        err = (proc.stderr or "").strip().splitlines()
        return {"url": url, "ok": False, "code": 0, "length": None, "error": err[-1] if err else f"curl {proc.returncode}"}
    return {"url": url, "ok": code == 200, "code": code, "length": length, "error": "" if code == 200 else f"HTTP {code}"}


def download(url: str, dest: Path) -> tuple[bool, str, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if is_pdf(dest):
        return True, "cached", dest.stat().st_size
    part = dest.with_suffix(".part")
    if part.exists():
        part.unlink()
    proc = curl(
        [
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
            "de-linker-faq-prototype/1.0",
            "-o",
            str(part),
            url,
        ],
        DOWNLOAD_TIMEOUT + 15,
    )
    if proc.returncode != 0 or not part.exists():
        if part.exists():
            part.unlink()
        err = (proc.stderr or "").strip().splitlines()
        return False, err[-1] if err else f"curl exit {proc.returncode}", 0
    if not is_pdf(part):
        part.unlink()
        return False, "response was not a PDF", 0
    part.replace(dest)
    return True, "downloaded", dest.stat().st_size


def render(pdf: Path, png: Path) -> tuple[bool, str]:
    if png.exists() and png.stat().st_size > 64:
        try:
            png_size(png)
            return True, "cached"
        except ValueError:
            png.unlink()
    png.parent.mkdir(parents=True, exist_ok=True)
    prefix = png.with_suffix("")
    proc = subprocess.run(
        [
            "pdftoppm",
            "-f",
            "1",
            "-l",
            "1",
            "-png",
            "-scale-to",
            str(SCALE_TO),
            "-singlefile",
            str(pdf),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        timeout=RENDER_TIMEOUT,
        check=False,
    )
    if proc.returncode == 0 and png.exists():
        try:
            png_size(png)
            return True, "rendered"
        except ValueError as exc:
            png.unlink(missing_ok=True)
            return False, f"bad png ({exc})"
    err = (proc.stderr or proc.stdout or "").strip().splitlines()
    reason = err[-1] if err else f"pdftoppm exit {proc.returncode}"
    # qlmanage names the output <basename>.pdf.png beside the source.
    ql_dir = CACHE / "ql"
    ql_dir.mkdir(parents=True, exist_ok=True)
    ql = subprocess.run(
        ["qlmanage", "-t", "-s", str(SCALE_TO), "-o", str(ql_dir), str(pdf)],
        capture_output=True,
        text=True,
        timeout=RENDER_TIMEOUT,
        check=False,
    )
    produced = ql_dir / f"{pdf.name}.png"
    if ql.returncode == 0 and produced.exists() and produced.stat().st_size > 64:
        produced.replace(png)
        try:
            png_size(png)
            return True, "qlmanage"
        except ValueError:
            png.unlink(missing_ok=True)
    ql_err = (ql.stderr or "").strip().splitlines()
    extra = ql_err[-1] if ql_err else "qlmanage produced nothing"
    return False, f"{reason}; {extra}"


def budget_report(urls: dict[str, list[dict[str, str]]], probes: dict[str, dict[str, object]], total: int) -> str:
    """Decision table for a corpus that exceeds the download budget."""
    rows = []
    for url, refs in urls.items():
        length = probes[url].get("length")
        rows.append(
            {
                "url": url,
                "bytes": length if isinstance(length, int) else 0,
                "brand": refs[0]["brand"],
                "type": refs[0]["type"],
                "title": refs[0]["title"],
            }
        )
    lines = [
        f"STOP: known Content-Length {total / 1024 / 1024:.1f} MB exceeds the 400 MB budget. No files downloaded.",
        "",
        "Per brand:",
    ]
    by_brand: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_brand[str(row["brand"])].append(row)
    for brand in sorted(by_brand):
        docs = by_brand[brand]
        mb = sum(int(d["bytes"]) for d in docs) / 1024 / 1024
        lines.append(f"  {brand}: {len(docs)} docs, {mb:.1f} MB")
    lines.append("")
    lines.append("Size buckets:")
    edges = [(1, "<1 MB"), (5, "1–5 MB"), (8, "5–8 MB"), (15, "8–15 MB"), (40, "15–40 MB"), (10**6, ">40 MB")]
    prev = 0.0
    for cap, label in edges:
        bucket = [r for r in rows if prev < r["bytes"] / 1024 / 1024 <= cap]
        mb = sum(int(r["bytes"]) for r in bucket) / 1024 / 1024
        lines.append(f"  {label}: {len(bucket)} files, {mb:.1f} MB")
        prev = cap
    lines.append("")
    lines.append("Subset if individual files over a cap are deferred:")
    for cap_mb in (5, 8, 15, 20):
        cap = cap_mb * 1024 * 1024
        kept = [r for r in rows if int(r["bytes"]) <= cap]
        deferred = [r for r in rows if int(r["bytes"]) > cap]
        mb = sum(int(r["bytes"]) for r in kept) / 1024 / 1024
        lines.append(
            f"  skip >{cap_mb} MB: keep {len(kept)}/{len(rows)} ({mb:.1f} MB), defer {len(deferred)}"
        )
        deferred_brands: dict[str, int] = defaultdict(int)
        for row in deferred:
            deferred_brands[str(row["brand"])] += 1
        if deferred_brands:
            detail = ", ".join(f"{brand} {n}" for brand, n in sorted(deferred_brands.items()))
            lines.append(f"    deferred by brand: {detail}")
    lines.append("")
    lines.append("Largest files:")
    for row in sorted(rows, key=lambda item: int(item["bytes"]), reverse=True)[:20]:
        lines.append(
            f"  {int(row['bytes']) / 1024 / 1024:6.1f} MB  {row['brand']:<10} {row['type']:<14} {row['url']}"
        )
    return "\n".join(lines)


def coverage(urls: dict[str, list[dict[str, str]]], ok: set[str]) -> list[str]:
    lines = []
    for lang in ("en", "de"):
        lines.append(f"{lang.upper()} docs with a thumbnail:")
        by_brand: dict[str, list[str]] = defaultdict(list)
        for url, refs in urls.items():
            for ref in refs:
                if ref["lang"] == lang:
                    by_brand[ref["brand"]].append(url)
        total = got = 0
        for brand in sorted(by_brand):
            docs = by_brand[brand]
            hit = sum(1 for url in docs if url in ok)
            total += len(docs)
            got += hit
            lines.append(f"  {brand}: {hit}/{len(docs)}")
        lines.append(f"  total: {got}/{total}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Render page-1 thumbnails for FAQ prototype PDFs.")
    parser.add_argument("--probe-only", action="store_true", help="HEAD the URLs and print the size estimate.")
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=0,
        help="Defer PDFs larger than this many MB (0 = no per-file cap). Deferred files keep the type-tile fallback.",
    )
    args = parser.parse_args()

    urls = load_urls()
    print(f"unique URLs: {len(urls)}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    print(f"probing {len(urls)} URLs ({WORKERS}-way)…", flush=True)
    probes: dict[str, dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(probe, url): url for url in urls}
        done = 0
        for future in as_completed(futures):
            url = futures[future]
            done += 1
            try:
                probes[url] = future.result()
            except Exception as exc:  # noqa: BLE001 — one bad HEAD must not abort the probe
                probes[url] = {"url": url, "ok": False, "code": 0, "length": None, "error": str(exc)}
            if done % 20 == 0 or done == len(urls):
                print(f"  probed {done}/{len(urls)}", flush=True)

    known = [p["length"] for p in probes.values() if isinstance(p.get("length"), int)]
    unknown = [url for url, p in probes.items() if p.get("length") is None and p.get("ok")]
    bad = [url for url, p in probes.items() if not p.get("ok")]
    total = sum(known)
    print(
        f"Content-Length known for {len(known)}/{len(urls)}: {total / 1024 / 1024:.1f} MB; "
        f"unknown length: {len(unknown)}; HEAD not 200: {len(bad)}",
        flush=True,
    )
    if bad:
        for url in bad[:12]:
            refs = urls[url]
            brand = refs[0]["brand"] if refs else "?"
            print(f"  HEAD fail  {brand}  {probes[url].get('error')}  {url}", flush=True)
        if len(bad) > 12:
            print(f"  … {len(bad) - 12} more", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    probe_path = CACHE / "probe.json"
    probe_path.write_text(json.dumps({url: probes[url] for url in urls}, indent=2) + "\n")
    file_cap = int(args.max_file_mb * 1024 * 1024) if args.max_file_mb and args.max_file_mb > 0 else 0
    deferred = {
        url
        for url, info in probes.items()
        if file_cap and isinstance(info.get("length"), int) and int(info["length"]) > file_cap
    }
    if deferred:
        deferred_bytes = sum(int(probes[url]["length"]) for url in deferred)
        print(
            f"deferring {len(deferred)} files over {args.max_file_mb:g} MB ({deferred_bytes / 1024 / 1024:.1f} MB)",
            flush=True,
        )
    eligible_bytes = sum(
        int(info["length"])
        for url, info in probes.items()
        if url not in deferred and isinstance(info.get("length"), int)
    )
    if eligible_bytes > BUDGET or (args.probe_only and total > BUDGET):
        report = budget_report(urls, probes, total)
        if deferred:
            report += (
                f"\n\n--max-file-mb {args.max_file_mb:g} still selects "
                f"{eligible_bytes / 1024 / 1024:.1f} MB"
                + ("." if eligible_bytes <= BUDGET else ", which is still over the 400 MB budget.")
            )
        print(report, flush=True)
        (CACHE / "size-report.txt").write_text(report + "\n")
        if eligible_bytes > BUDGET or args.probe_only:
            print(f"STOP: no files downloaded. Probe saved to {probe_path}", flush=True)
            return 2
    if args.probe_only:
        return 0
    targets = [url for url in urls if url not in deferred]

    print(f"downloading into {CACHE} ({WORKERS}-way, skip cached)…", flush=True)
    downloaded: dict[str, tuple[bool, str, int]] = {}
    byte_lock = threading.Lock()
    running = 0
    over = threading.Event()

    def fetch(url: str) -> tuple[str, bool, str, int]:
        nonlocal running
        if over.is_set() and not is_pdf(cache_path(url)):
            return url, False, "stopped: download budget exceeded", 0
        ok, reason, size = download(url, cache_path(url))
        if ok and reason == "downloaded":
            with byte_lock:
                running += size
                if running > BUDGET:
                    over.set()
        return url, ok, reason, size

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch, url) for url in targets]
        done = 0
        for future in as_completed(futures):
            url, ok, reason, size = future.result()
            downloaded[url] = (ok, reason, size)
            done += 1
            if done % 10 == 0 or done == len(targets) or not ok:
                mark = "ok" if ok else "FAIL"
                print(f"  [{done}/{len(targets)}] {mark} {reason} {size}  {url.split('/')[-1]}", flush=True)

    got_pdf = {url for url, (ok, _, _) in downloaded.items() if ok}
    print(f"PDFs on disk: {len(got_pdf)}/{len(urls)}", flush=True)
    fresh = sum(size for ok, reason, size in downloaded.values() if ok and reason == "downloaded")
    print(f"bytes fetched this run: {fresh / 1024 / 1024:.1f} MB", flush=True)
    if over.is_set():
        print("STOP: this run crossed 400 MB of new downloads. Rendering only what is cached.", flush=True)

    print("rendering page 1…", flush=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, object]] = {}
    failures: list[dict[str, str]] = []
    rendered = 0
    for index, url in enumerate(sorted(urls), start=1):
        name = sha_name(url)
        png = THUMBS / name
        if url in deferred:
            continue
        if url not in got_pdf:
            _, reason, _ = downloaded.get(url, (False, "not downloaded", 0))
            failures.append({"url": url, "reason": reason, "brand": urls[url][0]["brand"]})
            continue
        try:
            ok, reason = render(cache_path(url), png)
        except subprocess.TimeoutExpired:
            ok, reason = False, f"render timed out after {RENDER_TIMEOUT}s"
        except Exception as exc:  # noqa: BLE001
            ok, reason = False, str(exc)
        if not ok:
            failures.append({"url": url, "reason": reason, "brand": urls[url][0]["brand"]})
            print(f"  [{index}/{len(urls)}] FAIL {reason}  {url.split('/')[-1]}", flush=True)
            continue
        width, height = png_size(png)
        manifest[url] = {"file": name, "width": width, "height": height}
        rendered += 1
        if index % 10 == 0 or index == len(urls) or reason != "cached":
            print(f"  [{index}/{len(urls)}] {reason} {width}x{height}  {url.split('/')[-1]}", flush=True)

    (THUMBS / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (THUMBS / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    ok_urls = set(manifest)
    lines = [
        f"rendered: {len(manifest)}/{len(urls)}",
        f"deferred over per-file cap: {len(deferred)}",
        f"failed: {len(failures)}",
        f"png bytes: {sum(p.stat().st_size for p in THUMBS.glob('*.png')) / 1024 / 1024:.1f} MB",
        *coverage(urls, ok_urls),
    ]
    if failures:
        lines.append("failures:")
        for item in failures:
            lines.append(f"  {item['brand']}: {item['reason']} — {item['url']}")
    report = "\n".join(lines)
    print(report, flush=True)
    (CACHE / "report.txt").write_text(report + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
