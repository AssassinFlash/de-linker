#!/usr/bin/env python3
"""One-time reviewed Woo fact repair; runtime consumers read Woo, never this plan.

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
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/cutover/src"), str(ROOT / "tools/local/src")]

from linker_cutover.target import (  # type: ignore[import-not-found]  # noqa: E402
    local_target,
    remote_target,
)

HERE = Path(__file__).resolve().parent
MARKER = "@@615-dc-figures@@"


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
    request: dict[str, Any] = {"action": args.action}
    if args.action == "preview":
        request["plan"] = json.loads((HERE / "615-dc-figures.json").read_text())
    else:
        request["receipt"] = json.loads(args.receipt.read_text())
    encoded_request = base64.b64encode(json.dumps(request).encode()).decode()
    php = (HERE / "615-dc-figures.php").read_text().removeprefix("<?php")
    php = php.replace("'615-dc-figures-payload'", repr(encoded_request))
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    run = subprocess.run(
        command, input="<?php" + php, capture_output=True, text=True, check=False
    )
    if run.returncode != 0:
        print(run.stderr.strip() or run.stdout.strip(), file=sys.stderr)
        return run.returncode
    output = run.stdout
    result = json.loads(
        next(
            line[len(MARKER) :]
            for line in output.splitlines()
            if line.startswith(MARKER)
        )
    )
    if args.action == "preview":
        # Exclusive creation keeps a previous receipt intact even on a racing invocation.
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
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
