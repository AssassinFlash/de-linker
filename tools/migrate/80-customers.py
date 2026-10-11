#!/usr/bin/env python3
"""#80 migration: the accounts that existed before the cutover are approved.

The site's accounts carry an approval state, `linker_account_status`: what a
visitor becomes when they register is `pending`, and the three states the team
sets on an account are `approved`, `restricted` and `rejected`. That state
belongs to the account approval of the commerce chain; this migration is the
one write that happens outside a person's click, because the cutover must not
lock out the customers who were already here:

    every account with WooCommerce's customer role *at the moment of the run*
    gets `approved`.

It runs once, after the new plugins are in place (docs/specs/17-cutover.md
step 4). A second run is harmless: accounts already approved are left alone,
and accounts registered later are never touched (the site's own registration
gives them their state).

Usage (a local instance first; live through the cutover's WP-CLI):

    python3 tools/migrate/80-customers.py --wp ~/de-linker-local/t80/wp.sh plan
    python3 tools/migrate/80-customers.py --wp ~/de-linker-local/t80/wp.sh --user 1 apply --write
    python3 tools/migrate/80-customers.py --wp ~/de-linker-local/t80/wp.sh verify

`plan` is the dry run: it reports every customer with its current state and
writes nothing. `apply` without `--write` writes nothing either. `verify`
fails (exit 1) while any customer is not approved. `rollback --write` removes
the state again — before the run no customer had it, so removal is exactly the
state the site was in; the database backup the cutover takes first is the
further fallback.

The WordPress side is 80-customers.php, which WP-CLI evaluates (wp eval-file -).
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

PHP = Path(__file__).with_name("80-customers.php")
PHP_PAYLOAD = "'80-customers-payload'"
MARKER = "@@80-customers@@"

# The account approval state: the user meta, and the value every account that
# was already here gets. One place, because the writing of this state and the
# reading of it (the account approval of the commerce chain) must not drift:
# docs/specs/17-cutover.md step 4 names the same key.
META_KEY = "linker_account_status"
APPROVED = "approved"

# A PHP diagnostic the WP-CLI phar may print into stdout ahead of the value
# (9-i18n.py, same phar, same machine).
PHP_DIAGNOSTIC = re.compile(
    r"^(?:PHP )?(?:Deprecated|Warning|Notice|Fatal error|Parse error): "
    r".+ in .+ on line \d+$"
)


class WP:
    """WP-CLI, as a command prefix (the 9-i18n.py wrapper)."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, stdin: str | None = None, as_user: bool = False) -> str:
        command = [*self.prefix, *args]
        if as_user and self.user:
            command.append(f"--user={self.user}")
        result = subprocess.run(
            command, input=stdin, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        return "\n".join(
            line
            for line in result.stdout.splitlines()
            if not PHP_DIAGNOSTIC.match(line)
        )

    def wp_eval(
        self, request: dict[str, Any], *, as_user: bool = False
    ) -> dict[str, Any]:
        """Runs 80-customers.php inside WordPress with the request."""
        php = PHP.read_text()
        if php.count(PHP_PAYLOAD) != 1:
            raise SystemExit(f"{PHP.name} must contain {PHP_PAYLOAD} exactly once.")
        payload = {**request, "marker": MARKER, "meta_key": META_KEY, "value": APPROVED}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        output = self.run(
            "eval-file",
            "-",
            stdin=php.replace(PHP_PAYLOAD, f"'{encoded}'"),
            as_user=as_user,
        )
        answer = next(
            (
                line[len(MARKER) :]
                for line in output.splitlines()
                if line.startswith(MARKER)
            ),
            None,
        )
        if answer is None:
            raise SystemExit(f"no answer from {PHP.name}:\n{output}")
        loaded: dict[str, Any] = json.loads(answer)
        return loaded


def read(wp: WP) -> dict[str, Any]:
    return wp.wp_eval({"action": "read"})


def states(answer: dict[str, Any]) -> str:
    """The counts of the answer by state, 'none' for accounts without one."""
    counts = {
        key: value
        for key, value in answer.items()
        if key not in ("customers", "accounts", "wrong", "ok", "written", "removed")
    }
    named = {
        ("none" if "" == key else key): len(value) for key, value in counts.items()
    }
    return ", ".join(f"{key} {named[key]}" for key in sorted(named))


def print_accounts(answer: dict[str, Any]) -> None:
    for account in answer.get("accounts", []):
        state = account["state"] or "none"
        print(f"    {account['login']} ({state})")


def do_plan(wp: WP) -> int:
    answer = read(wp)
    print(f"{answer.get('customers', 0)} customers: {states(answer) or 'none'}")
    print_accounts(answer)
    print(f"plan: every account above would be set to {APPROVED}")
    return 0


def do_apply(wp: WP, write: bool) -> int:
    if not write:
        answer = read(wp)
        print(f"{answer.get('customers', 0)} customers: {states(answer) or 'none'}")
        print(f"dry run: a run with --write sets every account above to {APPROVED}")
        return 0
    answer = wp.wp_eval({"action": "write"}, as_user=True)
    print(f"written: {answer.get('written', 0)} accounts set to {APPROVED}")
    print(f"now: {states(answer)}")
    return 0


def do_verify(wp: WP) -> int:
    answer = wp.wp_eval({"action": "verify"})
    if answer.get("ok"):
        print(f"verify: {answer.get('customers', 0)} customers, all {APPROVED}")
        return 0
    print(
        f"verify: FAILED — {len(answer.get('wrong', []))} customers are not {APPROVED}:"
    )
    for login in answer.get("wrong", []):
        print(f"    {login}")
    return 1


def do_rollback(wp: WP, write: bool) -> int:
    if not write:
        answer = read(wp)
        print(f"{answer.get('customers', 0)} customers: {states(answer) or 'none'}")
        print("dry run: a run with --write removes the state again")
        return 0
    answer = wp.wp_eval({"action": "rollback"}, as_user=True)
    print(f"removed: the state of {answer.get('removed', 0)} accounts")
    print(f"now: {states(answer) or 'none'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command, e.g. ~/de-linker-local/t80/wp.sh"
    )
    parser.add_argument(
        "--user", default=None, help="administrator login, for unfiltered writes"
    )
    parser.add_argument("command", choices=["plan", "apply", "verify", "rollback"])
    parser.add_argument("--write", action="store_true", help="apply for real")
    args = parser.parse_args()
    wp = WP(args.wp, args.user)
    if args.command == "plan":
        return do_plan(wp)
    if args.command == "apply":
        return do_apply(wp, args.write)
    if args.command == "verify":
        return do_verify(wp)
    return do_rollback(wp, args.write)


if __name__ == "__main__":
    sys.exit(main())
