"""Refresh safe projections from the preserved original warranty corpus."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from test_chunking import Words
from test_publication import authority

from index.chunking import Chunk
from index.publication import ScopeProof, compile_publication


def warranty_current_fixture() -> tuple[
    dict[str, Any], list[Chunk], list[Chunk], dict[str, ScopeProof]
]:
    path = (
        Path(__file__).parent / "fixtures/publication-compiler/warranty-current.json.gz"
    )
    data = json.loads(gzip.decompress(path.read_bytes()))
    raw = data["manifest"]
    raw["model_identity_revision"] = "fixture-identity-1"
    scopes: dict[str, ScopeProof] = data["scopes"]
    for scope in scopes.values():
        scope["model_identity_revision"] = raw["model_identity_revision"]
    original = [Chunk(**item) for item in data["original"]]
    compiled = [Chunk(**item) for item in data["compiled"]]

    # Old captured projections include truncated values that the current
    # validator correctly rejects. Recompile from the unchanged native rows.
    fresh, fresh_scopes = compile_publication(original, raw, authority(raw), Words())
    existing = {chunk.id for chunk in compiled}
    for chunk in fresh:
        scope = fresh_scopes.get(chunk.id)
        if chunk.id not in existing and scope and scope["basis"] == "table_projection":
            compiled.append(chunk)
            scopes[chunk.id] = scope
            existing.add(chunk.id)
    return raw, original, compiled, scopes
