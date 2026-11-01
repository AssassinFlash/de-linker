#!/usr/bin/env python3
"""Guarded, receipt-backed update of the two maintained cable references.

Preview creates one private recovery receipt. Apply, verify and rollback use
that same receipt and the same reviewed input; no product is created or reset.
Production data writes require the normal full backup first.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/cutover/src"), str(ROOT / "tools/local/src")]

from linker_cutover.target import (  # type: ignore[import-not-found]  # noqa: E402
    Target,
    local_target,
    remote_target,
)

PLAN = ROOT / "plugins/linker-commerce/data/cable-references.json"
PHP = Path(__file__).with_suffix(".php")
MARKER = "@@548-cable-reference-currents@@"
PAYLOAD = "'548-cable-reference-currents-payload'"
REFERENCES = {"nexans-038021106": 8467, "nexans-038023102": 8468}
ORIGINALS = {
    "nexans-038021106": (
        "0fed83cc110b0689361193d2241cccd6a22b4a15fbba4756a1c1cc78aa805ce3",
        (55, 52, 44),
    ),
    "nexans-038023102": (
        "217bfaf2296673fc499a1886fc0a5967bd2d4d1de7071336c04806018abf3d69",
        (70, 67, 57),
    ),
}
LAYINGS = (
    (
        "single-in-air-60c-120c",
        "single_in_air",
        "Permissible current rating in air, 120°C conductor temperature, 60°C ambient – 1 cable",
    ),
    (
        "single-on-surface-60c-120c",
        "single_on_surface",
        "Permissible current rating on surface, 120°C conductor temperature, 60°C ambient – 1 cable",
    ),
    (
        "two-touching-on-surface-60c-120c",
        "two_touching_on_surface",
        "Permissible current rating on surface, 120°C conductor temperature, 60°C ambient – 2 cables touching",
    ),
)


class MigrationError(RuntimeError):
    """The reviewed input or an exact recovery receipt is not safe to use."""


def load_plan() -> tuple[dict[str, Any], str]:
    """Read the one-time reviewed input and pin the exact bytes."""
    raw = PLAN.read_bytes()
    plan = json.loads(raw)
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise MigrationError("Unsupported cable reference input.")
    rows = plan.get("references")
    if not isinstance(rows, list) or len(rows) != 2:
        raise MigrationError("The two reviewed cable references are required.")
    if any(not isinstance(row, dict) for row in rows) or {
        row.get("id") for row in rows
    } != set(REFERENCES):
        raise MigrationError(
            "Cable reference identities differ from the reviewed scope."
        )
    for row in rows:
        facts = row.get("cable_facts")
        ratings = (
            facts.get("reference_current_ratings") if isinstance(facts, dict) else None
        )
        documents = row.get("documents")
        blob, currents = ORIGINALS[row["id"]]
        if (
            row.get("kind") != "cable"
            or not isinstance(documents, list)
            or len(documents) != 1
            or not isinstance(documents[0], dict)
            or documents[0].get("expected_blob_sha256") != blob
            or documents[0].get("url")
            != f"https://de-linker.com/wp-content/uploads/2026/11/{row['id']}.pdf"
            or not isinstance(ratings, list)
            or len(ratings) != 3
        ):
            raise MigrationError(
                "Each reviewed reference needs its three sourced ratings."
            )
        for rating, (identifier, laying, quote), current in zip(
            ratings, LAYINGS, currents, strict=True
        ):
            if not isinstance(rating, dict) or not isinstance(
                rating.get("source"), dict
            ):
                raise MigrationError("Invalid reviewed current row.")
            source = rating["source"]
            if (
                rating.get("id") != identifier
                or rating.get("laying") != laying
                or rating.get("ambient_temperature_c") != 60
                or rating.get("rated_conductor_temperature_c") != 120
                or type(rating.get("current_a")) is not int
                or rating["current_a"] != current
                or source.get("document_url") != documents[0].get("url")
                or source.get("blob_sha256") != blob
                or source.get("page") != 2
                or source.get("quote") != f"{quote} {current} A"
            ):
                raise MigrationError(
                    "Reviewed current or source differs from the original PDF."
                )
    return plan, hashlib.sha256(raw).hexdigest()


def validate_receipt(
    receipt: dict[str, Any], plan: dict[str, Any], digest: str
) -> None:
    """Independently prove that only reviewed ratings were appended."""
    if (
        receipt.get("schema_version") != 1
        or receipt.get("scope") != "nexans-reference-currents-v1"
        or receipt.get("plan_sha256") != digest
        or not isinstance(receipt.get("site"), str)
    ):
        raise MigrationError("Receipt identity or reviewed input differs.")
    products = receipt.get("products")
    if (
        not isinstance(products, dict)
        or len(products) != 2
        or any(
            not isinstance(key, str) or not key.isdigit() or not isinstance(entry, dict)
            for key, entry in products.items()
        )
    ):
        raise MigrationError("Receipt must contain both cable references.")
    entries = {row["id"]: row for row in plan["references"]}
    if {entry.get("engineering_id") for entry in products.values()} != set(REFERENCES):
        raise MigrationError("Receipt reference identities differ.")
    host = urlsplit(receipt["site"]).hostname
    if (
        host not in {"localhost", "127.0.0.1", "::1"}
        and {entry["engineering_id"]: int(key) for key, entry in products.items()}
        != REFERENCES
    ):
        raise MigrationError("Production cable product IDs differ.")
    changes: list[dict[str, Any]] = []
    for key, entry in products.items():
        if not key.isdigit() or not isinstance(entry, dict):
            raise MigrationError("Invalid receipt product.")
        before = entry.get("before")
        documents = entry.get("documents")
        if not isinstance(before, dict) or not isinstance(documents, dict):
            raise MigrationError("Receipt lacks its original metadata or documents.")
        expected = copy.deepcopy(before)
        ratings = expected.setdefault("reference_current_ratings", [])
        if not isinstance(ratings, list):
            raise MigrationError("Original reference currents are not a list.")
        seen = {item.get("id"): item for item in ratings if isinstance(item, dict)}
        if len(seen) != len(ratings) or None in seen:
            raise MigrationError("Original reference current identities are invalid.")
        for planned in entries[entry["engineering_id"]]["cable_facts"][
            "reference_current_ratings"
        ]:
            item = copy.deepcopy(planned)
            source = item["source"]
            doc_id = (
                "doc-"
                + hashlib.sha256(
                    unquote(urlsplit(source["document_url"]).path).encode()
                ).hexdigest()
            )
            doc = documents.get(doc_id)
            if (
                not isinstance(doc, dict)
                or doc.get("blob_sha256") != source["blob_sha256"]
            ):
                raise MigrationError(
                    "Receipt document differs from the reviewed original."
                )
            item["source"] = {
                "document_id": doc_id,
                "document_revision": doc["document_revision"],
                "blob_sha256": source["blob_sha256"],
                "product_id": int(key),
                "page": source["page"],
                "quote": source["quote"],
            }
            existing = seen.get(item["id"])
            if existing is not None and existing != item:
                raise MigrationError("A reviewed reference current conflicts with Woo.")
            if existing is None:
                ratings.append(item)
                seen[item["id"]] = item
                changes.append(
                    {
                        "product_id": int(key),
                        "id": item["id"],
                        "before": None,
                        "after": item,
                    }
                )
        if expected != entry.get("after"):
            raise MigrationError("Receipt modifies unrelated cable facts.")
    if receipt.get("changes") != changes:
        raise MigrationError("Receipt change list differs from its preimages.")


def private_receipt(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or stat.S_IMODE(path.stat().st_mode) != 0o600
        or path.stat().st_uid != os.getuid()
    ):
        raise MigrationError("Receipt must be a private regular file.")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise MigrationError("Receipt is not an object.")
    return value


def write_receipt(path: Path, value: dict[str, Any]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def invoke(site: Target, request: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    payload = base64.b64encode(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    source = PHP.read_text()
    if source.count(PAYLOAD) != 1:
        raise MigrationError("Migration payload marker differs.")
    php = source.removeprefix("<?php").replace(PAYLOAD, repr(payload))
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    try:
        run = subprocess.run(
            command,
            input="<?php" + php,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as error:
        raise MigrationError(
            "Transport timed out; outcome is unknown. Retain the receipt and verify before retrying."
        ) from error
    lines = [
        line[len(MARKER) :]
        for line in run.stdout.splitlines()
        if line.startswith(MARKER)
    ]
    if len(lines) != 1:
        raise MigrationError(
            run.stderr.strip() or "Migration returned no unique result."
        )
    result = json.loads(lines[0])
    if not isinstance(result, dict):
        raise MigrationError("Migration returned an invalid result.")
    if run.returncode:
        raise MigrationError(
            run.stderr.strip() or "Migration failed; retain the receipt."
        )
    return run.returncode, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance")
    target.add_argument("--production", action="store_true")
    parser.add_argument("action", choices=("preview", "apply", "verify", "rollback"))
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan, digest = load_plan()
        receipt = None if args.action == "preview" else private_receipt(args.receipt)
        if args.action == "preview" and (
            args.receipt.exists() or args.receipt.is_symlink()
        ):
            raise MigrationError(
                "Use a new receipt path; existing recovery data is preserved."
            )
        if receipt is not None:
            validate_receipt(receipt, plan, digest)
        request = {
            "action": args.action,
            "plan": plan,
            "plan_sha256": digest,
            "receipt": receipt,
        }
        site = remote_target() if args.production else local_target(args.instance)
        _, result = invoke(site, request)
        if args.action == "preview":
            validate_receipt(result, plan, digest)
            write_receipt(args.receipt, result)
        products = result.get("products")
        if args.action == "preview" and isinstance(products, dict):
            products = [
                {
                    "product_id": int(key),
                    "engineering_id": value["engineering_id"],
                    "product_revision": value["product_revision"],
                }
                for key, value in products.items()
            ]
        print(
            json.dumps(
                {
                    "action": result.get("action"),
                    "source_revision": result.get("source_revision"),
                    "changes": result.get("changes"),
                    "products": products,
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (MigrationError, OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
