#!/usr/bin/env python3
"""Preview or apply the receipt-backed HS3 document title correction.

Preview is read-only and writes one private receipt. Production apply/rollback
requires the reviewed receipt's SHA-256 and the normal full backup first. A
partial or interrupted operation must be inspected with the same receipt.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/local/src"))
from linker_local.processes import (  # type: ignore[import-not-found]  # noqa: E402
    without_research_credentials,
)

PHP = Path(__file__).with_suffix(".php")
MARKER = "@@548-hs3-titles@@"
PAYLOAD = "'548-hs3-titles-payload'"
PRODUCTS = {
    "1185": (6833, 12, "DLK-SAJ-HS312KT2WP"),
    "1186": (6832, 6, "DLK-SAJ-HS36KT2WP"),
    "1187": (6831, 8, "DLK-SAJ-HS38KT2WP"),
    "2198": (6730, 5, "DLK-SAJ-HS35KT2WP"),
    "2199": (6729, 10, "DLK-SAJ-HS310KT2WP"),
}
DOCUMENTS = (
    {
        "id": "doc-77669d4a1e6c821e1f1909c3b2309da96f0241565072952e68d6ec5499797411",
        "sha": "43d6efd869b4c66f485eb40f602e369d95a47665f33fb6330607a99884012479",
        "url": "https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_BU3_BC3-TV_EU-Declaration-of-Conformity_V2.pdf",
        "type": "certificate",
        "lang": "EN/DE",
        "role": "certificate",
        "title": "SAJ HS3, BU3 and BC3-TV EU Declaration of Conformity (Multilingual)",
        "de": "SAJ HS3, BU3 und BC3-TV EU-Konformitätserklärung (mehrsprachig)",
    },
    {
        "id": "doc-784554fad43dd1b2f49c5dc618cbe1c22a7afcb7e3451c29efe50aecbd6d4638",
        "sha": "e00f9645d187c241570a4037afa6a1dd54c23cd3d41b189bc44a0e0b24e4f7b3",
        "url": "https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_5-12K-T2_Datasheet_DE.pdf",
        "type": "datasheet",
        "lang": "DE",
        "role": "datasheet",
        "title": "SAJ HS3 5–12K-T2 Three-Phase Datasheet (German)",
        "de": "SAJ HS3 5–12K-T2 Datenblatt für das dreiphasige System (Deutsch)",
    },
)


def old_title(doc: dict[str, str], kw: int) -> str:
    model = f"HS3-{kw}K-T2-W/G-PX"
    if doc["type"] == "certificate":
        return f"EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the {model})"
    return f"SAJ HS3 5-12K three-phase datasheet, German (covers the {model})"


def expected_rows(before: Any, kw: int) -> list[Any]:
    if not isinstance(before, list):
        raise ValueError("Document preimage is not a list.")
    after = copy.deepcopy(before)
    for doc in DOCUMENTS:
        matches = [
            row
            for row in after
            if isinstance(row, dict) and row.get("url") == doc["url"]
        ]
        if len(matches) != 1:
            raise ValueError("Each reviewed PDF must have exactly one row.")
        row = matches[0]
        if any(
            row.get(key) != doc[key] for key in ("url", "type", "lang", "role")
        ) or row.get("title") != old_title(doc, kw):
            raise ValueError("Original document title, language or role differs.")
        row["title"] = doc["title"]
    return after


def validate_receipt(receipt: Any, target: str) -> None:
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != 1
        or receipt.get("scope") != "hs3-document-titles-v1"
        or receipt.get("action") != "preview"
        or receipt.get("site")
        != {"production": "https://de-linker.com", "local": "http://127.0.0.1:9347"}[
            target
        ]
    ):
        raise ValueError("Receipt identity or target site differs.")
    products = receipt.get("products")
    if not isinstance(products, dict) or list(products) != list(PRODUCTS):
        raise ValueError("Receipt must contain the five reviewed product pairs.")
    for pid, (de, kw, sku) in PRODUCTS.items():
        row = products[pid]
        if (
            not isinstance(row, dict)
            or row.get("de") != de
            or row.get("sku") != sku
            or expected_rows(row.get("before"), kw) != row.get("after")
        ):
            raise ValueError(f"Product {pid} receipt changes unrelated data.")
    if receipt.get("title_changes") != [
        {"document_id": d["id"], "en": d["title"], "de": d["de"]} for d in DOCUMENTS
    ]:
        raise ValueError("Receipt's title changes do not match the reviewed wording.")
    option = receipt.get("option")
    if (
        not isinstance(option, dict)
        or type(option.get("id")) is not int
        or option["id"] <= 0
    ):
        raise ValueError("Receipt lacks the exact title-option identity.")
    try:
        for key in ("before_base64", "after_base64"):
            if not base64.b64decode(option[key], validate=True):
                raise ValueError("Empty option preimage.")
    except (KeyError, TypeError) as exc:
        raise ValueError("Invalid title-option preimage.") from exc
    if not isinstance(receipt.get("relations"), dict) or not isinstance(
        receipt.get("authority"), dict
    ):
        raise ValueError("Receipt lacks the native manifest or raw associations.")


def run(args: argparse.Namespace) -> None:
    if args.action in {"apply", "rollback"} and not args.write:
        raise ValueError("Apply and rollback require --write and the normal backup.")
    if args.action not in {"apply", "rollback"} and args.write:
        raise ValueError("--write is only valid for apply or rollback.")
    receipt = None
    if args.action == "preview":
        if args.receipt.exists() or args.receipt.is_symlink():
            raise ValueError("Receipt already exists; preserve it.")
    else:
        if (
            args.receipt.is_symlink()
            or not args.receipt.is_file()
            or stat.S_IMODE(args.receipt.stat().st_mode) & 0o077
        ):
            raise ValueError("Receipt must be an existing private file.")
        raw = args.receipt.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if args.target == "production" and (
            args.receipt_sha256 != digest or len(digest) != 64
        ):
            raise ValueError("Production receipt SHA-256 must match the reviewed file.")
        receipt = json.loads(raw)
        validate_receipt(receipt, args.target)
    request = {"action": args.action, "target": args.target, "receipt": receipt}
    payload = base64.b64encode(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    source = PHP.read_text(encoding="utf-8")
    if source.count(PAYLOAD) != 1:
        raise ValueError("PHP payload marker differs.")
    program = source.replace(PAYLOAD, repr(payload))
    if args.target == "local":
        cmd = [
            "/opt/homebrew/opt/php@8.3/bin/php",
            "-c",
            str(Path.home() / "de-linker-local/p548/php.ini"),
            "/opt/homebrew/bin/wp",
            "--path=" + str(Path.home() / "de-linker-local/p548/wordpress"),
            "eval-file",
            "-",
        ]
    else:
        cmd = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "hostinger-de-linker",
            "/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html eval-file -",
        ]
    try:
        result = subprocess.run(
            cmd,
            input=program,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=without_research_credentials(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            "Transport outcome unknown; keep the receipt and inspect before retry."
        ) from exc
    lines = [
        line.removeprefix(MARKER)
        for line in result.stdout.splitlines()
        if line.startswith(MARKER)
    ]
    if result.returncode or len(lines) != 1:
        raise ValueError(
            (
                result.stderr.strip()
                or "No unique migration response; inspect before retry."
            )[:2000]
        )
    response = json.loads(lines[0])
    if args.action == "preview":
        validate_receipt(response, args.target)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(args.receipt, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(response, out, ensure_ascii=False, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        digest = hashlib.sha256(args.receipt.read_bytes()).hexdigest()
        print(
            json.dumps(
                {
                    "action": "preview",
                    "products": len(PRODUCTS),
                    "title_rows": 10,
                    "source_revision": response["source_revision"],
                    "receipt_sha256": digest,
                },
                ensure_ascii=False,
            )
        )
    else:
        print(json.dumps(response, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--action",
        choices=("preview", "apply", "inspect", "verify", "rollback"),
        required=True,
    )
    parser.add_argument("--target", choices=("local", "production"), required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--write", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error
