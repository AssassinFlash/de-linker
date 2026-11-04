#!/usr/bin/env python3
"""One-time reviewed battery parallel-cluster limit import; runtime consumers read Woo.

Preview stores exact preimages and proposed changes in a local receipt. Apply
requires that receipt and refuses changed products, fields or PDF bytes. The
same receipt supports a guarded rollback without overwriting later edits.
Production data writes require the normal full backup before applying.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/cutover/src"), str(ROOT / "tools/local/src")]

from linker_cutover.target import (  # type: ignore[import-not-found]  # noqa: E402
    local_target,
    remote_target,
)

HERE = Path(__file__).resolve().parent
PLAN = HERE / "548-battery-parallel-limits.json"
PHP = HERE / "548-battery-parallel-limits.php"
MARKER = "@@548-battery-parallel-limits@@"
PAYLOAD = "'548-battery-parallel-limits-payload'"
HEX = re.compile(r"^[a-f0-9]{64}$")
FIELDS = ("stacks_parallel_max",)
SET_KEYS = {"value", "unit", "citation"}


class MigrationError(RuntimeError):
    """The plan, receipt or PHP result is not safe to use."""


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MigrationError(f"{label} must be a JSON object.")
    return cast(dict[str, Any], value)


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or HEX.fullmatch(value) is None:
        raise MigrationError(f"{label} must be a SHA-256 digest.")
    return value


def load_plan(path: Path = PLAN) -> dict[str, Any]:
    """Read and validate the deliberately narrow reviewed-plan contract."""
    if not path.is_file():
        raise MigrationError(f"Reviewed plan is missing: {path}")
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationError(f"Reviewed plan is unreadable: {path}") from error
    plan = _object(raw, "Plan")
    if (
        plan.get("schema_version") != 1
        or plan.get("kind") != "battery_parallel_limits_v1"
    ):
        raise MigrationError("Plan must be a battery_parallel_limits_v1 schema 1.")
    products = _object(plan.get("products"), "Plan products")
    if not products:
        raise MigrationError("Plan contains no products.")
    for key, value in products.items():
        if not key.isdigit() or int(key) < 1:
            raise MigrationError(f"Invalid product key: {key}")
        product = _object(value, f"Plan product {key}")
        if set(product) != {"model", "sku", "figures"}:
            raise MigrationError(f"Plan product {key} has an unsupported shape.")
        if not isinstance(product["model"], str) or not product["model"].strip():
            raise MigrationError(f"Plan product {key} needs a model.")
        if not isinstance(product["sku"], str) or not product["sku"].strip():
            raise MigrationError(f"Plan product {key} needs a SKU.")
        figures = _object(product["figures"], f"Plan product {key} figures")
        if not figures or set(figures) - set(FIELDS):
            raise MigrationError(f"Plan product {key} names an unreviewed field.")
        for field, change in figures.items():
            patch = _object(change, f"Plan product {key} {field}")
            if set(patch) != {"expect", "set", "source"} or patch["expect"] is not None:
                raise MigrationError(f"Plan product {key} {field} was already written.")
            values = _object(patch["set"], f"Plan product {key} {field} set")
            if set(values) != SET_KEYS:
                raise MigrationError(
                    f"Plan product {key} {field} has an unknown shape."
                )
            if (
                not isinstance(values["unit"], str)
                or not values["unit"].strip()
                or not str(values["value"]).isdigit()
            ):
                raise MigrationError(
                    f"Plan product {key} {field} needs a whole count and a unit."
                )
            citation = _object(
                values["citation"], f"Plan product {key} {field} citation"
            )
            if set(citation) != {"url", "page"}:
                raise MigrationError(f"Plan product {key} {field} citation is invalid.")
            if not str(citation["url"]).startswith(
                "https://de-linker.com/wp-content/uploads/"
            ):
                raise MigrationError(f"Plan product {key} {field} cites another host.")
            if type(citation["page"]) is not int or citation["page"] < 1:
                raise MigrationError(f"Plan product {key} {field} needs a page.")
            source = _object(patch["source"], f"Plan product {key} {field} source")
            required = {
                "document_id",
                "blob_sha256",
                "document_revision",
                "page",
                "quote",
                "basis",
            }
            if set(source) != required:
                raise MigrationError(
                    f"Plan product {key} {field} source is incomplete."
                )
            if not isinstance(source["document_id"], str) or not source[
                "document_id"
            ].startswith("doc-"):
                raise MigrationError(f"Plan product {key} {field} has no document.")
            _hash(source["blob_sha256"], f"Plan product {key} {field} blob")
            _hash(source["document_revision"], f"Plan product {key} {field} revision")
            if type(source["page"]) is not int or source["page"] != citation["page"]:
                raise MigrationError(
                    f"Plan product {key} {field} source page differs from its citation."
                )
            if not isinstance(source["quote"], str) or not source["quote"].strip():
                raise MigrationError(f"Plan product {key} {field} has no quote.")
            if not isinstance(source["basis"], str) or not source["basis"].strip():
                raise MigrationError(f"Plan product {key} {field} has no basis.")
    return plan


def load_receipt(path: Path) -> dict[str, Any]:
    """Read a private local receipt without accepting group/world access."""
    if path.is_symlink() or not path.is_file():
        raise MigrationError(f"Receipt is not a regular local file: {path}")
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        raise MigrationError(f"Receipt permissions must be 0600, found {mode:04o}.")
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationError(f"Receipt is unreadable: {path}") from error
    receipt = _object(raw, "Receipt")
    if not isinstance(receipt.get("site"), str):
        raise MigrationError("Receipt has no site.")
    products = _object(receipt.get("products"), "Receipt products")
    if not products:
        raise MigrationError("Receipt contains no products.")
    for key, value in products.items():
        if not key.isdigit() or int(key) < 1:
            raise MigrationError(f"Invalid receipt product key: {key}")
        entry = _object(value, f"Receipt product {key}")
        required = {"model", "before", "after", "protected", "documents"}
        if not required <= set(entry):
            raise MigrationError(f"Receipt product {key} is incomplete.")
        if not isinstance(entry["after"], str) or not isinstance(
            entry["protected"], str
        ):
            raise MigrationError(f"Receipt product {key} has no readback identity.")
        documents = _object(entry["documents"], f"Receipt product {key} documents")
        for document_id, identity in documents.items():
            if not str(document_id).startswith("doc-"):
                raise MigrationError(f"Receipt product {key} has an invalid document.")
            row = _object(identity, f"Receipt product {key} document {document_id}")
            _hash(row.get("blob_sha256"), f"Receipt product {key} blob")
            _hash(row.get("document_revision"), f"Receipt product {key} revision")
    return receipt


def build_request(
    action: str,
    *,
    plan: dict[str, Any] | None = None,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build exactly one of the two transport shapes sent to the PHP side."""
    if action == "preview" and plan is not None and receipt is None:
        return {"action": action, "plan": plan}
    if action in {"apply", "rollback"} and receipt and plan is None:
        return {"action": action, "receipt": receipt}
    raise MigrationError(f"Invalid request for action {action}.")


def parse_marker(output: str) -> dict[str, Any]:
    """Read one stable PHP marker and reject missing or duplicate results."""
    payloads = [
        line[len(MARKER) :] for line in output.splitlines() if line.startswith(MARKER)
    ]
    if len(payloads) != 1:
        raise MigrationError(f"Expected one {MARKER} result, found {len(payloads)}.")
    try:
        return _object(json.loads(payloads[0]), "PHP result")
    except json.JSONDecodeError as error:
        raise MigrationError("PHP result is not valid JSON.") from error


def render(request: dict[str, Any]) -> str:
    """Substitute the one payload placeholder with this request."""
    encoded = base64.b64encode(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    source = PHP.read_text()
    if source.count(PAYLOAD) != 1:
        raise MigrationError("PHP payload placeholder must appear exactly once.")
    return "<?php" + source.removeprefix("<?php").replace(PAYLOAD, repr(encoded))


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Create a new 0600 receipt; never replace an existing recovery point."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance")
    target.add_argument("--production", action="store_true")
    parser.add_argument("action", choices=("preview", "apply", "rollback"))
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    site = remote_target() if args.production else local_target(args.instance)
    if args.action == "preview" and args.receipt.exists():
        parser.error(
            "Use a fresh receipt path; an existing recovery receipt is preserved."
        )
    request = build_request(
        args.action,
        plan=load_plan() if args.action == "preview" else None,
        receipt=None if args.action == "preview" else load_receipt(args.receipt),
    )
    php = render(request)
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    run = subprocess.run(
        command, input=php, capture_output=True, text=True, check=False
    )
    if run.returncode != 0:
        print(run.stderr.strip() or run.stdout.strip(), file=sys.stderr)
        return run.returncode
    result = parse_marker(run.stdout)
    if args.action == "preview":
        write_receipt(args.receipt, result)
    print(
        json.dumps(
            {
                "action": args.action,
                "site": result["site"],
                "changes": result["changes"],
                "source_revision": result["source_revision"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
