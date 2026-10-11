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
import re
import shlex
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


def wp(*args: str) -> str:
    """The instance's WP-CLI, for the fixtures a test creates and removes."""
    result = subprocess.run(
        [*shlex.split(WP), *args], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"wp {args[0]} failed:\n{result.stderr}"
    return result.stdout


def states() -> dict[str, str]:
    """Every customer with its state, read through the migration itself."""
    answer = customers.read(customers.WP(WP, None))
    return {
        str(account["login"]): str(account["state"]) for account in answer["accounts"]
    }


def locales() -> dict[str, str]:
    """Every customer with its user locale, read through the migration itself."""
    answer = customers.read(customers.WP(WP, None))
    return {
        str(account["login"]): str(account["locale"]) for account in answer["accounts"]
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


def test_apply_fills_an_empty_locale_from_the_latest_inquiry() -> None:
    """Ticket #73's backfill, merged into this migration (docs/specs/11-commerce.md).

    Two customers the way the site has them before the cutover: no approval
    state and no locale. The first has two inquiries, the older German and the
    newer English — the run takes the latest. The second already carries a
    locale — the run leaves it. Both, and their orders, are removed again.
    """
    before = states()
    before_locales = locales()
    if any(before.values()):
        pytest.skip(
            "the instance's customers carry approval states already; this migration "
            "is for the state before the cutover, and rollback would remove them"
        )

    def inquiry(customer_id: str, locale: str, created: str) -> str:
        output = wp(
            "eval",
            f'$order = wc_create_order( array( "customer_id" => {customer_id} ) );'
            f' $order->set_date_created( "{created}" );'
            f' $order->update_meta_data( "{customers.INQUIRY_LOCALE_META}", "{locale}" );'
            " $order->save(); echo $order->get_id();",
        )
        return output.strip()

    def customer(login: str) -> str:
        output = wp(
            "user",
            "create",
            login,
            f"{login}@example.test",
            "--role=customer",
            "--porcelain",
        )
        return output.strip()

    empty_login = "linker-migrate-locale-empty"
    kept_login = "linker-migrate-locale-kept"
    empty_id = customer(empty_login)
    kept_id = customer(kept_login)
    orders = [
        inquiry(empty_id, "de_DE_formal", "2026-10-01 10:00:00"),
        inquiry(empty_id, "en_US", "2026-10-02 10:00:00"),
        inquiry(kept_id, "de_DE_formal", "2026-10-02 10:00:00"),
    ]
    try:
        assert empty_id.isdigit() and kept_id.isdigit(), (empty_id, kept_id)
        assert all(order.isdigit() for order in orders), orders
        wp("user", "meta", "update", kept_id, customers.LOCALE_META, "fr_FR")

        planned = run("plan")
        assert planned.returncode == 0, planned.stderr
        print(planned.stdout)
        overview = re.search(
            r"plan: empty locales the run would fill: (\d+)", planned.stdout
        )
        assert overview is not None, planned.stdout
        assert int(overview.group(1)) >= 1
        assert re.search(
            rf"^\s+{empty_login} \(none\), locale <- en_US \(its latest inquiry\)$",
            planned.stdout,
            re.M,
        ), planned.stdout
        assert re.search(
            rf"^\s+{kept_login} \(none\), locale fr_FR$", planned.stdout, re.M
        ), planned.stdout

        applied = run("--user", "1", "apply", "--write")
        assert applied.returncode == 0, applied.stderr
        print(applied.stdout)
        assert f"locales: {overview.group(1)} filled" in applied.stdout

        filled = locales()
        assert filled[empty_login] == "en_US"
        assert filled[kept_login] == "fr_FR"
        assert {
            login: locale for login, locale in filled.items() if login in before_locales
        } == before_locales

        rolled_back = run("--user", "1", "rollback", "--write")
        assert rolled_back.returncode == 0, rolled_back.stderr
        print(rolled_back.stdout)
        # The state is back to the no-decision default; the filled locale stays
        # (it is the value the registration would have written).
        assert {
            login: state for login, state in states().items() if login in before
        } == before
        assert locales()[empty_login] == "en_US"
    finally:
        for order in orders:
            wp(
                "eval",
                f"$order = wc_get_order( {order} ); $order && $order->delete( true );",
            )
        for user_id in (empty_id, kept_id):
            if user_id.isdigit():
                wp("user", "delete", user_id, "--yes")
    assert states() == before
    assert locales() == before_locales
