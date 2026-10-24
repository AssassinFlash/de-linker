"""Capture actual immutable release bytes before accepting energy runs.

Production packaging must retain this source/lock snapshot and the matching
executable release. A different worker refuses an old run; reads never require
recalculation. The snapshot is private reproducibility data, not authentication.
"""

from __future__ import annotations

import base64
import platform
import sqlite3
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

from .canonical import Json, Object, digest, encode
from .errors import VersionUnavailable


@dataclass(frozen=True)
class RuntimeSnapshot:
    content: bytes
    sha256: str

    @classmethod
    def capture(cls) -> RuntimeSnapshot:
        package = Path(__file__).resolve().parent
        service = package.parents[2]
        files: list[Json] = []
        paths = [
            *sorted(package.glob("*.py")),
            service / "pyproject.toml",
            service / "uv.lock",
        ]
        try:
            for path in paths:
                raw = path.read_bytes()
                files.append(
                    {
                        "path": str(path.relative_to(service)),
                        "sha256": digest(raw),
                        "base64": base64.b64encode(raw).decode("ascii"),
                    }
                )
        except OSError as error:
            raise VersionUnavailable(
                "immutable planning release bytes unavailable"
            ) from error
        document: Object = {
            "schema": 1,
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "libc": list(platform.libc_ver()),
            "sqlite": sqlite3.sqlite_version,
            # Installed versions matter as well as the retained lockfile. In
            # particular raw HTTP read behavior and numerical/geospatial work
            # cannot share an execution identity across different libraries.
            "dependencies": {
                name: version(name)
                for name in (
                    "pydantic",
                    "requests",
                    "urllib3",
                    "pvlib",
                    "numpy",
                    "pandas",
                    "scipy",
                    "pyproj",
                    "shapely",
                )
            },
            "files": files,
        }
        content = encode(document)
        return cls(content, digest(content))
