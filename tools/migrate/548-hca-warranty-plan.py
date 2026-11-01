#!/usr/bin/env python3
"""Prepare a read-only, auditable HCA warranty migration from a Woo snapshot.

No production writes are performed. The host URL and media ID remain explicit
placeholders until the exact SHA-verified PDF is uploaded through the normal
WordPress media flow and independently read back in the approved Woo window.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "local/src"))
from linker_local.processes import (  # type: ignore[import-not-found]  # noqa: E402
    without_research_credentials,
)

SOURCE_SHA256 = "88a8a5bd9e70bc398fe990069272526c660c1731103ff113e53f93f7fd789307"
SNAPSHOT_SHA256 = "30b40404d4f488679820db519a5c92d309d88d3f064e16336b4df1d10a37bcd2"
SOURCE_URL = "https://en.goodwe.com/Public/Uploads/uploadfile/files/20261014/GOODWELimitedWarrantyforEVChargerforEURev_1_220260917.pdf"
OLD_URL = "https://de-linker.com/wp-content/uploads/2026/10/GW_Limited-Warranty_EV-Charger_Europe.pdf"
OLD_MEDIA_ID = 6426
HOSTED_URL_PENDING = "<hosted-url-after-verified-media-upload>"
MEDIA_ID_PENDING = "<attachment-id-after-verified-media-upload>"
PRODUCTS = {3557: 6689, 3586: 6663, 3587: 6662}


def digest(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def _row_once(
    rows: Any, predicate: Any, description: str
) -> tuple[int, dict[str, Any]]:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"{description} is not a list of document rows")
    matches = [(i, row) for i, row in enumerate(rows) if predicate(row)]
    if len(matches) != 1:
        raise ValueError(
            f"{description}: expected exactly one old policy, found {len(matches)}"
        )
    return matches[0]


def prepare(snapshot: dict[str, Any], source: Path) -> dict[str, Any]:
    """Check all six live product records; produce symbolic, non-writable changes."""
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError(
            "the proposed source PDF bytes do not match the reviewed original"
        )
    if snapshot.get("site") != "https://de-linker.com/":
        raise ValueError("unexpected source site")
    products = snapshot.get("products")
    if not isinstance(products, dict) or set(products) != {
        str(p) for pair in PRODUCTS.items() for p in pair
    }:
        raise ValueError("snapshot does not contain exactly the three EN/DE pairs")
    media = snapshot.get("media", {})
    if media.get(str(OLD_MEDIA_ID), {}).get("url") != OLD_URL:
        raise ValueError("old attachment identity changed")
    changes: list[dict[str, Any]] = []
    for en_id, de_id in PRODUCTS.items():
        en = products[str(en_id)]
        de = products[str(de_id)]
        for row, lang, pid in ((en, "en", en_id), (de, "de", de_id)):
            fields = row.get("woo_fields", {})
            if (
                fields.get("canonical_id") != en_id
                or fields.get("product_id") != pid
                or fields.get("actual_language") != lang
                or fields.get("translation_en") != en_id
                or fields.get("translation_de") != de_id
                or fields.get("status") != "publish"
            ):
                raise ValueError(f"product {pid} status or language pairing changed")
        meta = en.get("metadata", {})
        if meta.get("_linker_documents_managed") != ["1"]:
            raise ValueError(f"product {en_id}: document authority changed")
        docs = en.get("documents_decoded")
        idx, old = _row_once(
            docs, lambda row: row.get("url") == OLD_URL, f"product {en_id} documents"
        )
        if old.get("type") != "warranty":
            raise ValueError(f"product {en_id}: original policy role changed")
        after = copy.deepcopy(docs)
        after[idx]["url"] = HOSTED_URL_PENDING
        after[idx]["title"] = (
            "GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)"
        )
        changes.append(
            {
                "product_id": en_id,
                "locale_consumers": ["en", "de"],
                "meta_key": "_linker_documents",
                "storage": "native_array",
                "before_sha256": digest(docs),
                "before": docs,
                "after": after,
            }
        )
        for key, locale in (
            ("_tv_legacy_acf_json", "en"),
            ("_linker_de_acf_json", "de"),
        ):
            values = meta.get(key)
            if (
                not isinstance(values, list)
                or len(values) != 1
                or not isinstance(values[0], str)
            ):
                raise ValueError(f"product {en_id}: {key} is missing or ambiguous")
            obj = json.loads(values[0])
            if not isinstance(obj, dict):
                raise ValueError(f"product {en_id}: {key} is not an object")
            rows = obj.get("downloads")
            index, row = _row_once(
                rows,
                lambda item: item.get("download_file") == OLD_MEDIA_ID,
                f"product {en_id} {key}",
            )
            if row.get("download_language") != "EN":
                raise ValueError(f"product {en_id}: policy language changed")
            changed = copy.deepcopy(obj)
            target = changed["downloads"][index]
            target["download_file"] = MEDIA_ID_PENDING
            target["download_type"] = "Warranty" if locale == "en" else "Garantie"
            target["download_role"] = "warranty"
            target["download_title"] = (
                "GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)"
                if locale == "en"
                else "GoodWe Garantie für EV-Ladestationen (Europa, Rev. 1.2, englisches Original)"
            )
            changes.append(
                {
                    "product_id": en_id,
                    "locale_consumers": [locale],
                    "meta_key": key,
                    "storage": "json_string",
                    "before_sha256": hashlib.sha256(values[0].encode()).hexdigest(),
                    "before": obj,
                    "after": changed,
                }
            )
    return {
        "status": "DRY_RUN_NOT_WRITABLE",
        "site": snapshot["site"],
        "snapshot_captured_utc": snapshot["captured_utc"],
        "source": {
            "original_url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "bytes": source.stat().st_size,
            "page_count": 3,
        },
        "pending": {
            "hosted_url": HOSTED_URL_PENDING,
            "attachment_id": MEDIA_ID_PENDING,
        },
        "preserve": {
            "old_attachment_id": OLD_MEDIA_ID,
            "old_url": OLD_URL,
            "other_product_document_rows": True,
            "translation_product_metadata": True,
        },
        "changes": changes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--target", choices=("local", "production"))
    parser.add_argument(
        "--action",
        choices=("preview", "stage", "apply", "inspect", "verify", "rollback"),
    )
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--receipt-sha256")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if hashlib.sha256(args.snapshot.read_bytes()).hexdigest() != SNAPSHOT_SHA256:
        parser.error("the reviewed Woo snapshot bytes differ")
    plan = prepare(json.loads(args.snapshot.read_text(encoding="utf-8")), args.source)
    if args.out is not None:
        if args.action or args.target or args.receipt or args.write:
            parser.error("--out is only for the read-only plan")
        args.out.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"{plan['status']}: {len(plan['changes'])} reviewed fields")
        return
    if not args.action or not args.target or not args.receipt:
        parser.error("--action, --target and --receipt are required")
    if args.action in {"stage", "apply", "rollback"} and not args.write:
        parser.error("stage, apply and rollback require --write")
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    reviewed = {}
    for en, de in PRODUCTS.items():
        row = snapshot["products"][str(en)]
        reviewed[str(en)] = {
            "de": de,
            "documents": row["documents_decoded"],
            "acf_en": row["metadata"]["_tv_legacy_acf_json"][0],
            "acf_de": row["metadata"]["_linker_de_acf_json"][0],
            "sku": row["woo_fields"]["sku"],
        }
    receipt = None
    if args.action == "preview":
        if args.receipt.exists() or args.receipt.is_symlink():
            raise ValueError("receipt already exists; preserve the original")
    else:
        if (
            args.receipt.is_symlink()
            or not args.receipt.is_file()
            or stat.S_IMODE(args.receipt.stat().st_mode) & 0o077
        ):
            raise ValueError("receipt must be an existing private file")
        receipt_bytes = args.receipt.read_bytes()
        if args.target == "production" and (
            not args.receipt_sha256
            or len(args.receipt_sha256) != 64
            or any(c not in "0123456789abcdef" for c in args.receipt_sha256)
            or hashlib.sha256(receipt_bytes).hexdigest() != args.receipt_sha256
        ):
            raise ValueError(
                "production receipt SHA-256 must match the reviewed receipt"
            )
        receipt = json.loads(receipt_bytes)
        if (
            receipt.get("reviewed") != reviewed
            or receipt.get("scope") != "hca-warranty-rev12-v1"
        ):
            raise ValueError("receipt and reviewed snapshot differ")
    request = {
        "action": args.action,
        "target": args.target,
        "reviewed": reviewed,
        "receipt": receipt,
    }
    if args.action == "stage":
        request["pdf"] = base64.b64encode(args.source.read_bytes()).decode()
    payload = base64.b64encode(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    source = Path(__file__).with_name("548-hca-warranty.php").read_text()
    marker = "'548-hca-warranty-payload'"
    if source.count(marker) != 1:
        raise ValueError("PHP payload marker differs")
    program = source.replace(marker, repr(payload))
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
        run = subprocess.run(
            cmd,
            input=program,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=without_research_credentials(),
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(
            "transport outcome unknown; keep the receipt and inspect before retry"
        ) from error
    lines = [
        line.removeprefix("@@548-hca-warranty@@")
        for line in run.stdout.splitlines()
        if line.startswith("@@548-hca-warranty@@")
    ]
    if run.returncode or len(lines) != 1:
        raise ValueError((run.stderr.strip() or "no unique migration response")[:1000])
    result = json.loads(lines[0])
    if args.action == "preview":
        if (
            result.get("reviewed") != reviewed
            or result.get("scope") != "hca-warranty-rev12-v1"
        ):
            raise ValueError("invalid preview receipt")
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(result, out, ensure_ascii=False, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in (
                    "action",
                    "state",
                    "attachment_id",
                    "url",
                    "states",
                    "title_change",
                )
                if k in result
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2) from error
