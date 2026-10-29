"""Request-scoped reuse is bounded and never serves unverified bytes."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import pytest

from linker_engine.planning.canonical import encode
from linker_engine.planning.errors import VersionUnavailable
from linker_engine.planning.frozen_documents import FrozenDocuments
from linker_engine.planning.storage import Blobs


class Counting:
    """A `Blobs` that records how often each hash was actually read."""

    def __init__(self, blobs: Blobs) -> None:
        self.blobs = blobs
        self.reads: list[str] = []

    def read(self, sha256: str) -> bytes:
        self.reads.append(sha256)
        return self.blobs.read(sha256)

    def object(self, sha256: str) -> NoReturn:  # pragma: no cover - unused
        raise AssertionError("the reader must verify through read")


def test_one_document_is_read_and_parsed_once_per_request(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    content = encode(
        {"schema_version": 1, "kind": "retained", "values": list(range(8))}
    )
    sha = blobs.put(content)
    counting = Counting(blobs)
    documents = FrozenDocuments(counting)  # type: ignore[arg-type]
    for _ in range(3):
        assert documents.object(sha) == documents.object(sha)
    assert counting.reads == [sha]
    assert documents.parses == 1


def test_a_different_document_is_still_read(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    first = blobs.put(encode({"schema_version": 1, "kind": "one"}))
    second = blobs.put(encode({"schema_version": 1, "kind": "two"}))
    counting = Counting(blobs)
    documents = FrozenDocuments(counting)  # type: ignore[arg-type]
    assert documents.object(first)["kind"] == "one"
    assert documents.object(second)["kind"] == "two"
    assert counting.reads == [first, second]


def test_bounds_fall_back_to_a_plain_read_rather_than_evicting(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    first = blobs.put(encode({"schema_version": 1, "kind": "one"}))
    second = blobs.put(encode({"schema_version": 1, "kind": "two"}))
    counting = Counting(blobs)
    documents = FrozenDocuments(counting, max_documents=1)  # type: ignore[arg-type]
    documents.object(first)
    documents.object(second)
    # The resident entry stayed and the refused one is simply read again.
    documents.object(first)
    documents.object(second)
    assert counting.reads == [first, second, second]


def test_byte_bound_keeps_results_correct(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    payload = encode({"schema_version": 1, "kind": "big", "values": list(range(64))})
    sha = blobs.put(payload)
    counting = Counting(blobs)
    documents = FrozenDocuments(counting, max_bytes=1)  # type: ignore[arg-type]
    assert documents.object(sha)["kind"] == "big"
    assert documents.object(sha)["kind"] == "big"
    assert counting.reads == [sha, sha]


def test_unverified_bytes_are_never_reused(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    sha = blobs.put(encode({"schema_version": 1, "kind": "one"}))
    documents = FrozenDocuments(blobs)
    assert documents.object(sha)["kind"] == "one"
    stored = blobs.directory / sha[:2] / sha
    stored.write_bytes(encode({"schema_version": 1, "kind": "tampered"}))
    # The retained reader keeps the verified result for this request, and a new
    # request fails closed on the changed bytes instead of returning either.
    assert documents.object(sha)["kind"] == "one"
    with pytest.raises(VersionUnavailable):
        FrozenDocuments(blobs).object(sha)


def test_bounds_must_be_positive(tmp_path: Path) -> None:
    blobs = Blobs(tmp_path / "blobs")
    with pytest.raises(ValueError):
        FrozenDocuments(blobs, max_documents=0)
    with pytest.raises(ValueError):
        FrozenDocuments(blobs, max_bytes=0)
