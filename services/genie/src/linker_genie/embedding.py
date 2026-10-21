"""Embedding models of the document index.

One model encodes the chunks when the index is built and the queries when it is
searched; the index records the model's name, and `query_encoder` returns the matching
query encoder, or None when this host cannot run it. Every model embeds the same
chunks; each formats them as its model card or documentation prescribes.

- Open models (`OPEN_MODELS`) run their ONNX export through ONNX Runtime: the build
  embeds chunks on the Mac with all cores, the VPS encodes queries with one thread and
  no spinning (1 vCPU shared with the engine, no PyTorch there; owner, 2026-10-09).
- `gemini-embedding-2` through an OpenAI-compatible `/v1/embeddings`: OpenRouter
  by default (OPENROUTER_API_KEY, OPENROUTER_BASE_URL — the owner's model routing
  law of 2026-10-11); AIHubMix only behind the explicit
  `LINKER_EMBEDDING_PROVIDER=aihubmix` switch (AIHUBMIX_API_KEY,
  AIHUBMIX_BASE_URL), never as an automatic fallback. One client embeds chunks
  and queries alike. Keys come from the environment or the owner's files under
  ~/.config/terravolt-builder/ and never enter the repository.
docs/research/2026-10-09/embedding-bakeoff.md compares the models.

Vectors travel as float32 little-endian bytes, the form sqlite-vec stores.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from linker_judges.budget import take

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

    @property
    def fingerprint(self) -> dict[str, str]:
        """What makes two encoders produce the same vectors; the index records it."""
        ...

    def embed_documents(self, passages: Sequence[Passage]) -> list[bytes]:
        """One vector per passage, for storing."""
        ...

    def embed_query(self, text: str) -> bytes:
        """The vector a query is searched with."""
        ...


def sha256_of(path: str | Path) -> str:
    """A file's sha256, in streaming blocks; the index build reuses it for its files."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


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
        onnx_path = fetch(spec.onnx_file)
        tokenizer_path = fetch(spec.tokenizer_file)
        self._fingerprint = {
            "model": spec.name,
            "revision": spec.revision,
            "onnx_file": spec.onnx_file,
            "onnx_sha256": sha256_of(onnx_path),
            "tokenizer_sha256": sha256_of(tokenizer_path),
            "query_prefix": spec.query_prefix,
            "passage_prefix": spec.passage_prefix,
            "pooling": spec.pooling,
            "dimensions": str(spec.dimensions),
        }
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
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
            onnx_path, options, providers=["CPUExecutionProvider"]
        )
        self._inputs = {item.name for item in self._session.get_inputs()}
        self._outputs = [item.name for item in self._session.get_outputs()]

    @property
    def model(self) -> str:
        return self.spec.name

    @property
    def dimensions(self) -> int:
        return self.spec.dimensions

    @property
    def fingerprint(self) -> dict[str, str]:
        return dict(self._fingerprint)

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
        # Batches of similar length waste less on padding; the order is restored after.
        order = sorted(range(len(texts)), key=lambda index: len(texts[index]))
        vectors: list[bytes] = [b""] * len(texts)
        for start in range(0, len(order), ONNX_BATCH):
            batch = order[start : start + ONNX_BATCH]
            for index, vector in zip(
                batch, self._vectors([texts[index] for index in batch]), strict=True
            ):
                vectors[index] = vector
        return vectors

    def embed_query(self, text: str) -> bytes:
        return self._vectors([self.spec.query_prefix + text])[0]


UrlOpen = Callable[..., Any]


class EmbeddingError(RuntimeError):
    """The embedding endpoint did not return vectors after every attempt.

    Raised, never swallowed: the model routing law of 2026-10-11 forbids a silent
    fallback when OpenRouter fails, so a search whose query cannot be encoded fails
    with this error instead of ranking by keywords.

    `failure_kind` is the class the turn records (#410). The message is for
    the log. A new sentence is still a retrieval failure.
    """

    failure_kind = "retrieval"


# Fragments of the sentences `GeminiEmbedder._embed` raises. The raises
# below include them, and `sentence_is_encoder_failure` reads them, so a
# probe that only kept the message still names an encoder failure. The
# turn does not need this when it still has the exception.
_UNEXPECTED = "unexpected response ("
_COUNT_FOR = " embeddings for "
_HTTP_ON_ATTEMPT = "HTTP "
_ON_ATTEMPT = " on attempt "
_AFTER_ATTEMPTS = " after "
_ATTEMPTS = " attempts"


def sentence_is_encoder_failure(text: str) -> bool:
    """True when `text` is a sentence `_embed` raises.

    Used only after the exception type has been lost (#410). An
    `EmbeddingError` is retrieval with any message.
    """
    if _UNEXPECTED in text or _COUNT_FOR in text:
        return True
    if _HTTP_ON_ATTEMPT in text and _ON_ATTEMPT in text:
        return True
    return (
        _AFTER_ATTEMPTS in text
        and _ATTEMPTS in text
        and any(
            name in text for name in ("URLError", "TimeoutError", "ConnectionError")
        )
    )


# gemini-embedding-2: 3072 dimensions by default (Gemini embeddings guide); the API
# rejects more than 100 inputs per request ("at most 100 requests can be in one batch",
# AIHubMix error, 2026-10-09). Task formats from the guide's asymmetric retrieval table:
# queries "task: question answering | query: {content}", documents
# "title: {title} | text: {content}".
GEMINI_DIMENSIONS = 3072
GEMINI_BATCH = 100
# A query is encoded while a customer waits. OpenRouter encodes one in 0.46 s median,
# 0.83 s at most from the VPS, and 3.8 s median, 5.35 s at most from the Mac
# (12 requests each, measured 2026-10-17, issue #257), so an attempt may take 10 s.
# Two attempts with 0.5 s between them end within 20.5 s; a failed turn searches
# twice (cycle.run retries the generation once), 41 s, inside the shell's 60 s
# proxy budget for the whole turn. A third attempt would pass it (63 s).
QUERY_TIMEOUT = 10.0
QUERY_ATTEMPTS = 2
QUERY_BACKOFF = 0.5
# A corpus build waits for big batches: one request of 100 chunks takes about 4 s
# through AIHubMix (measured 2026-10-09) and the build has no customer waiting, so a
# request may take minutes; one retry has covered every endpoint blip of a build.
BUILD_TIMEOUT = 300.0
BUILD_ATTEMPTS = 2
# Requests in flight while embedding many texts. One request takes about 4 s through
# AIHubMix (measured 2026-10-09); four keep a corpus build to minutes.
GEMINI_WORKERS = 4


class GeminiEmbedder:
    """gemini-embedding-2 through an OpenAI-compatible endpoint.

    OpenRouter (the default) names the model google/gemini-embedding-2; the
    fingerprint below keeps the bake-off's provider-neutral name because the
    index was built with it and the fingerprint check compares names.
    """

    model = GEMINI
    dimensions = GEMINI_DIMENSIONS
    fingerprint = {
        "model": GEMINI,
        "dimensions": str(GEMINI_DIMENSIONS),
        "query_format": "task: question answering | query: {text}",
        "document_format": "title: {title} | text: {text}",
    }

    def __init__(
        self,
        api_key: str,
        base_url: str,
        urlopen: UrlOpen = urllib.request.urlopen,
        model: str = GEMINI,
        # The clock of the query retry backoff; injected so tests need no waiting.
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self.model = model
        # Bases may carry their own /v1 (OpenRouter does); keep exactly one.
        stem = base_url.rstrip("/").removesuffix("/v1")
        self._url = stem + "/v1/embeddings"
        self._urlopen = urlopen
        self._sleep = sleep
        self._lock = threading.Lock()
        self.tokens = 0

    def _embed(
        self,
        texts: Sequence[str],
        timeout: float = BUILD_TIMEOUT,
        attempts: int = BUILD_ATTEMPTS,
        backoff: float = 0.0,
        runtime: bool = False,
    ) -> list[bytes]:
        """Vectors of `texts`, or EmbeddingError once every attempt has failed.

        A transport error, a timeout, a 429 or a 5xx is tried again; any other HTTP
        error and an answer without the right vectors are final at once.
        """
        request = urllib.request.Request(
            self._url,
            data=json.dumps({"model": self.model, "input": list(texts)}).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        for attempt in range(1, attempts + 1):
            if runtime:
                take("embedding")
            try:
                with self._urlopen(request, timeout=timeout) as response:
                    payload = json.load(response)
                rows = sorted(payload["data"], key=lambda row: int(row["index"]))
                vectors = [
                    pack([float(value) for value in row["embedding"]]) for row in rows
                ]
            except urllib.error.HTTPError as error:
                if (error.code != 429 and error.code < 500) or attempt == attempts:
                    raise EmbeddingError(
                        f"{self.model}: {_HTTP_ON_ATTEMPT}{error.code}{_ON_ATTEMPT}"
                        f"{attempt} of {attempts}"
                    ) from error
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                if attempt == attempts:
                    raise EmbeddingError(
                        f"{self.model}: {type(error).__name__}{_AFTER_ATTEMPTS}"
                        f"{attempts}{_ATTEMPTS}: {error}"
                    ) from error
            except (ValueError, KeyError, TypeError) as error:
                raise EmbeddingError(
                    f"{self.model}: {_UNEXPECTED}{type(error).__name__}: {error})"
                ) from error
            else:
                if len(vectors) != len(texts):
                    raise EmbeddingError(
                        f"{self.model} returned {len(vectors)}{_COUNT_FOR}"
                        f"{len(texts)} texts"
                    )
                with self._lock:
                    self.tokens += int(payload.get("usage", {}).get("total_tokens", 0))
                return vectors
            if backoff:
                self._sleep(backoff * 2 ** (attempt - 1))
        raise EmbeddingError(f"{self.model}: no attempt was made")

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
        """One query, on the customer's clock: QUERY_TIMEOUT, QUERY_ATTEMPTS."""
        return self._embed(
            [f"task: question answering | query: {text}"],
            timeout=QUERY_TIMEOUT,
            attempts=QUERY_ATTEMPTS,
            backoff=QUERY_BACKOFF,
            runtime=True,
        )[0]


_OPENROUTER_FILE = Path("~/.config/terravolt-builder/openrouter.env").expanduser()
# The escalation endpoint's key file, same rule as the file above; read by
# whoever calls DeepSeek (index.eval.rerank) through `credentials` below.
DEEPSEEK_FILE = Path("~/.config/terravolt-builder/deepseek.env").expanduser()


def _load_openrouter_env() -> None:
    """The owner's OpenRouter credentials, when the process env has none."""
    if not _OPENROUTER_FILE.exists():
        return
    for line in _OPENROUTER_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, value = line.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip("\"'"))


def credentials(
    env_key: str, env_base: str, default_base: str, file: Path
) -> tuple[str, str] | None:
    """(base URL, key) from the environment, else from the owner's file; None when
    neither has a key."""
    values = dict(os.environ)
    if env_key not in values and file.exists():
        for line in file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                name = name.strip().removeprefix("export ").strip()
                values.setdefault(name, value.strip().strip("'\""))
    key = values.get(env_key, "")
    if not key:
        return None
    return values.get(env_base, default_base).rstrip("/"), key


def gemini_from_env() -> GeminiEmbedder | None:
    """The gemini encoder per the model routing law: OpenRouter by default.

    AIHubMix serves only behind LINKER_EMBEDDING_PROVIDER=aihubmix - an explicit
    manual switch, never an automatic fallback (owner 2026-10-11).
    """
    if os.environ.get("LINKER_EMBEDDING_PROVIDER", "") == "aihubmix":
        key = os.environ.get("AIHUBMIX_API_KEY", "")
        base = os.environ.get("AIHUBMIX_BASE_URL", "")
        return GeminiEmbedder(key, base) if key and base else None
    _load_openrouter_env()
    key = os.environ.get("OPENROUTER_API_KEY", "")
    base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return GeminiEmbedder(key, base, model="google/gemini-embedding-2") if key else None


MODELS = (*OPEN_MODELS, GEMINI)


def query_encoder(model: str) -> Embedder | None:
    """The query encoder for an index built with `model`, if this host can run it.

    BGE-M3's build encoder is sentence-transformers (`index.local_model.LocalEmbedder`,
    the bake-off's control): the same class must encode its queries, or the index's
    fingerprint check rejects the session. It needs PyTorch, so a host without the
    `index` dependency group - the VPS - has no BGE-M3 encoder and searches it by
    keywords only.
    """
    try:
        if model == BGE_M3:
            from index.local_model import LocalEmbedder

            return LocalEmbedder(OPEN_MODELS[BGE_M3])
        if model in OPEN_MODELS:
            return OnnxEmbedder(OPEN_MODELS[model])
        if model == GEMINI:
            return gemini_from_env()
    except ImportError:
        return None
    return None
