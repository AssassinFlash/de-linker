"""WP-CLI eval-file helper for tools/faq (same shape as tools/migrate/7-facts.py)."""

from __future__ import annotations

import base64
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

PHP = Path(__file__).with_name("wordpress.php")
PHP_PAYLOAD = "'15-faq-payload'"
MARKER = "@@15-faq@@"


def wp_eval(wp: str, request: dict[str, Any]) -> dict[str, Any]:
    """Runs wordpress.php inside WordPress with the request; returns its answer."""
    php = PHP.read_text()
    if php.count(PHP_PAYLOAD) != 1:
        sys.exit(f"{PHP.name} must contain {PHP_PAYLOAD} exactly once.")
    payload = {**request, "marker": MARKER}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    argv = shlex.split(wp) + ["eval-file", "-"]
    result = subprocess.run(
        argv,
        input=php.replace(PHP_PAYLOAD, f"'{encoded}'"),
        capture_output=True,
        text=True,
        check=False,
    )
    answer = next(
        (
            line[len(MARKER) :]
            for line in result.stdout.splitlines()
            if line.startswith(MARKER)
        ),
        None,
    )
    if result.returncode != 0 or answer is None:
        sys.exit(
            f"WP-CLI failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    loaded: dict[str, Any] = json.loads(answer)
    return loaded
