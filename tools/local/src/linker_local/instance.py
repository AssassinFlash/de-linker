"""An instance: its name, ports, database and the files it keeps under the data root."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# State shared by every instance on this Mac: the download cache and the
# credentials of the MySQL user. Fixed, so a test run with its own
# LINKER_LOCAL_HOME shares them instead of replacing them.
SHARED = Path.home() / "de-linker-local"

# The address every instance, engine and Genie listens on: the loopback only
# (spec 5: `php -S 127.0.0.1:<port>`).
HOST = "127.0.0.1"

DATABASE_PREFIX = "linker_"
# A database name has at most 64 characters (MySQL 8.4 Reference Manual §11.2.1
# "Identifier Length Limits", read via Apify on 2026-10-09), and an instance's
# database is "linker_<name>". The name is also a directory name and goes
# unquoted into SQL and TOML, so it keeps to lower-case letters, digits and "_".
NAME = re.compile(r"[a-z][a-z0-9_]*")
NAME_MAX_LENGTH = 64 - len(DATABASE_PREFIX)


def home() -> Path:
    """Directory of the registry and the instance directories (`~/de-linker-local`)."""
    return Path(os.environ.get("LINKER_LOCAL_HOME", str(SHARED)))


def database_of(name: str) -> str:
    return DATABASE_PREFIX + name


def directory_of(root: Path, name: str) -> Path:
    return root / name


def check_name(name: str) -> None:
    """Raise ValueError unless `name` can name an instance."""
    if not NAME.fullmatch(name) or len(name) > NAME_MAX_LENGTH:
        raise ValueError(
            f"{name!r} is not an instance name: lower-case letters, digits and _, "
            f"starting with a letter, at most {NAME_MAX_LENGTH} characters"
        )


@dataclass(frozen=True)
class Instance:
    """One WordPress instance; every path it uses is derived here."""

    name: str
    port: int
    engine_port: int
    genie_port: int
    root: Path

    @property
    def database(self) -> str:
        return database_of(self.name)

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}"

    @property
    def dir(self) -> Path:
        return directory_of(self.root, self.name)

    @property
    def docroot(self) -> Path:
        return self.dir / "wordpress"

    @property
    def wp_content(self) -> Path:
        return self.docroot / "wp-content"

    @property
    def php_ini(self) -> Path:
        return self.dir / "php.ini"

    @property
    def router(self) -> Path:
        return self.dir / "router.php"

    @property
    def admin_file(self) -> Path:
        return self.dir / "admin.txt"

    @property
    def snapshot_file(self) -> Path:
        """Which live snapshot the instance holds (linker-pull's `load` writes it)."""
        return self.dir / "snapshot.json"

    @property
    def mail_dir(self) -> Path:
        return self.dir / "mail"

    @property
    def log_dir(self) -> Path:
        return self.dir / "logs"

    @property
    def isolation_log(self) -> Path:
        """Requests the isolation mu-plugin refused, one per line."""
        return self.log_dir / "isolation.log"

    @property
    def run_dir(self) -> Path:
        return self.dir / "run"

    @property
    def provisioned_marker(self) -> Path:
        """Written as the last step of provisioning; its absence means unfinished."""
        return self.dir / ".provisioned"

    def is_provisioned(self) -> bool:
        return self.provisioned_marker.is_file()
