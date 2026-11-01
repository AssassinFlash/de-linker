#!/usr/bin/env python3
"""Preview, apply, verify or roll back the reviewed GoodWe controller Woo facts.

Preview records the exact preimages. Retain the private receipt with the
recovery point. Production writes use the established full-backup policy.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/cutover/src"), str(ROOT / "tools/local/src")]

from linker_cutover.target import (  # type: ignore[import-not-found]  # noqa: E402
    local_target,
    remote_target,
)

STEM = "548-controller-facts"
MARKER = f"@@{STEM}@@"
HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance")
    target.add_argument("--production", action="store_true")
    parser.add_argument("action", choices=("preview", "apply", "rollback", "verify"))
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    preview = args.action == "preview"
    receipt: Path = args.receipt
    if preview:
        if receipt.exists() or receipt.is_symlink():
            parser.error("Preview needs a fresh receipt path.")
        path = HERE / f"{STEM}.json"
    else:
        if (
            receipt.is_symlink()
            or not receipt.is_file()
            or receipt.stat().st_mode & 0o077
        ):
            parser.error("Use the regular private file issued by preview.")
        path = receipt
    saved = path.read_bytes()
    request = {
        "action": args.action,
        "plan" if preview else "receipt": json.loads(saved),
    }
    encoded = base64.b64encode(json.dumps(request).encode()).decode()
    source = (HERE / f"{STEM}.php").read_text()
    placeholder = f"'{STEM}-payload'"
    if source.count(placeholder) != 1:
        raise ValueError("Missing or ambiguous WordPress action payload.")
    site = remote_target() if args.production else local_target(args.instance)
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    result = subprocess.run(
        command,
        input=source.replace(placeholder, repr(encoded)),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        print(
            result.stderr.strip() or "Woo action failed without a diagnostic.",
            file=sys.stderr,
        )
        return result.returncode
    lines = [
        line[len(MARKER) :]
        for line in result.stdout.splitlines()
        if line.startswith(MARKER)
    ]
    if len(lines) != 1:
        raise ValueError("Expected one Woo receipt marker.")
    payload = json.loads(lines[0])
    if payload.get("schema_version") != 1 or not isinstance(
        payload.get("products"), dict
    ):
        raise ValueError("Incomplete controller migration receipt.")
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    if preview:
        with os.fdopen(
            os.open(receipt, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb"
        ) as out:
            out.write(data)
    elif args.action in ("apply", "rollback") or (
        args.action == "verify" and payload.get("applied_source_revision")
    ):
        # Keep the preview's exact preimages together with the committed revision.
        with tempfile.NamedTemporaryFile(dir=receipt.parent, delete=False) as out:
            staged = Path(out.name)
        try:
            staged.write_bytes(data)
            if receipt.read_bytes() != saved:
                raise ValueError(
                    "Receipt changed during the operation. Preserve it and verify the target."
                )
            os.replace(staged, receipt)
        finally:
            staged.unlink(missing_ok=True)
    print(
        json.dumps(
            {
                "action": args.action,
                "site": payload["site"],
                "state": payload["state"],
                "source_revision": payload["observed_source_revision"],
                "changes": len(payload["changes"])
                if isinstance(payload["changes"], list)
                else payload["changes"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
