"""Embedding models of the document index.

One model encodes the chunks when the index is built and the queries when it is
searched; the index records the model's name, and `query_encoder` returns the matching
query encoder, or None when this host cannot run it. Every model embeds the same
chunks; each formats them as its model card or documentation prescribes.

- Open models (`OPEN_MODELS`) run their ONNX export through ONNX Runtime: the build
  embeds chunks on the Mac with all cores, the VPS encodes queries with one thread and
  no spinning (1 vCPU shared with the engine, no PyTorch there; owner, 2026-10-09).
- `gemini-embedding-2` through AIHubMix's OpenAI-compatible `/v1/embeddings`
  (AIHUBMIX_API_KEY, AIHUBMIX_BASE_URL), for chunks and queries alike.
docs/research/2026-10-09/embedding-bakeoff.md compares them.

Vectors travel as float32 little-endian bytes, the form sqlite-vec stores.
"""

from __future__ import annotations

import json
import os
import struct
import threading
import urllib.request
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

ARCTIC_M = "Snowflake/snowflake-arctic-embed-m-v2.0"
E5_SMALL = "intfloat/multilingual-e5-small"
E5_BASE = "intfloat/multilingual-e5-base"
BGE_M3 = "BAAI/bge-m3"
GEMINI = "gemini-embedding-2"


@dataclass(frozen=True)
class Passage:
    """A chunk as an embedding model sees it: its document's title and its text."""

    title: str
    text: str


class Embedder(Protocol):
    """A model that turns passages and queries into comparable vectors."""

    @property
    def model(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        """One vector per passage, for storing."""
        ...

    def embed_query(self, text: str) -> bytes:
        """The vector a query is searched with."""
        ...


def pack(vector: Sequence[float]) -> bytes:
    """A vector as float32 little-endian bytes."""
    return struct.pack(f"<{len(vector)}f", *vector)


@dataclass(frozen=True)
class OpenModel:
    """An open-weight model: its input format, its int8 ONNX export and pooling."""

    name: str
    revision: str
    dimensions: int
    query_prefix: str
    passage_prefix: str
    onnx_file: str
    tokenizer_file: str
    # How the ONNX graph's output becomes the sentence vector: `cls` (first token),
    # `mean` (mask-weighted mean), or `sentence_embedding` (an output already pooled).
    pooling: str
    # Files the ONNX graph loads from beside itself (external weights).
    onnx_data: tuple[str, ...] = ()


# Facts from each model card and Hugging Face file list, read 2026-10-09 (Apify):
# arctic-embed-m-v2.0: 768 dimensions, CLS pooling, "query: " on queries only, official
#   int8 ONNX `onnx/model_int8.onnx`.
# multilingual-e5-small / -base: 384 / 768 dimensions, mean pooling, every input starts
#   with "query: " or "passage: ", official `onnx/model_qint8_avx512_vnni.onnx`.
# BGE-M3: 1024 dimensions, "no longer requires adding instructions to the queries";
#   its official ONNX export is fp32 only and already pools (`sentence_embedding`).
# Revisions are the repositories' commits on that date, so a rebuild reads the same files.
OPEN_MODELS = {
    ARCTIC_M: OpenModel(
        ARCTIC_M,
        "95c2741480856aa9666782eb4afe11959938017f",
        768,
        "query: ",
        "",
        "onnx/model_int8.onnx",
        "tokenizer.json",
        "cls",
    ),
    E5_SMALL: OpenModel(
        E5_SMALL,
        "614241f622f53c4eeff9890bdc4f31cfecc418b3",
        384,
        "query: ",
        "passage: ",
        "onnx/model_qint8_avx512_vnni.onnx",
        "onnx/tokenizer.json",
        "mean",
    ),
    E5_BASE: OpenModel(
        E5_BASE,
        "d128750597153bb5987e10b1c3493a34e5a4502a",
        768,
        "query: ",
        "passage: ",
        "onnx/model_qint8_avx512_vnni.onnx",
        "onnx/tokenizer.json",
        "mean",
    ),
    BGE_M3: OpenModel(
        BGE_M3,
        "5617a9f61b028005a4858fdac845db406aefb181",
        1024,
        "",
        "",
        "onnx/model.onnx",
        "onnx/tokenizer.json",
        "sentence_embedding",
        onnx_data=("onnx/model.onnx_data", "onnx/Constant_7_attr__value"),
    ),
}
# XLM-RoBERTa position limit of e5 ("Long texts will be truncated to at most 512
# tokens", e5 model card). Chunks are cut to 512 XLM-R tokens with their header, so
# only a model prefix can push one past it; the cut then drops the last few tokens.
MAX_TOKENS = 512
# Chunks per ONNX Runtime call when the build embeds documents.
ONNX_BATCH = 16


class OnnxEmbedder:
    """An open model's ONNX export through ONNX Runtime.

    `threads=1` is the VPS query encoder: one intra-op thread, no inter-op parallelism
    and no spinning, so it never holds the single vCPU the engine also needs (owner,
    2026-10-09). The build passes all of the Mac's cores. Files come from the Hugging
    Face cache at the pinned revision (HF_HOME decides where), downloaded on first use.
    """

    def __init__(self, spec: OpenModel, threads: int = 1) -> None:
        import onnxruntime
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        self.spec = spec

        def fetch(filename: str) -> str:
            return str(hf_hub_download(spec.name, filename, revision=spec.revision))

        for filename in spec.onnx_data:
            fetch(filename)
        self._tokenizer = Tokenizer.from_file(fetch(spec.tokenizer_file))
        self._tokenizer.enable_truncation(MAX_TOKENS)
        # Batches are padded with the model's own pad token (XLM-RoBERTa's `<pad>`).
        pad = self._tokenizer.token_to_id("<pad>")
        if pad is None:
            self._tokenizer.enable_padding()
        else:
            self._tokenizer.enable_padding(pad_id=pad, pad_token="<pad>")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        options.add_session_config_entry("session.inter_op.allow_spinning", "0")
        self._session = onnxruntime.InferenceSession(
            fetch(spec.onnx_file), options, providers=["CPUExecutionProvider"]
        )
        self._inputs = {item.name for item in self._session.get_inputs()}
        self._outputs = [item.name for item in self._session.get_outputs()]

    @property
    def model(self) -> str:
        return self.spec.name

    @property
    def dimensions(self) -> int:
        return self.spec.dimensions

    def _vectors(self, texts: Sequence[str]) -> list[bytes]:
        import numpy as np

        encodings = self._tokenizer.encode_batch(list(texts))
        ids = np.array([encoding.ids for encoding in encodings], dtype=np.int64)
        mask = np.array(
            [encoding.attention_mask for encoding in encodings], dtype=np.int64
        )
        feed = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._inputs:
            feed["token_type_ids"] = np.zeros_like(ids)
        result = dict(zip(self._outputs, self._session.run(None, feed), strict=True))
        if self.spec.pooling == "sentence_embedding":
            vectors = result["sentence_embedding"]
        elif self.spec.pooling == "cls":
            vectors = result[self._outputs[0]][:, 0]
        else:
            hidden = result[self._outputs[0]]
            vectors = (hidden * mask[:, :, None]).sum(axis=1) / mask.sum(axis=1)[
                :, None
            ]
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        return [bytes(row.astype("<f4").tobytes()) for row in vectors]

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        texts = [self.spec.passage_prefix + passage.text for passage in passages]
        vectors: list[bytes] = []
        for start in range(0, len(texts), ONNX_BATCH):
            vectors.extend(self._vectors(texts[start : start + ONNX_BATCH]))
        return vectors

    def embed_query(self, text: str) -> bytes:
        return self._vectors([self.spec.query_prefix + text])[0]


UrlOpen = Callable[..., Any]

# gemini-embedding-2: 3072 dimensions by default (Gemini embeddings guide); the API
# rejects more than 100 inputs per request ("at most 100 requests can be in one batch",
# AIHubMix error, 2026-10-09). Task formats from the guide's asymmetric retrieval table:
# queries "task: question answering | query: {content}", documents
# "title: {title} | text: {content}".
GEMINI_DIMENSIONS = 3072
GEMINI_BATCH = 100
# Requests in flight while embedding many texts. One request takes about 4 s through
# AIHubMix (measured 2026-10-09); four keep a corpus build to minutes.
GEMINI_WORKERS = 4


class GeminiEmbedder:
    """gemini-embedding-2 through AIHubMix's OpenAI-compatible endpoint."""

    model = GEMINI
    dimensions = GEMINI_DIMENSIONS

    def __init__(
        self, api_key: str, base_url: str, urlopen: UrlOpen = urllib.request.urlopen
    ) -> None:
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/v1/embeddings"
        self._urlopen = urlopen
        self._lock = threading.Lock()
        self.tokens = 0

    def _embed(self, texts: Sequence[str]) -> list[bytes]:
        request = urllib.request.Request(
            self._url,
            data=json.dumps({"model": self.model, "input": list(texts)}).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        with self._urlopen(request, timeout=300) as response:
            payload = json.load(response)
        rows = sorted(payload["data"], key=lambda row: int(row["index"]))
        if len(rows) != len(texts):
            raise RuntimeError(
                f"{self.model} returned {len(rows)} embeddings for {len(texts)} texts"
            )
        with self._lock:
            self.tokens += int(payload.get("usage", {}).get("total_tokens", 0))
        return [pack([float(value) for value in row["embedding"]]) for row in rows]

    def _embed_all(self, texts: Sequence[str]) -> list[bytes]:
        batches = [
            texts[start : start + GEMINI_BATCH]
            for start in range(0, len(texts), GEMINI_BATCH)
        ]
        with ThreadPoolExecutor(max_workers=GEMINI_WORKERS) as pool:
            return [
                vector
                for vectors in pool.map(self._embed, batches)
                for vector in vectors
            ]

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        return self._embed_all(
            [
                f"title: {passage.title or 'none'} | text: {passage.text}"
                for passage in passages
            ]
        )

    def embed_queries(self, texts: Sequence[str]) -> list[bytes]:
        """Many queries in batched requests (the bake-off encodes its golden set)."""
        return self._embed_all(
            [f"task: question answering | query: {text}" for text in texts]
        )

    def embed_query(self, text: str) -> bytes:
        return self._embed([f"task: question answering | query: {text}"])[0]


def gemini_from_env() -> GeminiEmbedder | None:
    key = os.environ.get("AIHUBMIX_API_KEY", "")
    base = os.environ.get("AIHUBMIX_BASE_URL", "")
    return GeminiEmbedder(key, base) if key and base else None


MODELS = (*OPEN_MODELS, GEMINI)


def query_encoder(model: str) -> Embedder | None:
    """The query encoder for an index built with `model`, if this host can run it."""
    try:
        if model in OPEN_MODELS:
            return OnnxEmbedder(OPEN_MODELS[model])
        if model == GEMINI:
            return gemini_from_env()
    except ImportError:
        return None
    return None
