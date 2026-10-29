#!/usr/bin/env python3
"""Show existing reviewed German document titles on German pages only.

Plan reads the fresh Woo snapshot and writes a local receipt. Apply stores that
exact map in one option and refuses if the reviewed titles or the option changed.
Rollback restores the option captured in the receipt. This does not rewrite
stored English wording. Production use still requires the normal full backup;
this session does not write production.
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
MARKER = "@@de-document-descriptions@@"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--instance")
    target.add_argument("--production", action="store_true")
    parser.add_argument("action", choices=("plan", "apply", "verify", "rollback"))
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.production
        and os.environ.get("LINKER_ALLOW_PRODUCTION_CONTENT_WRITE") != "1"
    ):
        parser.error(
            "Production content writes stay refused until LINKER_ALLOW_PRODUCTION_CONTENT_WRITE=1 is set for a backed-up run."
        )
    site = remote_target() if args.production else local_target(args.instance)
    if args.action == "plan" and args.receipt.exists():
        parser.error(
            "Use a fresh receipt path; an existing recovery receipt is preserved."
        )
    request: dict[str, Any] = {"action": args.action}
    if args.action != "plan":
        request["receipt"] = json.loads(args.receipt.read_text())
    encoded = base64.b64encode(json.dumps(request).encode()).decode()
    php = (HERE / "de-document-descriptions.php").read_text().removeprefix("<?php")
    php = php.replace("'de-document-descriptions-payload'", repr(encoded))
    command = site.shell_command(shlex.join([*site.wp_on_target(), "eval-file", "-"]))
    run = subprocess.run(
        command, input="<?php" + php, capture_output=True, text=True, check=False
    )
    if run.returncode != 0:
        print(run.stderr.strip() or run.stdout.strip(), file=sys.stderr)
        return run.returncode
    result = json.loads(
        next(
            line[len(MARKER) :]
            for line in run.stdout.splitlines()
            if line.startswith(MARKER)
        )
    )
    if args.action == "plan":
        fd = os.open(args.receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    titles = result.get("titles")
    if titles is None:
        titles = len(result.get("map") or {})
    if (
        args.action in {"apply", "verify"}
        and "receipt" in request
        and not result.get("map")
    ):
        titles = len(request["receipt"]["map"])
    print(
        json.dumps(
            {
                "action": args.action,
                "site": result.get("site"),
                "changes": result.get("changes"),
                "titles": titles,
                "blockers": len(
                    result.get(
                        "blockers", request.get("receipt", {}).get("blockers", [])
                    )
                ),
                "ok": result.get("ok"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
