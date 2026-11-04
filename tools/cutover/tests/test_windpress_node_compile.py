"""The headless WindPress compile's contract tests (Node), run from the
cutover lane that owns the deploy flow around them."""

import subprocess
from pathlib import Path


def test_windpress_node_compile_contract() -> None:
    subprocess.run(
        [
            "node",
            "--test",
            str(
                Path(__file__).resolve().parents[2] / "windpress-node-compile.test.mjs"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
