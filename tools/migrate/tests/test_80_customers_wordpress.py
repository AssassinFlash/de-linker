"""80-customers.py with its real WordPress side (80-customers.php) on a local instance.

The instance is the one whose WP-CLI command is LINKER_MIGRATE_TEST_WP, e.g.
~/de-linker-local/t80/wp.sh, carrying the live snapshot (its customers have no
approval state yet — the state this migration is for). Without it the tests are
skipped (CI has no WordPress). The tests write, verify and roll back there and
leave the instance as they found it.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

HERE = Path(__file__).resolve().parent
WP = os.environ.get("LINKER_MIGRATE_TEST_WP", "")

pytestmark = pytest.mark.skipif(
    not WP,
    reason="Set LINKER_MIGRATE_TEST_WP to the WP-CLI command of a local instance "
    "carrying the live snapshot.",
)


def load_script() -> ModuleType:
    """80-customers.py is a script, not an importable module name."""
    spec = importlib.util.spec_from_file_location(
        "eighty_customers_wp", HERE.parent / "80-customers.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


customers = load_script()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HERE.parent / "80-customers.py"), "--wp", WP, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def states() -> dict[str, str]:
    """Every customer with its state, read through the migration itself."""
    answer = customers.read(customers.WP(WP, None))
    return {
        str(account["login"]): str(account["state"]) for account in answer["accounts"]
    }


def test_plan_reads_without_writing() -> None:
    before = states()
    assert before, "the instance carries no customers: load the snapshot first"

    result = run("plan")
    assert result.returncode == 0, result.stderr

    print(result.stdout)
    assert f"{len(before)} customers" in result.stdout
    assert states() == before


def test_apply_verify_and_rollback() -> None:
    before = states()
    if any(before.values()):
        pytest.skip(
            "the instance's customers carry approval states already; this migration "
            "is for the state before the cutover, and rollback would remove them"
        )

    applied = run("--user", "1", "apply", "--write")
    assert applied.returncode == 0, applied.stderr
    print(applied.stdout)
    assert f"written: {len(before)} accounts" in applied.stdout
    assert set(states().values()) == {customers.APPROVED}

    verified = run("verify")
    assert verified.returncode == 0, verified.stdout + verified.stderr
    print(verified.stdout)

    rolled_back = run("--user", "1", "rollback", "--write")
    assert rolled_back.returncode == 0, rolled_back.stderr
    print(rolled_back.stdout)
    assert states() == before

    failed = run("verify")
    assert failed.returncode == 1
    print(failed.stdout)
