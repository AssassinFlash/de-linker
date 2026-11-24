"""Run the deployed shell probe against predictable HTTP replies."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (
            '{"status":"ok","service":"linker-planner-http","workspace_readable":true,"worker_alive":true}\n200',
            "200",
        ),
        ('{"status":"degraded","worker_alive":false}\n503', "503"),
        ('{"status":"ok"}\n200', "200/invalid"),
        ("not-json\n200", "200/invalid"),
    ],
)
def test_probe_collects_all_services_even_after_a_failure(
    tmp_path: Path, reply: str, expected: str
) -> None:
    curl = tmp_path / "curl"
    curl.write_text("""#!/bin/bash
case "${!#}" in
https://de-linker.com/wp-json/) printf 200 ;;
http://127.0.0.1:8901/health|http://127.0.0.1:8902/health) printf '{"status":"ok"}\\n200' ;;
http://127.0.0.1:8911/health) printf '%s' "$PLANNER_REPLY" ;;
*) exit 9 ;;
esac
""")
    curl.chmod(0o755)
    prior = "2026-11-10T00:00:00Z 200\n"
    log = tmp_path / "site-probe.log"
    log.write_text(prior * 2016)
    proc = subprocess.run(
        ["bash", str(Path(__file__).parents[1] / "ops/site-probe.sh"), str(tmp_path)],
        env={
            **os.environ,
            "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
            "PLANNER_REPLY": reply,
        },
        check=False,
    )
    assert proc.returncode == (0 if expected == "200" else 1)
    records = log.read_text().splitlines()
    assert len(records) == 2016
    assert (tmp_path / "site-probe.last").read_text().splitlines() == [records[-1]]
    assert records[-1].split()[1:] == ["200", "200", expected, "200"]
