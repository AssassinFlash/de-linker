"""The Homebrew MySQL server: the `linker_local` user and one database per instance.

Administration runs as MySQL's root over the local socket (`mysql -u root`,
which Homebrew's MySQL accepts without a password); WordPress connects as
`linker_local`, which is granted its instances' databases and nothing else.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from linker_local import secret
from linker_local.instance import SHARED
from linker_local.processes import without_research_credentials

USER = "linker_local"
# Where the password of linker_local is kept: one per machine, as the user is.
CREDENTIALS = SHARED / "linker_local.my.cnf"


class MySQLError(RuntimeError):
    """A statement failed; the message carries MySQL's error."""


class MySQL:
    """Root-level statements through the `mysql` client."""

    def __init__(self, credentials: Path) -> None:
        # A MySQL option file ([client] user/password), readable by its owner
        # only: `mysql --defaults-extra-file=<it>` opens a session as linker_local.
        self.credentials = credentials

    def query(self, sql: str) -> str:
        result = subprocess.run(
            [
                "mysql",
                "--user=root",
                "--batch",
                "--skip-column-names",
                "--execute",
                sql,
            ],
            env=without_research_credentials(),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise MySQLError(
                result.stderr.strip() or f"mysql exited with {result.returncode}"
            )
        return result.stdout

    def socket(self) -> str:
        """Path of the server's Unix socket; WordPress connects through it."""
        return self.query("SELECT @@socket").strip()

    def ensure_user(self) -> str:
        """Create `linker_local` on first use and return its password."""
        if self.credentials.exists():
            password = self._read_password()
            if not self._user_exists():
                self.query(
                    f"CREATE USER '{USER}'@'localhost' IDENTIFIED BY '{password}'"
                )
            return password
        if self._user_exists():
            raise MySQLError(
                f"MySQL user {USER} exists but {self.credentials} is missing; drop the user "
                f"(mysql -u root -e \"DROP USER '{USER}'@'localhost'\") and reset the instances"
            )
        password = secret.password()
        self.credentials.parent.mkdir(parents=True, exist_ok=True)
        self.credentials.touch(mode=0o600)
        self.credentials.write_text(f"[client]\nuser={USER}\npassword={password}\n")
        self.query(f"CREATE USER '{USER}'@'localhost' IDENTIFIED BY '{password}'")
        return password

    def database_exists(self, database: str) -> bool:
        return bool(
            self.query(f"SHOW DATABASES LIKE '{_like_literal(database)}'").strip()
        )

    def grant_dump_privileges(self) -> None:
        """Give `linker_local` what a consistent dump needs.

        `GRANT ALL PRIVILEGES ON <database>.*` is not enough: since MySQL
        8.0.32, mysqldump's `--single-transaction` — the flag that makes a dump
        of a live site consistent, and the one tools/pull and tools/cutover both
        use — starts with `FLUSH /*!40101 LOCAL */ TABLES`, and that is a global
        privilege. Without it a local instance cannot be dumped the way the
        production host is dumped, which is exactly what the cutover drill runs
        (`docs/specs/17-cutover.md`, `tools/cutover`). Both of the privileges the
        server names in its refusal are granted ("you need (at least one of) the
        RELOAD or FLUSH_TABLES privilege(s)"), and re-granting is a no-op, so
        this stays idempotent.
        """
        self.query(f"GRANT FLUSH_TABLES, RELOAD ON *.* TO '{USER}'@'localhost'")

    def create_database(self, database: str) -> None:
        """Create the database and grant it to linker_local; the name is check_name()-safe."""
        self.query(
            f"CREATE DATABASE `{database}`;"
            f" GRANT ALL PRIVILEGES ON `{database}`.* TO '{USER}'@'localhost'"
        )
        self.grant_dump_privileges()

    def drop_database(self, database: str) -> None:
        self.query(f"DROP DATABASE IF EXISTS `{database}`")

    def _user_exists(self) -> bool:
        found = self.query(
            f"SELECT COUNT(*) FROM mysql.user WHERE user = '{USER}' AND host = 'localhost'"
        )
        return found.strip() == "1"

    def _read_password(self) -> str:
        for line in self.credentials.read_text().splitlines():
            if line.startswith("password="):
                return line.removeprefix("password=")
        raise MySQLError(f"{self.credentials} has no password line")


def _like_literal(value: str) -> str:
    """Escape LIKE's wildcard "_" so SHOW DATABASES matches the name exactly."""
    return value.replace("_", "\\_")
