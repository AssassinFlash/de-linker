"""Measured immutable serving release identity, independent of index metadata."""

from __future__ import annotations

import hashlib
from pathlib import Path


def serving_revision(root: Path | None = None) -> str:
    """Hash actual runtime source and dependency inputs in a complete service release.

    Native deployments ship the full service root and create an editable locked
    virtualenv there. Neither its host path nor its environment enters this hash.
    """
    root = root or Path(__file__).resolve().parents[2]
    paths = {
        # The independent quality worker consumes completed turns, not this
        # process's knowledge. Keep its delivery lifecycle out of serving proof.
        *(
            path
            for path in root.joinpath("src/linker_genie").rglob("*.py")
            if not path.is_relative_to(root / "src/linker_genie/quality")
        ),
        root / "pyproject.toml",
        root / "uv.lock",
    }
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        name, content = path.relative_to(root).as_posix().encode(), path.read_bytes()
        digest.update(len(name).to_bytes(8, "big") + name)
        digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


# Captured at process import/startup, never read from SQLite or remeasured after
# an index switch. Deployment releases are immutable; an old process keeps its
# old identity even if a new current symlink/index has already been published.
RUNTIME_SERVING_REVISION = serving_revision()
