"""BGE-M3 through sentence-transformers on the build Mac's GPU: the bake-off's control.

Its official ONNX export is fp32 only (2.3 GB). Embedding the corpus with it on the
CPU is out of reach and it does not fit the VPS budget either (fp32: p95 254 ms, RSS
1.5 GB; self-quantized int8: RSS 1.1 GB, docs/research/2026-10-09/embedding-bakeoff.md),
so the bake-off encodes both chunks and queries with PyTorch here.
"""

from __future__ import annotations

from collections.abc import Sequence

from linker_genie.embedding import OpenModel, Passage

# Passages per encode call: sentence-transformers' default batch size.
BATCH = 32


class LocalEmbedder:
    """An open model run with sentence-transformers (PyTorch; MPS on the Mac)."""

    def __init__(self, spec: OpenModel) -> None:
        from sentence_transformers import SentenceTransformer

        self.spec = spec
        self._model = SentenceTransformer(spec.name, revision=spec.revision)

    @property
    def model(self) -> str:
        return self.spec.name

    @property
    def dimensions(self) -> int:
        return self.spec.dimensions

    @property
    def fingerprint(self) -> dict[str, str]:
        return {
            "model": self.spec.name,
            "revision": self.spec.revision,
            "backend": "sentence-transformers",
            "dimensions": str(self.spec.dimensions),
        }

    def _encode(self, texts: Sequence[str]) -> list[bytes]:
        vectors = self._model.encode(
            list(texts),
            batch_size=BATCH,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return [bytes(row.astype("<f4").tobytes()) for row in vectors]

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        return self._encode(
            [self.spec.passage_prefix + passage.text for passage in passages]
        )

    def embed_query(self, text: str) -> bytes:
        return self._encode([self.spec.query_prefix + text])[0]
