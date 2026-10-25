"""Content identity of the real knowledge preparation and applicability recipe.

Woo owns inputs; this identity owns how those inputs become a serving index. A
compiler correction must automatically reprocess an unchanged Woo source. Paths
are relative to this service, never deployment paths, credentials or timestamps.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def recipe_revision(root: Path | None = None) -> str:
    """Hash compiler modules, serving proof rules and the locked dependency input.

    New compiler and runtime modules participate automatically, including helpers
    introduced by later fixes. Tests, generated data and local configuration do
    not form part of the recipe.
    """
    root = root or Path(__file__).resolve().parents[1]
    paths = {
        *root.joinpath("index").rglob("*.py"),
        *root.joinpath("src/linker_genie").rglob("*.py"),
        *root.joinpath("ops").rglob("*.py"),
        root / "pyproject.toml",
        root / "uv.lock",
    }
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        name = path.relative_to(root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()
