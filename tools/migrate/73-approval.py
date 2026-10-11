#!/usr/bin/env python3
"""#73 migration: every existing customer becomes approved at the switch.

Runs against a WordPress through WP-CLI, locally or over SSH:

    python3 tools/migrate/73-approval.py --wp ~/de-linker-local/t73/wp.sh plan
    python3 tools/migrate/73-approval.py --wp ~/de-linker-local/t73/wp.sh apply --write
    python3 tools/migrate/73-approval.py --wp ~/de-linker-local/t73/wp.sh verify
    python3 tools/migrate/73-approval.py --wp "ssh hostinger-de-linker /usr/local/bin/wp --path=..." apply --write

The owner's ruling (ticket 73): existing customers are all approved when the
approval feature switches on, so nobody loses prices they already had. Two
writes per customer, only where the value is missing, so the run is idempotent
and never touches a state a human set afterwards:

1. `linker_approval_status` = approved. Accounts with any recorded state stay
   as they are; a plain customer without one was created before the switch.
   Staff and other roles are not customers and need no approval.
2. `locale` = the language of the customer's most recent inquiry
   (`_linker_locale` on the order), where the user locale is still empty, so
   the later approval emails go out in the language the customer used.

Rollback: the two meta keys are this migration's only user writes; removing
`linker_approval_status` rows returns every customer to the no-decision
default (pending), which is the pre-switch shape only if the switch is being
undone as a whole.
"""

from __future__ import annotations

import argparse
import base64
import shlex
import subprocess
from typing import Any

# The meta keys this migration reads and writes. Their single reader is the
# plugin (Linker\Commerce\Registration\Approval).
STATUS_META = "linker_approval_status"
LOCALE_META = "locale"
APPROVED = "approved"
STATUSES = ("pending", "approved", "restricted", "rejected")


class WP:
    """WP-CLI, as a command prefix."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, as_user: bool = False) -> str:
        command = [*self.prefix, *args]
        if as_user and self.user:
            command.append(f"--user={self.user}")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        return result.stdout

    def query(self, sql: str) -> list[list[str]]:
        """Rows of a SELECT; values that may hold any byte come back base64-encoded by the query."""
        out = self.run("db", "query", sql, "--skip-column-names", "--batch")
        return [line.split("\t") for line in out.splitlines() if line.strip()]


def b64(value: str) -> str:
    """A TO_BASE64() value: MySQL breaks it every 76 characters, which batch output shows as a literal \\n."""
    value = value.replace("\\n", "").strip()
    return base64.b64decode(value).decode("utf-8") if value not in ("", "NULL") else ""


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


class Migration:
    def __init__(self, wp: WP) -> None:
        self.wp = wp
        self.prefix = wp.run("db", "prefix").strip()

    def customers(self) -> list[dict[str, Any]]:
        """Plain customers with their current approval state and user locale.

        The role lives in the serialized capabilities meta value; the LIKE
        matches the role entry inside it. "customer" is a substring of no
        other role name on this site (administrator, editor, author,
        contributor, subscriber, shop_manager).
        """
        role_meta = sql_string(self.prefix + "capabilities")
        rows = self.wp.query(
            f"SELECT u.ID, COALESCE(MAX(CASE WHEN m.meta_key = '{LOCALE_META}' THEN TO_BASE64(m.meta_value) END), ''), "
            f"COALESCE(MAX(CASE WHEN m.meta_key = '{STATUS_META}' THEN TO_BASE64(m.meta_value) END), '') "
            f"FROM {self.prefix}users u "
            f"JOIN {self.prefix}usermeta r ON r.user_id = u.ID AND r.meta_key = {role_meta} "
            f"AND r.meta_value LIKE '%\"customer\"%' "
            f"LEFT JOIN {self.prefix}usermeta m ON m.user_id = u.ID "
            f"AND m.meta_key IN ({sql_string(LOCALE_META)}, {sql_string(STATUS_META)}) "
            f"GROUP BY u.ID ORDER BY u.ID"
        )
        return [
            {
                "id": int(row[0]),
                "locale": b64(row[1]),
                "status": b64(row[2]),
            }
            for row in rows
        ]

    def inquiry_locale(self, user_id: int) -> str:
        """The language of the customer's most recent inquiry, '' when there is none."""
        rows = self.wp.query(
            f"SELECT COALESCE(TO_BASE64(m.meta_value), '') FROM {self.prefix}wc_orders o "
            f"JOIN {self.prefix}wc_orders_meta m ON m.order_id = o.id "
            f"AND m.meta_key = {sql_string('_linker_locale')} "
            f"WHERE o.customer_id = {int(user_id)} AND o.type = 'shop_order' "
            f"ORDER BY o.date_created_gmt DESC LIMIT 1"
        )
        return b64(rows[0][0]) if rows else ""

    def plan(self) -> list[dict[str, Any]]:
        """The writes apply would make, one row per customer that needs one."""
        items = []
        for customer in self.customers():
            writes = {}
            if customer["status"] == "":
                writes[STATUS_META] = APPROVED
            if customer["locale"] == "":
                language = self.inquiry_locale(customer["id"])
                if language != "":
                    writes[LOCALE_META] = language
            if writes:
                items.append({"id": customer["id"], "writes": writes})
        return items

    def apply(self, items: list[dict[str, Any]]) -> int:
        written = 0
        for item in items:
            for key, value in item["writes"].items():
                self.wp.run("user", "meta", "update", str(item["id"]), key, value)
                print(f"user {item['id']}: {key} = {value}")
                written += 1
        return written

    def verify(self) -> bool:
        """Every plain customer has an approval state, and every state is one of the four."""
        bad = []
        for customer in self.customers():
            if customer["status"] == "":
                bad.append(f"user {customer['id']}: no approval state")
            elif customer["status"] not in STATUSES:
                bad.append(f"user {customer['id']}: unknown state {customer['status']}")
        for line in bad:
            print(line)
        print(f"{len(bad)} problems")
        return not bad


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command prefix, e.g. 'ssh host wp --path=…'"
    )
    parser.add_argument(
        "--user", help="administrator login for the steps that need one"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="print what apply would write")
    apply_parser = sub.add_parser("apply", help="the two writes per customer")
    apply_parser.add_argument(
        "--write", action="store_true", help="without it, only the plan is printed"
    )
    sub.add_parser("verify", help="every customer has a valid approval state")
    args = parser.parse_args()

    migration = Migration(WP(args.wp, args.user))
    if args.command == "verify":
        return 0 if migration.verify() else 1
    items = migration.plan()
    for item in items:
        print(
            f"user {item['id']}: {', '.join(f'{key}={value}' for key, value in item['writes'].items())}"
        )
    if args.command == "plan" or not args.write:
        print(
            f"{len(items)} customers to write; dry run"
            + ("" if args.command == "plan" else ": add --write")
        )
        return 0
    written = migration.apply(items)
    print(f"{written} meta values written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
