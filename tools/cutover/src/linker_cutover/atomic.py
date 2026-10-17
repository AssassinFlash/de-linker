"""Same-filesystem staged publication (#298); transport belongs to Target.

Hidden siblings keep staged and previous plugins out of WordPress discovery.
Directories use the ticket's two renames, with restoration if the second fails.
This is a per-path switch, not a transaction across all deployed plugins.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from linker_cutover.target import CutoverError, Target


def publish(target: Target, source: Path, relative: str) -> str:
    """Upload a complete tree or file beside live; keep the previous version."""
    if not source.is_dir() and not source.is_file():
        raise CutoverError(f"{source} is not a file or directory")
    path = Path(relative)
    staged = str(path.with_name(f".{path.name}.next"))
    live, next_path, previous = (
        shlex.quote(target.path_of(name))
        for name in (relative, staged, str(path.with_name(f".{path.name}.prev")))
    )
    absent = shlex.quote(
        target.path_of(str(path.with_name(f".{path.name}.prev-absent")))
    )
    parent = shlex.quote(target.path_of(str(path.parent)))
    timing = shlex.quote(f"rename {relative}: %R s")
    target.shell(f"set -eu\nmkdir -p {parent}\nrm -rf {next_path}")
    if source.is_file():
        target.copy_file_in(source, staged)
        # Files need only one rename over live. Back up before that rename;
        # unlike moving live away, this never leaves a missing PHP file.
        return target.shell(
            f"""set -eu
test -f {next_path}
rm -rf {previous} {absent}
if [ -e {live} ] || [ -L {live} ]; then
    cp -p {live} {previous}
else
    : > {absent}
fi
TIMEFORMAT={timing}
{{ time mv -f {next_path} {live}; }} 2>&1
"""
        )
    target.copy_in(source, staged)
    return target.shell(
        f"""set -eu
test -d {next_path}
rm -rf {previous} {absent}
restore() {{
    if [ ! -e {live} ] && [ ! -L {live} ]; then
        if [ -e {previous} ] || [ -L {previous} ]; then mv {previous} {live}; fi
    fi
}}
trap restore EXIT
trap 'exit 1' HUP INT TERM
TIMEFORMAT={timing}
{{ time {{
if [ -e {live} ] || [ -L {live} ]; then
    mv {live} {previous}
else
    : > {absent}
fi
mv {next_path} {live}
}}; }} 2>&1
trap - EXIT HUP INT TERM
"""
    )


def rollback(target: Target, relatives: list[str]) -> None:
    """Restore the saved versions without a build, upload or database import.

    Preflight all paths before the first write. A marker records first-time
    installs, so rollback also removes files that did not exist before deploy.
    """
    scripts: list[str] = []
    checks: list[str] = []
    for relative in relatives:
        path = Path(relative)
        live, next_path, previous, absent = (
            shlex.quote(target.path_of(name))
            for name in (
                relative,
                str(path.with_name(f".{path.name}.next")),
                str(path.with_name(f".{path.name}.prev")),
                str(path.with_name(f".{path.name}.prev-absent")),
            )
        )
        message = shlex.quote(f"no previous deployment for {relative}")
        checks.append(
            f"if [ ! -e {previous} ] && [ ! -L {previous} ] && [ ! -f {absent} ]; "
            f"then echo {message} >&2; exit 1; fi"
        )
        scripts.append(
            f"""if [ -f {absent} ]; then
    rm -rf {live}
    rm -f {absent}
elif [ -d {previous} ] || [ -L {previous} ]; then
    rm -rf {next_path}
    restore_rollback() {{
        if [ ! -e {live} ] && [ ! -L {live} ]; then
            if [ -e {next_path} ] || [ -L {next_path} ]; then mv {next_path} {live}; fi
        fi
    }}
    trap restore_rollback EXIT
    trap 'exit 1' HUP INT TERM
    if [ -e {live} ] || [ -L {live} ]; then mv {live} {next_path}; fi
    mv {previous} {live}
    trap - EXIT HUP INT TERM
    rm -rf {next_path}
else
    mv -f {previous} {live}
fi"""
        )
    target.shell("set -eu\n" + "\n".join(checks + scripts))
