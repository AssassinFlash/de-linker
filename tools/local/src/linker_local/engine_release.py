"""Read a verified, instance-owned executable selection without upgrading it."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from .instance import Instance
from .processes import ProcessError


def engine_project(instance: Instance, checkout: Path) -> Path:
    selection = instance.dir / "planner/engine-release.json"
    if not selection.exists():
        return checkout
    try:
        value: object = json.loads(selection.read_bytes())
        if (
            not isinstance(value, dict)
            or set(value) != {"schema_version", "directory", "files"}
            or type(value["schema_version"]) is not int
            or value["schema_version"] != 1
            or not isinstance(value["directory"], str)
            or not isinstance(value["files"], dict)
            or not value["files"]
        ):
            raise ValueError("invalid executable selection")
        directory = Path(value["directory"])
        releases = instance.dir / "planner/runtime-releases"
        if (
            not directory.is_absolute()
            or directory.is_symlink()
            or not directory.resolve().is_relative_to(instance.dir.resolve())
            or directory.parent.resolve() != releases.resolve()
            or not directory.is_dir()
        ):
            raise ValueError("executable must remain in its owned release directory")
        files = value["files"]
        required = {
            "pyproject.toml",
            "uv.lock",
            "src/linker_engine/__init__.py",
            "src/linker_engine/application.py",
            "src/linker_engine/planning/worker_host.py",
        }
        if not required.issubset(files):
            raise ValueError("incomplete HTTP/worker executable")
        for name, expected in files.items():
            path = PurePosixPath(name)
            if (
                not isinstance(expected, str)
                or re.fullmatch(r"[a-f0-9]{64}", expected) is None
                or path.is_absolute()
                or ".." in path.parts
                or str(path) != name
                or not (
                    name in {"pyproject.toml", "uv.lock"}
                    or (name.startswith("src/linker_engine/") and name.endswith(".py"))
                    or (name.startswith("schemas/") and name.endswith(".json"))
                )
            ):
                raise ValueError("invalid executable file binding")
            target = directory / name
            if (
                target.is_symlink()
                or not target.resolve().is_relative_to(directory.resolve())
                or hashlib.sha256(target.read_bytes()).hexdigest() != expected
            ):
                raise ValueError("executable file no longer matches its binding")
        actual = {
            str(path.relative_to(directory))
            for path in (directory / "src/linker_engine").rglob("*.py")
        }
        actual.update(
            str(path.relative_to(directory))
            for path in (directory / "schemas").rglob("*.json")
        )
        declared = {name for name in files if name.startswith(("src/", "schemas/"))}
        if actual != declared:
            raise ValueError("executable source inventory differs from its binding")
        environment = directory / ".venv"
        if (
            environment.resolve() != (checkout / ".venv").resolve()
            or not (environment / "bin/python").is_file()
        ):
            raise ValueError("executable requires its matching retained environment")
        return directory
    except (OSError, ValueError, TypeError) as error:
        # The original exception can contain private bytes or operator input.
        raise ProcessError(
            "owned engine release selection could not be verified"
        ) from error
