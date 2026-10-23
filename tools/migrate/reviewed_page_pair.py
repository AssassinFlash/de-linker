"""Compose trusted CLI templates; page content travels only as base64 JSON."""

from __future__ import annotations

import base64
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def render(payload: dict[str, Any]) -> str:
    """Keep the hardened content writer unchanged, inside the baseline wrapper."""
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    writer_payload = base64.b64encode(
        json.dumps({"operation": "save", "changes": payload["changes"]}).encode()
    ).decode()
    writer = (
        (HERE / "repair-legal-script.php")
        .read_text()
        .removeprefix("<?php")
        .replace("__LEGAL_SCRIPT_PAYLOAD__", writer_payload)
    )
    return (
        (HERE / "reviewed-page-pair.php")
        .read_text()
        .removeprefix("<?php")
        .replace("__REVIEWED_PAIR_PAYLOAD__", encoded)
        .replace(
            "throw new LogicException( '__REVIEWED_PAIR_CONTENT_WRITER__' );", writer
        )
    )


def invoke(prefix: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Use the existing WP-CLI STDIN transport without shell interpolation."""
    command = shlex.split(prefix)
    tail = ["eval", "eval( stream_get_contents( STDIN ) );"]
    command = (
        [*command, shlex.join(tail)]
        if Path(command[0]).name == "ssh"
        else [*command, *tail]
    )
    result = subprocess.run(
        command, input=render(payload), text=True, capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            f"WordPress failed ({result.returncode}): {result.stderr[:800]}"
        )
    marker = "@@reviewed-pair@@" if payload["mode"] == "read" else "@@legal-script@@"
    for line in result.stdout.splitlines():
        if line.startswith(marker):
            answer = json.loads(line[len(marker) :])
            if isinstance(answer, dict):
                return answer
    raise RuntimeError("WordPress returned no structured paired readback")


def read(prefix: str, en: int, de: int) -> dict[str, Any]:
    """Read the explicit language pair and four native translation keys."""
    return invoke(prefix, {"mode": "read", "changes": [{"id": en}, {"id": de}]})
