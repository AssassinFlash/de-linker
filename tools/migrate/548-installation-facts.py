#!/usr/bin/env python3
"""Guarded Woo installation-facts migration with a local recovery receipt.

Preview freezes exact meta preimages, protected Woo state, document identities,
source identities and expected hashes. Apply and rollback require that receipt
and refuse later edits. Production writes require the normal full backup.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn, cast

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/cutover/src"), str(ROOT / "tools/local/src")]

from linker_cutover.target import (  # type: ignore[import-not-found]  # noqa: E402
    Target,
    local_target,
    remote_target,
)

HERE = Path(__file__).resolve().parent
PLAN = HERE / "548-installation-facts.json"
PHP = HERE / "548-installation-facts.php"
MARKER = "@@548-installation-facts@@"
PAYLOAD = "'548-installation-facts-payload'"
HEX = re.compile(r"^[a-f0-9]{64}$")


class MigrationError(RuntimeError):
    """The plan, receipt or PHP result is not safe to use."""


def _json_object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MigrationError(f"{label} must be a JSON object.")
    return cast(dict[str, Any], value)


def load_plan(path: Path = PLAN) -> dict[str, Any]:
    """Read and validate the deliberately narrow reviewed-plan contract."""
    if not path.is_file():
        raise MigrationError(f"Reviewed plan is missing: {path}")
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationError(f"Reviewed plan is unreadable: {path}") from error
    plan = _json_object(raw, "Plan")
    if set(plan) != {"schema_version", "products"} or plan["schema_version"] != 1:
        raise MigrationError("Plan must contain only schema_version=1 and products.")
    products = _json_object(plan["products"], "Plan products")
    if not products:
        raise MigrationError("Plan contains no products.")
    for key, value in products.items():
        if not key.isdigit() or int(key) < 1:
            raise MigrationError(f"Invalid product key: {key}")
        product = _json_object(value, f"Plan product {key}")
        if set(product) != {"model", "product_revision", "items"}:
            raise MigrationError(f"Plan product {key} has an unsupported shape.")
        if not isinstance(product["model"], str) or not product["model"].strip():
            raise MigrationError(f"Plan product {key} needs a model.")
        revision = product["product_revision"]
        if not isinstance(revision, str) or HEX.fullmatch(revision) is None:
            raise MigrationError(f"Plan product {key} needs a SHA-256 revision.")
        items = product["items"]
        if not isinstance(items, list) or not items:
            raise MigrationError(f"Plan product {key} needs installation facts.")
        for index, item in enumerate(items):
            _json_object(item, f"Plan product {key} item {index}")
    return plan


def load_receipt(path: Path) -> dict[str, Any]:
    """Read a private local receipt without accepting group/world access."""
    if path.is_symlink() or not path.is_file():
        raise MigrationError(f"Receipt is not a regular local file: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise MigrationError(f"Receipt permissions must be 0600, found {mode:04o}.")
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise MigrationError(f"Receipt is unreadable: {path}") from error
    receipt = _json_object(raw, "Receipt")
    if receipt.get("schema_version") != 1 or not isinstance(receipt.get("site"), str):
        raise MigrationError("Receipt has an unsupported shape.")
    products = _json_object(receipt.get("products"), "Receipt products")
    if not products:
        raise MigrationError("Receipt contains no products.")
    for key, value in products.items():
        if not key.isdigit() or int(key) < 1:
            raise MigrationError(f"Invalid receipt product key: {key}")
        entry = _json_object(value, f"Receipt product {key}")
        required = {
            "model",
            "product_revision",
            "before_exists",
            "before",
            "after",
            "after_hash",
            "protected",
            "documents",
            "product_documents",
            "sources",
        }
        if not required <= set(entry):
            raise MigrationError(f"Receipt product {key} is incomplete.")
        if not isinstance(entry["before_exists"], bool):
            raise MigrationError(f"Receipt product {key} has invalid before state.")
        after = _json_object(entry["after"], f"Receipt product {key} after")
        if after.get("schema_version") != 1 or not isinstance(after.get("items"), list):
            raise MigrationError(f"Receipt product {key} has invalid after metadata.")
        if (
            not isinstance(entry["after_hash"], str)
            or HEX.fullmatch(entry["after_hash"]) is None
        ):
            raise MigrationError(f"Receipt product {key} has an invalid after hash.")
        _json_object(entry["documents"], f"Receipt product {key} documents")
        _json_object(
            entry["product_documents"], f"Receipt product {key} product documents"
        )
        if not isinstance(entry["sources"], list):
            raise MigrationError(
                f"Receipt product {key} has invalid source identities."
            )
    return receipt


def build_request(
    action: str,
    *,
    plan: dict[str, Any] | None = None,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build exactly one of the two transport shapes sent to the PHP side."""
    if action in {"preview", "refresh"} and plan is not None and receipt is None:
        return {"action": action, "plan": plan}
    if (
        action in {"apply", "rollback", "verify"}
        and receipt is not None
        and plan is None
    ):
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
        return _json_object(json.loads(payloads[0]), "PHP result")
    except json.JSONDecodeError as error:
        raise MigrationError("PHP result is not valid JSON.") from error


def invoke(
    site: Target, request: dict[str, Any]
) -> tuple[int, str, dict[str, Any] | None]:
    """Run the WordPress side and retain a marker result even on verify failure."""
    encoded = base64.b64encode(
        json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
    ).decode()
    source = PHP.read_text()
    if source.count(PAYLOAD) != 1:
        raise MigrationError("PHP payload placeholder must appear exactly once.")
    php = source.removeprefix("<?php").replace(PAYLOAD, repr(encoded))
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    run = subprocess.run(
        command, input="<?php" + php, capture_output=True, text=True, check=False
    )
    result = parse_marker(run.stdout) if MARKER in run.stdout else None
    error = run.stderr.strip() or run.stdout.strip()
    return run.returncode, error, result


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """Create a new 0600 receipt; never replace an existing recovery point."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except BaseException:
        # fdopen owns the descriptor once entered; an earlier failure is closed here.
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance")
    target.add_argument("--production", action="store_true")
    parser.add_argument(
        "action", choices=("preview", "apply", "rollback", "verify", "refresh")
    )
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Refresh rewrites the reviewed plan; without it the diff is printed.",
    )
    return parser


def _fail(parser: argparse.ArgumentParser, message: str) -> NoReturn:
    parser.error(message)
    raise AssertionError("argparse.error always exits")


def _refresh(site: Any, write: bool) -> int:
    """Re-pin the reviewed plan to the current publication, changing only revisions.

    The preview already refuses a stale plan, so a plan cannot silently rot into
    a wrong one. What was missing is the sanctioned way to make it current
    again: without it every publication edit means hand-editing revisions and
    hand-editing the frozen-plan test, which is how the plan was put on main
    stale in the first place. Evidence never moves here: a source whose bytes
    differ is refused, not rewritten.
    """
    plan = load_plan(PLAN)
    code, error, result = invoke(site, build_request("refresh", plan=plan))
    if result is None:
        print(error, file=sys.stderr)
        return code or 1
    if code != 0:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(error, file=sys.stderr)
        return code
    pinned = _json_object(result.get("products"), "Refresh products")
    if set(pinned) != set(plan["products"]):
        raise MigrationError(
            "Refresh returned a different product set than the plan: "
            f"{sorted(set(pinned) ^ set(plan['products']))}."
        )
    changes: list[str] = []
    substitutions: dict[str, str] = {}
    for key, entry in plan["products"].items():
        current = _json_object(pinned.get(key), f"Refresh product {key}")
        revision = current.get("product_revision")
        if not isinstance(revision, str) or HEX.fullmatch(revision) is None:
            raise MigrationError(f"Refresh returned no revision for {key}.")
        if entry["product_revision"] != revision:
            changes.append(f"{key} product {entry['product_revision'][:12]} -> {revision[:12]}")
            substitutions[entry["product_revision"]] = revision
            entry["product_revision"] = revision
        documents = _json_object(current.get("documents"), f"Refresh documents {key}")
        for item in entry["items"]:
            source = _json_object(item.get("source"), f"Plan product {key} source")
            document = _json_object(
                documents.get(str(source.get("document_id"))),
                f"Refresh source {source.get('document_id')}",
            )
            if document.get("blob_sha256") != source.get("blob_sha256"):
                raise MigrationError(
                    f"Source bytes changed for {key}/{source.get('document_id')}; "
                    "review the page and quote before refreshing."
                )
            changed = document.get("document_revision")
            if not isinstance(changed, str) or HEX.fullmatch(changed) is None:
                raise MigrationError(f"Refresh returned no document revision for {key}.")
            if source["document_revision"] != changed:
                changes.append(f"{key} document {source['document_revision'][:12]} -> {changed[:12]}")
                substitutions[source["document_revision"]] = changed
                source["document_revision"] = changed
    for change in changes:
        print(change, file=sys.stderr)
    if not changes:
        print(json.dumps({"action": "refresh", "changes": 0, "written": False}))
        return 0
    if not write:
        print(
            json.dumps(
                {"action": "refresh", "changes": len(changes), "written": False},
                ensure_ascii=False,
            )
        )
        return 0
    # Substitute in place: a full re-serialization would reformat every line and
    # bury the nine values this actually changed.
    text = PLAN.read_text()
    for old, new in substitutions.items():
        text = text.replace(old, new)
    PLAN.write_text(text)
    print(json.dumps({"action": "refresh", "changes": len(changes), "written": True}))
    return 0


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    site = remote_target() if args.production else local_target(args.instance)
    try:
        if args.action == "refresh":
            return _refresh(site, args.write)
        if not isinstance(args.receipt, Path):
            _fail(parser, "This action needs --receipt.")
        if args.action == "preview":
            if args.receipt.exists() or args.receipt.is_symlink():
                _fail(
                    parser,
                    "Use a fresh receipt path; existing recovery data is preserved.",
                )
            request = build_request("preview", plan=load_plan())
        else:
            request = build_request(args.action, receipt=load_receipt(args.receipt))
        code, error, result = invoke(site, request)
        if result is None:
            print(error, file=sys.stderr)
            return code or 1
        if code != 0:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(error, file=sys.stderr)
            return code
        if args.action == "preview":
            receipt = load_receipt_from_result(args.receipt, result)
            write_receipt(args.receipt, receipt)
        if args.action == "verify":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
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
    except MigrationError as error:
        print(str(error), file=sys.stderr)
        return 2


def load_receipt_from_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Validate the PHP preview result without exposing a second parser."""
    if result.get("schema_version") != 1 or not isinstance(result.get("site"), str):
        raise MigrationError("Preview result has an unsupported shape.")
    if not isinstance(result.get("products"), dict) or not isinstance(
        result.get("changes"), int
    ):
        raise MigrationError("Preview result is incomplete.")
    if not isinstance(result.get("source_revision"), str):
        raise MigrationError("Preview result has no source revision.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
