"""Exercise the generated controller with isolated, in-memory host callbacks."""

import subprocess
from pathlib import Path


def test_epc_media_lifecycle() -> None:
    subprocess.run(
        [
            "node",
            "--test",
            str(Path(__file__).with_name("epc-media-controller.test.cjs")),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
