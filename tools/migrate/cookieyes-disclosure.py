#!/usr/bin/env python3
"""Remove CookieYes categories the privacy policy does not disclose.

CookieYes 3.5.7 prints every stored category into ``_ckyConfig``, including a
category whose visibility is 0. Accept all then records consent for that slug
and maps it into the WP Consent API. On the 2026-10-29 production snapshot,
Functional and Performance have no cookies, are already hidden from the banner
HTML, and are not described in Privacy section 3. This script deletes exactly
those two rows. It does not edit privacy pages, banner copy, or the disclosed
categories (necessary, analytics, advertisement).

A page of categories is

  apply  both hidden empty rows are present and match the known labels
  done   both rows are already absent and the three disclosed categories remain
  drift  anything else: nothing is written until a person has looked

``--write`` requires ``--backup-dir``. A non-loopback site also requires
``--full-backup``, the same completed production snapshot gate as
repair-legal-script.py. This lane does not write production.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
PHP = HERE / "cookieyes-disclosure.php"
PLACEHOLDER = "__LINKER_COOKIEYES_DISCLOSURE_PAYLOAD__"
MARKER = "@@cookieyes-disclosure@@"
DISCLOSED = ("necessary", "analytics", "advertisement")
UNDISCLOSED = ("functional", "performance")
EXPECTED_LABELS = {
    "functional": {"en": "Functional", "de": "Funktionale"},
    "performance": {"en": "Performance", "de": "Leistungs"},
}
CONFIG = re.compile(r"var _ckyConfig\s*=\s*(\{.*?\});", re.S)
TEMPLATE = re.compile(
    r'<script id="ckyBannerTemplate" type="text/template">(.*?)</script>', re.S
)
TITLE = re.compile(r'data-cky-tag="detail-category-title"[^>]*>([^<]*)<')


def classify(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Decide apply, done, or drift from one read. Does not contact WordPress."""
    categories = snapshot.get("categories")
    cookies = snapshot.get("cookies")
    if not isinstance(categories, list) or not isinstance(cookies, list):
        raise ValueError("CookieYes read is missing categories or cookies")
    by_slug = {}
    for row in categories:
        if not isinstance(row, dict) or not isinstance(row.get("slug"), str):
            raise ValueError("A category row has no slug")
        if row["slug"] in by_slug:
            raise ValueError(f"duplicate category slug: {row['slug']}")
        by_slug[row["slug"]] = row
    slugs = tuple(by_slug)
    disclosed = [by_slug[slug] for slug in DISCLOSED if slug in by_slug]
    if tuple(row["slug"] for row in disclosed) != DISCLOSED:
        return _drift("disclosed categories are missing or reordered")
    extra = [
        slug for slug in slugs if slug not in DISCLOSED and slug not in UNDISCLOSED
    ]
    if extra:
        return _drift("unexpected category slugs: " + ", ".join(extra))
    present = [slug for slug in UNDISCLOSED if slug in by_slug]
    if not present:
        return {
            "status": "done",
            "remove": [],
            "reason": "undisclosed categories are already absent",
        }
    if present != list(UNDISCLOSED):
        return _drift("only part of the undisclosed pair is present")
    remove = []
    for slug in UNDISCLOSED:
        row = by_slug[slug]
        reason = _row_drift(row, cookies)
        if reason:
            return _drift(reason)
        remove.append(row)
    return {
        "status": "apply",
        "remove": remove,
        "reason": "hidden empty categories are still published to the consent config",
    }


def _row_drift(row: dict[str, Any], cookies: list[Any]) -> str | None:
    slug = str(row["slug"])
    if row.get("labels") != EXPECTED_LABELS[slug]:
        return f"{slug} labels differ from the proven rows"
    if row.get("visibility") != 0:
        return f"{slug} is visible; removing it would change the banner"
    if row.get("prior_consent") != 0:
        return f"{slug} is granted before a choice"
    category_id = row.get("category_id")
    if not isinstance(category_id, int):
        return f"{slug} has no category id"
    owned = [
        cookie
        for cookie in cookies
        if isinstance(cookie, dict) and cookie.get("category") == category_id
    ]
    if owned:
        return f"{slug} has cookies"
    return None


def _drift(reason: str) -> dict[str, Any]:
    return {"status": "drift", "remove": [], "reason": reason}


def rendered_categories(html: str) -> list[str]:
    """Category slugs CookieYes publishes in the page, in config order."""
    match = CONFIG.search(html)
    if match is None:
        raise ValueError("page has no CookieYes config")
    config = json.loads(match.group(1))
    categories = config.get("_categories")
    if not isinstance(categories, list):
        raise ValueError("CookieYes config has no categories")
    return [str(item["slug"]) for item in categories if isinstance(item, dict)]


def rendered_titles(html: str) -> list[str]:
    """Visible preference-center titles. Hidden categories must stay absent."""
    match = TEMPLATE.search(html)
    if match is None:
        raise ValueError("page has no CookieYes banner template")
    return TITLE.findall(match.group(1))


def is_loopback(url: str) -> bool:
    return (urlsplit(url).hostname or "").lower() in {"127.0.0.1", "localhost", "::1"}


def is_production(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return host == "de-linker.com" or host.endswith(".de-linker.com")


def marked_json(stdout: str) -> dict[str, Any]:
    for line in stdout.splitlines():
        index = line.find(MARKER)
        if index < 0:
            continue
        parsed = json.loads(line[index + len(MARKER) :])
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("CookieYes read did not print a snapshot")


def invoke(wp: list[str], payload: dict[str, Any]) -> dict[str, Any]:
    source = PHP.read_text()
    if source.count(PLACEHOLDER) != 1:
        raise RuntimeError("cookieyes-disclosure.php must contain its placeholder once")
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    completed = subprocess.run(
        [
            *wp,
            "eval",
            source.removeprefix("<?php").replace(PLACEHOLDER, encoded),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stderr.write(completed.stderr)
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout)
        raise RuntimeError(
            completed.stderr.strip() or "CookieYes disclosure command failed"
        )
    return marked_json(completed.stdout)


def unchanged(before: dict[str, Any], after: dict[str, Any]) -> None:
    """The migration may delete only the planned category rows."""
    if before.get("privacy") != after.get("privacy"):
        raise RuntimeError("Privacy pages changed; refusing the result")
    if before.get("banner_contents") != after.get("banner_contents"):
        raise RuntimeError("Banner copy changed; refusing the result")
    if before.get("cookies") != after.get("cookies"):
        raise RuntimeError("Cookie rows changed; refusing the result")


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "cookieyes-disclosure"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned {response.status}")
        body = response.read()
        if not isinstance(body, bytes):
            raise RuntimeError(f"{url} did not return bytes")
        return body.decode("utf-8", "replace")


def check_rendered(home: str) -> None:
    """Loopback pages must publish only the three disclosed categories."""
    if not is_loopback(home):
        return
    root = home.rstrip("/")
    expected = {
        "/": ["Essential", "Website analytics", "Visit source"],
        "/de/": ["Notwendig", "Website-Analyse", "Besuchsquelle"],
    }
    for path, titles in expected.items():
        html = fetch(root + path)
        slugs = rendered_categories(html)
        if slugs != list(DISCLOSED):
            raise RuntimeError(
                f"{path} publishes {slugs}, not the disclosed categories"
            )
        if rendered_titles(html) != titles:
            raise RuntimeError(f"{path} banner titles changed")
        for hidden in ("Functional", "Performance", "Funktionale", "Leistungs"):
            if hidden in rendered_titles(html):
                raise RuntimeError(f"{path} still shows {hidden}")


def backup_path(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return directory / f"cookieyes-disclosure-before-{stamp}.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="WP-CLI prefix, without eval")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--rollback", type=Path, help="restore rows from this backup")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument(
        "--full-backup",
        type=Path,
        help="completed production snapshot; required before a non-loopback write",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="allow a non-loopback write after --full-backup; this lane does not set it",
    )
    args = parser.parse_args(argv)
    if args.write and args.rollback:
        parser.error("choose either --write or --rollback")
    if args.write and args.backup_dir is None:
        parser.error("--write needs --backup-dir")
    if args.rollback and not args.rollback.is_file():
        parser.error("--rollback file does not exist")

    wp = shlex.split(args.wp)
    if args.rollback:
        saved = json.loads(args.rollback.read_text())
        rows = saved.get("remove")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("rollback backup has no category rows")
        after = invoke(wp, {"operation": "rollback", "rows": rows})
        print(json.dumps({"rollback": True, "categories": _slugs(after)}, indent=2))
        return 0

    before = invoke(wp, {"operation": "read"})
    decision = classify(before)
    home = str(before.get("home") or "")
    if args.write and not is_loopback(home):
        if not args.production:
            raise RuntimeError(
                "refusing to write a non-loopback site without --production"
            )
        if args.full_backup is None:
            raise RuntimeError("a non-loopback write needs --full-backup")
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "repair", HERE / "repair-legal-script.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("repair-legal-script.py is missing")
        repair = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(repair)
        repair.verify_full_backup(args.full_backup)
    if not args.write or decision["status"] != "apply":
        print(json.dumps({"home": home, **decision, "write": False}, indent=2))
        return 0 if decision["status"] != "drift" else 2

    backup_dir = args.backup_dir
    if backup_dir is None:
        raise RuntimeError("--write needs --backup-dir")
    path = backup_path(backup_dir)
    path.write_text(
        json.dumps({"snapshot": before, "remove": decision["remove"]}, indent=2) + "\n"
    )
    path.chmod(0o600)
    print(f"Backup: {path}")
    after = invoke(wp, {"operation": "apply", "rows": decision["remove"]})
    unchanged(before, after)
    readback = classify(after)
    if readback["status"] != "done":
        raise RuntimeError(
            f"readback is {readback['status']}: {readback['reason']}; backup: {path}"
        )
    check_rendered(home)
    print(
        json.dumps(
            {
                "write": True,
                "status": "done",
                "backup": str(path),
                "privacy": after.get("privacy"),
                "categories": _slugs(after),
            },
            indent=2,
        )
    )
    return 0


def _slugs(snapshot: dict[str, Any]) -> list[str]:
    categories = snapshot.get("categories")
    if not isinstance(categories, list):
        return []
    return [str(row.get("slug")) for row in categories if isinstance(row, dict)]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
