"""WP-CLI against one instance, on the instance's PHP and php.ini."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from linker_local.instance import Instance


class WpCliError(RuntimeError):
    """A WP-CLI command failed; the message carries its error output."""


def phar() -> Path:
    """Homebrew's `wp` (WP-CLI 2.12, the production host's version, framework-choice.md §2)."""
    found = shutil.which("wp")
    if found is None:
        raise WpCliError(
            "WP-CLI is not installed: brew install wp-cli (docs/local-stack.md)"
        )
    return Path(found)


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

    def environment(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        # WP-CLI offers to replace its own phar when a person runs it
        # (Runner::auto_check_update()); the instance stays on 2.12.
        return {**os.environ, "WP_CLI_DISABLE_AUTO_CHECK_UPDATE": "1", **(extra or {})}

    def run(
        self, *args: str, stdin: str | None = None, env: dict[str, str] | None = None
    ) -> str:
        """Run a command and return its standard output without the trailing newline."""
        result = subprocess.run(
            self.command(*args),
            input=stdin,
            capture_output=True,
            text=True,
            env=self.environment(env),
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
            env=self.environment(),
            cwd=self.instance.dir,
            check=False,
        ).returncode
