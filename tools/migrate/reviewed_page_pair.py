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
        json.dumps(
            {
                "operation": "save",
                "changes": payload["changes"],
                "post_type": payload.get("post_type", "page"),
            }
        ).encode()
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
        .replace("/* __REVIEWED_PAIR_CONTENT_WRITER__ */", writer)
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
    marker = "@@reviewed-pair@@"
    for line in result.stdout.splitlines():
        if line.startswith(marker):
            answer = json.loads(line[len(marker) :])
            if isinstance(answer, dict):
                return answer
    raise RuntimeError("WordPress returned no structured paired readback")


def read(prefix: str, en: int, de: int, *, post_type: str = "page") -> dict[str, Any]:
    """Read the explicit language pair and four native translation keys."""
    return invoke(
        prefix,
        {"mode": "read", "post_type": post_type, "changes": [{"id": en}, {"id": de}]},
    )


def changes(
    ids: tuple[int, int], before: dict[str, str], after: dict[str, str]
) -> list[dict[str, Any]]:
    return [
        {"id": post, "before": before[str(post)], "after": after[str(post)]}
        for post in ids
    ]


def write(
    prefix: str,
    ids: tuple[int, int],
    before: dict[str, Any],
    after: dict[str, str],
    metadata: dict[str, Any],
    *,
    adopt: bool = False,
) -> dict[str, Any]:
    invoke(
        prefix,
        {
            "mode": "adopt" if adopt else "restore",
            "changes": changes(ids, before["pages"], after),
            "metadata_before": before["metadata"],
            "require_current": before["current"],
            "expected_metadata" if adopt else "metadata_restore": metadata,
        },
    )
    saved = read(prefix, *ids)
    if saved["pages"] != after or saved["metadata"] != metadata:
        raise RuntimeError("The paired content or translation did not read back")
    return saved


def verify_published(backup: dict[str, Any], current: dict[str, Any]) -> None:
    if (
        current["home"] != backup["before"]["home"]
        or (backup["before"]["current"] and not current["current"])
        or current["pages"] != backup["published_pages"]
        or current["metadata"]
        != backup.get("published_metadata", backup["before"]["metadata"])
    ):
        raise ValueError("The bilingual pair changed since publication")
