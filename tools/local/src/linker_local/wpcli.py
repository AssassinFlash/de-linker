"""WP-CLI against one instance, on the instance's PHP and php.ini."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from linker_local.instance import Instance

# The production host runs WP-CLI 2.12.0 (docs/research/2026-10-09/framework-choice.md §2).
VERSION = "2.12"


class WpCliError(RuntimeError):
    """A WP-CLI command failed; the message carries its error output."""


def phar() -> Path:
    """Homebrew's `wp`, run under the instance's PHP rather than its own shebang."""
    found = shutil.which("wp")
    if found is None:
        raise WpCliError(
            "WP-CLI is not installed: brew install wp-cli (docs/local-stack.md)"
        )
    return Path(found)


def environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The environment of every WP-CLI run. A person running WP-CLI is offered
    to replace its phar (Runner::auto_check_update()); it stays on 2.12."""
    return {**os.environ, "WP_CLI_DISABLE_AUTO_CHECK_UPDATE": "1", **(extra or {})}


def require_version(php: Path) -> None:
    """Fail unless `wp` is WP-CLI 2.12.x, the production host's minor version."""
    found = subprocess.run(
        [str(php), str(phar()), "--version"],
        capture_output=True,
        text=True,
        env=environment(),
        check=False,
    ).stdout.strip()
    if not found.startswith(f"WP-CLI {VERSION}."):
        raise WpCliError(
            f"WP-CLI {VERSION} is required (production's), `wp` is {found or 'not runnable'}"
        )


class WpCli:
    """`wp --path=<docroot> ...` under PHP 8.3 with the instance's php.ini."""

    def __init__(self, php: Path, instance: Instance) -> None:
        self.php = php
        self.instance = instance

    def command(self, *args: str) -> list[str]:
        return [
            str(self.php),
            "-c",
            str(self.instance.php_ini),
            str(phar()),
            f"--path={self.instance.docroot}",
            *args,
        ]

    def run(
        self, *args: str, stdin: str | None = None, env: dict[str, str] | None = None
    ) -> str:
        """Run a command and return its standard output without the trailing newline."""
        result = subprocess.run(
            self.command(*args),
            input=stdin,
            capture_output=True,
            text=True,
            env=environment(env),
            cwd=self.instance.dir,
            check=False,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise WpCliError(f"wp {' '.join(args)}: {detail}")
        return result.stdout.rstrip("\n")

    def passthrough(self, args: list[str]) -> int:
        """Run a command attached to the terminal; return its exit status."""
        return subprocess.run(
            self.command(*args),
            env=environment(),
            cwd=self.instance.dir,
            check=False,
        ).returncode
