#!/usr/bin/env python3
"""Preview, inspect, apply or reverse the CB2 quick-guide title receipt."""

from __future__ import annotations

import argparse
import base64
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
MARKER = "@@548-cb2-guide-titles@@"
PAYLOAD = "'548-cb2-guide-titles-payload'"
MODELS = {"4103": "57.3", "4104": "71.6", "4105": "85.9", "4106": "100.3"}
KEYS = ("_tv_legacy_acf_json", "_linker_de_acf_json", "_linker_de_source_acf_json")
NEW_EN = "SAJ CB2-(57.3K-100.3K)-HV5 quick installation guide (English)"
NEW_DE = (
    "SAJ CB2-(57.3K-100.3K)-HV5 Kurzanleitung zur Installation (englisches Original)"
)


def validate_receipt(receipt: Any, target: str) -> None:
    site = {"production": "https://de-linker.com", "local": "http://127.0.0.1:9347"}[
        target
    ]
    if not isinstance(receipt, dict) or any(
        receipt.get(k) != v
        for k, v in {
            "schema_version": 1,
            "scope": "cb2-guide-titles-v1",
            "action": "preview",
            "site": site,
        }.items()
    ):
        raise ValueError("Receipt scope or target site differs.")
    products = receipt.get("products")
    if not isinstance(products, dict) or list(products) != list(MODELS):
        raise ValueError("Receipt does not contain the four reviewed products.")
    for pid, model in MODELS.items():
        records = products[pid]
        if not isinstance(records, dict) or list(records) != list(KEYS):
            raise ValueError("Product metadata set differs.")
        for key in KEYS:
            row = records[key]
            before, after = row["before"], row["after"]
            if any(
                hashlib.sha256(row[k].encode()).hexdigest() != row[k + "_sha256"]
                for k in ("before", "after")
            ):
                raise ValueError("Receipt metadata hash differs.")
            original, edited = json.loads(before), json.loads(after)
            field = original["downloads"][3]
            old = (
                f"SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-{model}-HV5)"
                if key == "_linker_de_acf_json"
                else f"SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-{model}-HV5)"
            )
            if field.get("download_title") != old or field.get("download_file") != 6337:
                raise ValueError("Reviewed document row differs.")
            field["download_title"] = NEW_DE if key == "_linker_de_acf_json" else NEW_EN
            if original != edited:
                raise ValueError("Receipt changes an unrelated field.")
        if records[KEYS[0]]["before"] != records[KEYS[2]]["before"]:
            raise ValueError("English translation baseline differs.")
    option = receipt["option"]
    if type(option["id"]) is not int or option["id"] <= 0:
        raise ValueError("Receipt lacks the title option identity.")
    for key in ("before", "after"):
        value = base64.b64decode(option[key], validate=True)
        if not value or hashlib.sha256(value).hexdigest() != option[key + "_sha256"]:
            raise ValueError("Title option hash differs.")
    if not isinstance(receipt.get("authority"), dict):
        raise ValueError("Receipt lacks the source authority.")


def run(args: argparse.Namespace) -> None:
    if (args.action in {"apply", "rollback"}) != args.write:
        raise ValueError(
            "Only apply and rollback require --write and the normal backup."
        )
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
        if (
            args.target == "production"
            and args.receipt_sha256 != hashlib.sha256(raw).hexdigest()
        ):
            raise ValueError("Production receipt SHA-256 must match the reviewed file.")
        receipt = json.loads(raw)
        validate_receipt(receipt, args.target)
    payload = base64.b64encode(
        json.dumps(
            {"action": args.action, "target": args.target, "receipt": receipt},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    ).decode()
    source = PHP.read_text(encoding="utf-8")
    if source.count(PAYLOAD) != 1:
        raise ValueError("PHP request marker differs.")
    if args.target == "local":
        command = [
            "/opt/homebrew/opt/php@8.3/bin/php",
            "-c",
            str(Path.home() / "de-linker-local/p548/php.ini"),
            "/opt/homebrew/bin/wp",
            "--path=" + str(Path.home() / "de-linker-local/p548/wordpress"),
            "eval-file",
            "-",
        ]
    else:
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "hostinger-de-linker",
            "/usr/local/bin/wp --path=/home/u388076051/domains/de-linker.com/public_html eval-file -",
        ]
    try:
        result = subprocess.run(
            command,
            input=source.replace(PAYLOAD, repr(payload)),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            env=without_research_credentials(),
        )
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            "Transport outcome unknown; inspect the same receipt before retry."
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
        print(
            json.dumps(
                {
                    "action": "preview",
                    "products": 4,
                    "metadata_rows": 12,
                    "receipt_sha256": hashlib.sha256(
                        args.receipt.read_bytes()
                    ).hexdigest(),
                    "source_revision": response["authority"]["source"],
                }
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
