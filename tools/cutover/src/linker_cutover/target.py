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
from http.client import HTTPMessage
from pathlib import Path
from typing import IO, Any

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
# The switch writes here too (`steps.deploy`, `steps.remove_legacy`), so the
# backup carries it and the rollback puts it back (#81).
MU_PLUGINS = "wp-content/mu-plugins"
HTACCESS = ".htaccess"


class CutoverError(RuntimeError):
    """A step could not run, or a check it makes failed."""


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """An opener part that refuses every redirect, so a 3xx stays a 3xx.

    urllib follows redirects by default, and that is what made `verify`'s
    redirect assertion unfalsifiable: the 301 it asked about came back as the
    200 at the end of the chain, so the drill's record shows `/design-canvas/`
    answering 200 on a site that answers 301. Refusing the redirect hands the
    response to `HTTPDefaultErrorHandler`, which raises `HTTPError` — the
    status `http` reports is then the one the address itself answered.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Never build the follow-up request; see the class comment."""
        del req, fp, code, msg, headers, newurl
        return None


# One opener for every read: it holds no state, and building one is not free.
# `urllib.request.urlopen` is the redirect-following default and is not used here.
OPENER = urllib.request.build_opener(_NoRedirects)


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


def tar_pull_command(host: str, source: str) -> list[str]:
    """`ssh <host> tar -czf -` for a directory's contents, quoted for the far shell."""
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        host,
        f"tar -C {shlex.quote(source)} -czf - .",
    ]


def tar_push_command(host: str, destination: str) -> list[str]:
    """`ssh <host> 'mkdir -p … && tar -xzf -'` for a directory's contents."""
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        host,
        f"mkdir -p {shlex.quote(destination)} && tar -C {shlex.quote(destination)} -xzf -",
    ]


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

    def wp_on_target(self) -> list[str]:
        """WP-CLI as command parts valid ON the machine the site runs on.

        The remote prefix is an ssh command line ("cd <root> && <wp>"); the
        backup's dump and restore scripts already run on that machine, so the
        cd becomes `--path` and no transport remains. Running the remote form
        there would ssh to an alias that host does not have (measured
        2026-10-14: the dump died with "Could not resolve hostname").
        """
        if self.shell_prefix is None:
            return list(self.prefix)
        return [WP_CLI, f"--path={self.root}"]

    def shell_command(self, script: str) -> list[str]:
        """The argv that runs a shell script on the machine the site runs on.

        ssh joins its arguments with spaces and the remote login shell splits
        them again: beside `bash -c` the script must travel as one quoted word,
        or the remote shell eats its first token (measured 2026-10-14: the
        backup's dump arrived as a bare `set`, which printed the environment).
        One implementation: `shell` and the backup's stream both call this.
        """
        if self.shell_prefix is None:
            return ["bash", "-c", script]
        return [*self.shell_prefix, shlex.quote(script)]

    def shell(self, script: str) -> str:
        """Run a shell script on the machine the site runs on."""
        return _run(self.shell_command(script))

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
        """Where a WordPress-root-relative path is on the machine the site runs on.

        The guard is here and not in the remote branch alone: `Path(root) /
        "/etc/passwd"` is `/etc/passwd`, so a removal step handed an absolute
        path would delete outside the site on the local target too.
        """
        if relative.startswith("/") or ".." in relative.split("/"):
            raise CutoverError(f"{relative!r} is not a path inside the WordPress root")
        return str(Path(self.root) / relative)

    def address(self, relative: str) -> str:
        """The same path as rsync needs it: `host:path` when the site is remote.

        This is not `path_of`. A shell script, an `-e` test and a `cd` run on
        the machine the site runs on and want the bare path; rsync on this Mac
        wants the host in front of it. Handing the `host:path` form to the
        shell is a directory named after a host that no machine has: `[ -e ]`
        answers no, so every removal guarded by it was silently skipped.
        """
        path = self.path_of(relative)
        if self.rsync_remote is None:
            return path
        host = self.rsync_remote.split(":", 1)[0]
        return f"{host}:{path}"

    def copy_out(self, relative: str, destination: Path) -> None:
        """Copy a WordPress-root-relative directory off the target into `destination`."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.address(relative)
        if self.rsync_remote is None and not Path(self.path_of(relative)).is_dir():
            raise CutoverError(f"{relative} is not a directory on {self.label}")
        if self.rsync_remote is not None:
            # openrsync (macOS's rsync) dies on a large tree against this host
            # ("Connection closed by remote host", measured 2026-10-14); a tar
            # stream survives it. Directory contents, like rsync's slash form.
            destination.mkdir(parents=True, exist_ok=True)
            with subprocess.Popen(
                tar_pull_command(HOST, self.path_of(relative).rstrip("/")),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as pull:
                pushed = subprocess.run(
                    ["tar", "-C", str(destination), "-xzf", "-"],
                    stdin=pull.stdout,
                    check=False,
                )
                pull.wait()
            if pull.returncode != 0 or pushed.returncode != 0:
                detail = (pull.stderr.read() if pull.stderr else b"").decode(
                    errors="replace"
                ).strip()
                raise CutoverError(
                    f"reading {relative} from {self.label} failed: {detail}"
                )
            return
        # A trailing slash on the source copies the directory's contents, the
        # same thing rsync does with `<host>:<dir>`.
        self.rsync(f"{source.rstrip('/')}/", f"{destination}/")

    def copy_file_out(self, relative: str, destination: Path) -> None:
        """Copy one WordPress-root-relative file off the target to `destination`.

        One file is not the directory case: rsync's trailing slash means "this
        directory's contents", and on a file it is an error (`Not a directory`)
        — which is how `.htaccess` came to be written into a backup as an empty
        file instead of being taken. Same seam, same machine rules, the shape
        the caller names.
        """
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = self.path_of(relative)
        if self.rsync_remote is None and not Path(source).is_file():
            raise CutoverError(f"{relative} is not a file on {self.label}")
        self.rsync(self.address(relative), str(destination))

    def copy_file_in(self, source: Path, relative: str) -> None:
        """Copy one local file onto the target as the root-relative `relative`."""
        if not source.is_file():
            raise CutoverError(f"{source} is not a file")
        self.rsync(str(source), self.address(relative))

    def copy_in(self, source: Path, relative: str) -> None:
        """Copy `source` onto the target as the WordPress-root-relative `relative`."""
        if not source.is_dir():
            raise CutoverError(f"{source} is not a directory")
        destination = self.address(relative)
        if self.rsync_remote is None:
            # `just up` leaves wp-content/plugins/linker-* as symlinks into the
            # checkout. rsync would follow one and write into the repository, so
            # the link is replaced by a directory first — which is what the
            # production copy is, and what a rollback restores.
            path = Path(self.path_of(relative))
            if path.is_symlink():
                path.unlink()
            path.mkdir(parents=True, exist_ok=True)
            self.rsync(f"{source}/", f"{destination}/")
            return
        # See copy_out: the remote directory travels as a tar stream.
        with subprocess.Popen(
            ["tar", "-C", str(source), "-czf", "-", "."],
            stdout=subprocess.PIPE,
        ) as pack:
            pushed = subprocess.run(
                tar_push_command(HOST, destination),
                stdin=pack.stdout,
                check=False,
            )
        if pushed.returncode != 0:
            raise CutoverError(f"writing {relative} to {self.label} failed")

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

        Redirects are not followed (OPENER): a caller asking about a 301 is
        asking about the address, not about where it points.
        """
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if cache_buster:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}cbq={cache_buster}"
        request = urllib.request.Request(url, headers={"User-Agent": "linker-cutover"})
        try:
            with OPENER.open(request, timeout=30) as response:
                return response.status, response.read().decode(
                    "utf-8", errors="replace"
                )
        except urllib.error.HTTPError as error:
            # A 3xx lands here too, by design: `_NoRedirects` leaves it to the
            # default error handler, which raises with the status and the body.
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
