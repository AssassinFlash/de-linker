"""Where a cutover step runs: the production host, or one local instance.

The steps in `steps` never know which: they call `wp`, `shell`, `copy_out`,
`copy_in`, `http` and read `root`/`base_url`. Two implementations exist and
nowhere else in the tool does a transport appear:

- `local_target(name)` — an instance of the local stack (`just up <name>`,
  docs/local-stack.md), which is what the drill runs against. WP-CLI runs on
  this Mac; "shell" is `bash -c` here; copying is rsync between two local
  directories.
- `remote_target()` — `ssh hostinger-de-linker` (the production host, the same
  address tools/pull reads through). WP-CLI is `/usr/local/bin/wp` on the
  host's PHP 8.3; "shell" is that ssh command; copying is rsync to
  `<host>:<wordpress root>`.

Read-only is NOT a property of this module, unlike tools/pull's live module:
the cutover writes, which is why every step that can is separately re-runnable
and why `backup` runs before anything else.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# The production host and its WordPress root, as tools/pull/src/linker_pull/live.py
# records them (both read from the host on 2026-10-09).
HOST = "hostinger-de-linker"
WP_ROOT = "/home/u388076051/domains/de-linker.com/public_html"
WP_CLI = "/usr/local/bin/wp"
HOST_URL = "https://de-linker.com"
# The paths under the WordPress root a cutover reads or writes. One list, so
# the two targets cannot drift.
PLUGINS = "wp-content/plugins"
UPLOADS = "wp-content/uploads"
HTACCESS = ".htaccess"


class CutoverError(RuntimeError):
    """A step could not run, or a check it makes failed."""


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command, capture_output=True, text=True, check=False, cwd=cwd
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise CutoverError(
            f"{' '.join(shlex.quote(part) for part in command)}: {detail}"
        )
    return result.stdout


@dataclass(frozen=True)
class Target:
    """One WordPress site a cutover can run against, and how to reach it."""

    label: str
    root: str
    base_url: str
    # `prefix` builds the WP-CLI command; a command is `<prefix> <args…>`.
    prefix: tuple[str, ...]
    # How a shell script reaches the machine the site runs on; the script is
    # passed whole, so it may use pipes and quoting.
    shell_prefix: tuple[str, ...] | None
    # Where `copy_in`/`copy_out` place the remote end: None for a local path.
    rsync_remote: str | None

    def wp(self, *args: str, check: bool = True) -> str:
        """Run a WP-CLI command against the site and return its standard output."""
        command = [*self.prefix, *args]
        if not check:
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            return result.stdout.rstrip("\n")
        return _run(command).rstrip("\n")

    def wp_json(self, *args: str) -> Any:
        """A WP-CLI command that prints JSON."""
        return json.loads(self.wp(*args, "--format=json"))

    def shell(self, script: str) -> str:
        """Run a shell script on the machine the site runs on."""
        if self.shell_prefix is None:
            return _run(["bash", "-c", script])
        return _run([*self.shell_prefix, script])

    def rsync(
        self, source: str, destination: str, *, extra: list[str] | None = None
    ) -> str:
        """Copy `source` to `destination` with rsync, either end possibly a host:path."""
        command = ["rsync", "-az", "--delete", *(extra or [])]
        if source.startswith(f"{HOST}:") or destination.startswith(f"{HOST}:"):
            command += ["-e", "ssh -o BatchMode=yes"]
        command += [source, destination]
        return _run(command)

    def path_of(self, relative: str) -> str:
        """Where a WordPress-root-relative path is on this target's machine.

        The guard is here and not in the remote branch alone: `Path(root) /
        "/etc/passwd"` is `/etc/passwd`, so a removal step handed an absolute
        path would delete outside the site on the local target too.
        """
        if relative.startswith("/") or ".." in relative.split("/"):
            raise CutoverError(f"{relative!r} is not a path inside the WordPress root")
        if self.rsync_remote is None:
            return str(Path(self.root) / relative)
        return f"{self.rsync_remote}/{relative}"

    def copy_out(self, relative: str, destination: Path) -> None:
        """Copy a WordPress-root-relative path off the target into `destination`."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.path_of(relative)
        if self.rsync_remote is None:
            if not Path(source).exists():
                raise CutoverError(f"{relative} does not exist on {self.label}")
            # A trailing slash on the source copies the directory's contents,
            # the same thing rsync does with `<host>:<dir>`.
            self.rsync(f"{source}/", f"{destination}/")
            return
        self.rsync(f"{source.rstrip('/')}/", f"{destination}/")

    def copy_in(self, source: Path, relative: str) -> None:
        """Copy `source` onto the target as the WordPress-root-relative `relative`."""
        if not source.is_dir():
            raise CutoverError(f"{source} is not a directory")
        destination = self.path_of(relative)
        if self.rsync_remote is None:
            # `just up` leaves wp-content/plugins/linker-* as symlinks into the
            # checkout. rsync would follow one and write into the repository, so
            # the link is replaced by a directory first — which is what the
            # production copy is, and what a rollback restores.
            path = Path(destination)
            if path.is_symlink():
                path.unlink()
            path.mkdir(parents=True, exist_ok=True)
            self.rsync(f"{source}/", f"{destination}/")
            return
        self.rsync(f"{source}/", f"{destination}/")

    def exists(self, relative: str) -> bool:
        """Whether a WordPress-root-relative path is on the target."""
        result = self.shell(
            f"if [ -e {shlex.quote(self.path_of(relative))} ]; then echo yes; else echo no; fi"
        )
        return result.strip() == "yes"

    def tree(self, relative: str) -> list[str]:
        """Every file under a WordPress-root-relative path, as `<path> <sha256>`."""
        listing = self.shell(
            f"cd {shlex.quote(self.path_of(relative))} && find . -type f -print0 "
            "| sort -z | xargs -0 shasum -a 256"
        )
        return [line.strip() for line in listing.splitlines() if line.strip()]

    def http(self, path: str, *, cache_buster: str | None = None) -> tuple[int, str]:
        """Fetch one path from the site and return (status, body).

        Every request carries a cache-buster: production serves through
        LiteSpeed's full-page cache (docs/local-stack.md "与线上一致的部分"),
        and a cached answer is not evidence about the code under test.
        """
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if cache_buster:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}cbq={cache_buster}"
        request = urllib.request.Request(url, headers={"User-Agent": "linker-cutover"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read().decode(
                    "utf-8", errors="replace"
                )
        except urllib.error.HTTPError as error:
            return error.code, error.read().decode("utf-8", errors="replace")
        except OSError as error:  # a refused connection, a DNS failure, a timeout
            raise CutoverError(f"GET {url}: {error}") from error


def remote_target() -> Target:
    """The production host, over `ssh hostinger-de-linker`."""
    flags = ["ssh", "-o", "BatchMode=yes", HOST]
    return Target(
        label=HOST,
        root=WP_ROOT,
        base_url=HOST_URL,
        prefix=(*flags, f"cd {shlex.quote(WP_ROOT)} && {WP_CLI}"),
        shell_prefix=(*flags, "bash -c"),
        rsync_remote=f"{HOST}:{WP_ROOT}",
    )


def local_target(name: str) -> Target:
    """One local instance of the stack, addressed the way `just up` builds it."""
    # Imported here: this module is the tool's only link to tools/local, and the
    # tests that build a Target by hand must not need an instance registry.
    from linker_local.cli import require_php
    from linker_local.instance import home
    from linker_local.registry import Registry
    from linker_local.wpcli import WpCli

    instance = Registry(home()).get(name)
    if instance is None:
        raise CutoverError(f"no local instance named {name!r} (just up {name})")
    wp = WpCli(require_php(), instance)
    return Target(
        label=f"local:{name}",
        root=str(instance.docroot),
        base_url=instance.url,
        prefix=tuple(wp.command()),
        shell_prefix=None,
        rsync_remote=None,
    )


def wp_prefix_for(target: Target) -> str:
    """The target's WP-CLI command as a string, for `--wp` of tools/migrate."""
    return " ".join(shlex.quote(part) for part in target.prefix)
