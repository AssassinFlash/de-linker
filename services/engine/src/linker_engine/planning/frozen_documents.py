"""Request-scoped reuse of hash-verified frozen bytes and documents, bounded.

A single report request reads the same large model witness for the profile, the
component list, the array rows and the dependency list; the manifest check even
reads every dependency once more. Re-reading those bytes per consumer is pure
overhead, so one reader is shared across that request.

It is deliberately not a process cache: nothing outlives the request, there is
no age or key invalidation to reason about, and every cached entry was already
verified by `Blobs.read` before it was kept. Both bounds fall back to a plain
read rather than evicting, so one oversized document cannot make this grow
without limit or displace the artifact a later consumer needs.

A retained object is shared by every consumer of the request, so callers must
treat it as immutable: read fields, never edit the returned mapping.
"""

from __future__ import annotations

from typing import Protocol

from .canonical import Object, decode_object, encode
from .storage import Blobs

# Request working-set ceiling, not an industry standard. One report in this
# batch read a 24×8760 witness 11 times, 34.3 MiB in total. 32 documents is
# that observed set plus margin for the inputs, weather metadata, Woo basis,
# geometry and project parameters of a few references.
DEFAULT_MAX_DOCUMENTS = 32
# Same measurement: 34.3 MiB across those 11 reads. 96 MiB is that observed
# request working set plus margin, not a second cache tier.
DEFAULT_MAX_BYTES = 96 * 1024 * 1024


class FrozenReader(Protocol):
    """The read surface a verified retained document is reached through.

    Both `Blobs` and `FrozenDocuments` satisfy it, so a reader that already
    verified an artifact can be handed to a consumer typed against plain
    storage instead of each consumer opening the store again.
    """

    def read(self, sha256: str) -> bytes: ...

    def object(self, sha256: str) -> Object: ...


class FrozenDocuments:
    def __init__(
        self,
        blobs: Blobs,
        *,
        max_documents: int = DEFAULT_MAX_DOCUMENTS,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        if max_documents < 1 or max_bytes < 1:
            raise ValueError("frozen document bounds must be positive")
        self.blobs = blobs
        self.max_documents = max_documents
        self.max_bytes = max_bytes
        self._content: dict[str, bytes] = {}
        self._objects: dict[str, Object] = {}
        self._geometric_projections: dict[str, Object] = {}
        self._bytes = 0
        # Verified parses kept for this request; the regression asserts a
        # report parses each retained document once.
        self.parses = 0

    def read(self, sha256: str) -> bytes:
        cached = self._content.get(sha256)
        if cached is not None:
            return cached
        content = self.blobs.read(sha256)
        self._keep(sha256, content)
        return content

    def object(self, sha256: str) -> Object:
        cached = self._objects.get(sha256)
        if cached is not None:
            return cached
        value = decode_object(self.read(sha256))
        self.parses += 1
        if sha256 in self._content:
            # Both bounds apply to the parsed form too; a document that was not
            # retained as bytes must not be retained as an object either.
            self._objects[sha256] = value
        return value

    def geometric_witness(self, blobs: Blobs, sha256: str) -> Object:
        """Reuse a verified small projection when a full witness exceeds the cap."""
        cached = self._geometric_projections.get(sha256)
        if cached is not None:
            return cached
        from .geometric_pv_witness import project_witness

        value = project_witness(blobs, sha256)
        size = len(encode(value))
        self.parses += 1
        if (
            len(self._content) + len(self._geometric_projections) < self.max_documents
            and self._bytes + size <= self.max_bytes
        ):
            self._geometric_projections[sha256] = value
            self._bytes += size
        return value

    def _keep(self, sha256: str, content: bytes) -> None:
        if (
            len(self._content) + len(self._geometric_projections) < self.max_documents
            and self._bytes + len(content) <= self.max_bytes
        ):
            self._content[sha256] = content
            self._bytes += len(content)
