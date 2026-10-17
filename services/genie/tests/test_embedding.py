"""Embedding models: request formats and vector packing, without network or weights."""

import io
import json
import pathlib
import struct
import sys
import types
import urllib.error
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from linker_genie import embedding
from linker_genie.embedding import (
    ARCTIC_M,
    E5_SMALL,
    GEMINI_BATCH,
    OPEN_MODELS,
    QUERY_ATTEMPTS,
    QUERY_TIMEOUT,
    EmbeddingError,
    GeminiEmbedder,
    OnnxEmbedder,
    Passage,
    pack,
    query_encoder,
)


class FakeApi:
    """Answers OpenAI-compatible /v1/embeddings requests with one-hot vectors."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    @contextmanager
    def __call__(self, request: Any, timeout: float) -> Iterator[io.BytesIO]:
        body = json.loads(request.data)
        self.requests.append(
            {"url": request.full_url, "auth": request.headers["Authorization"], **body}
        )
        data = [
            {"index": i, "embedding": [float(i), 1.0]}
            for i in range(len(body["input"]))
        ]
        yield io.BytesIO(
            json.dumps(
                {"data": list(reversed(data)), "usage": {"total_tokens": 7}}
            ).encode()
        )


def test_pack_writes_float32_little_endian() -> None:
    assert pack([1.0, -2.5]) == struct.pack("<2f", 1.0, -2.5)


def test_gemini_documents_carry_title_and_text_and_go_in_batches_of_100() -> None:
    api = FakeApi()
    gemini = GeminiEmbedder("secret", "https://aihubmix.example/", urlopen=api)
    passages = [
        Passage(title="ET datasheet", text=f"chunk {i}")
        for i in range(GEMINI_BATCH + 1)
    ]

    vectors = gemini.embed_documents(passages)

    assert [len(request["input"]) for request in api.requests] == [GEMINI_BATCH, 1]
    assert api.requests[0]["input"][0] == "title: ET datasheet | text: chunk 0"
    assert api.requests[0]["url"] == "https://aihubmix.example/v1/embeddings"
    assert api.requests[0]["auth"] == "Bearer secret"
    assert api.requests[0]["model"] == "gemini-embedding-2"
    assert vectors[1] == pack([1.0, 1.0])  # re-ordered by the response's index
    assert gemini.tokens == 14


def test_gemini_queries_carry_the_question_answering_task() -> None:
    api = FakeApi()

    GeminiEmbedder("secret", "https://aihubmix.example", urlopen=api).embed_query(
        "Wie schwer ist der GW10K-ET?"
    )

    assert api.requests[0]["input"] == [
        "task: question answering | query: Wie schwer ist der GW10K-ET?"
    ]


def test_a_document_without_title_is_marked_none() -> None:
    api = FakeApi()

    GeminiEmbedder("k", "https://a.example", urlopen=api).embed_documents(
        [Passage(title="", text="t")]
    )

    assert api.requests[0]["input"] == ["title: none | text: t"]


class FailingApi:
    """Fails every request with `error`; counts the requests and their timeouts."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.timeouts: list[float] = []

    @contextmanager
    def __call__(self, request: Any, timeout: float) -> Iterator[io.BytesIO]:
        self.timeouts.append(timeout)
        raise self.error
        yield io.BytesIO()  # pragma: no cover - never reached


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://a.example", code, "x", {}, None)  # type: ignore[arg-type]


def test_a_query_that_never_encodes_raises_after_its_attempts() -> None:
    api = FailingApi(urllib.error.URLError("proxy 503"))
    waits: list[float] = []
    encoder = GeminiEmbedder("k", "https://a.example", urlopen=api, sleep=waits.append)

    with pytest.raises(EmbeddingError, match=f"after {QUERY_ATTEMPTS} attempts"):
        encoder.embed_query("How many MPPT?")

    assert api.timeouts == [QUERY_TIMEOUT] * QUERY_ATTEMPTS
    assert waits == [0.5 * 2**n for n in range(QUERY_ATTEMPTS - 1)]
    assert QUERY_ATTEMPTS >= 2


@pytest.mark.parametrize("code", [429, 502, 503])
def test_a_throttled_or_failing_endpoint_is_tried_again(code: int) -> None:
    api = FailingApi(_http_error(code))

    with pytest.raises(EmbeddingError, match=f"HTTP {code}"):
        GeminiEmbedder(
            "k", "https://a.example", urlopen=api, sleep=lambda _: None
        ).embed_query("q")

    assert len(api.timeouts) == QUERY_ATTEMPTS


@pytest.mark.parametrize("code", [400, 401, 404])
def test_a_refused_request_fails_at_once(code: int) -> None:
    api = FailingApi(_http_error(code))

    with pytest.raises(EmbeddingError, match=f"HTTP {code} on attempt 1"):
        GeminiEmbedder(
            "k", "https://a.example", urlopen=api, sleep=lambda _: None
        ).embed_query("q")

    assert len(api.timeouts) == 1


def test_an_answer_without_vectors_fails_at_once() -> None:
    class EmptyApi:
        calls = 0

        @contextmanager
        def __call__(self, request: Any, timeout: float) -> Iterator[io.BytesIO]:
            EmptyApi.calls += 1
            yield io.BytesIO(json.dumps({"error": "no data"}).encode())

    with pytest.raises(EmbeddingError, match="unexpected response"):
        GeminiEmbedder("k", "https://a.example", urlopen=EmptyApi()).embed_query("q")

    assert EmptyApi.calls == 1


def test_gemini_retries_once_on_a_transport_error() -> None:
    class FlakyApi:
        def __init__(self) -> None:
            self.calls = 0

        @contextmanager
        def __call__(self, request: Any, timeout: float) -> Iterator[io.BytesIO]:
            self.calls += 1
            if self.calls == 1:
                raise urllib.error.URLError("proxy 503")
            yield io.BytesIO(
                json.dumps({"data": [{"index": 0, "embedding": [1.0]}]}).encode()
            )

    api = FlakyApi()

    vector = GeminiEmbedder(
        "k", "https://a.example", urlopen=api, sleep=lambda _: None
    ).embed_query("q")

    assert api.calls == 2
    assert vector == pack([1.0])


class FakeSession:
    """Stands in for onnxruntime.InferenceSession: hidden states from the token count."""

    outputs = ("last_hidden_state",)

    def __init__(self, path: str, options: Any, providers: list[str]) -> None:
        self.options = options

    def get_inputs(self) -> list[Any]:
        return [
            types.SimpleNamespace(name=name) for name in ("input_ids", "attention_mask")
        ]

    def get_outputs(self) -> list[Any]:
        return [types.SimpleNamespace(name=name) for name in self.outputs]

    def run(self, names: object, feed: dict[str, Any]) -> list[Any]:
        import numpy as np

        batch, length = feed["input_ids"].shape
        # Token i of every row is the vector (i + 1, 1): CLS = (1, 1); the mean depends
        # on how many tokens the mask keeps.
        hidden = np.stack([np.arange(1, length + 1), np.ones(length)], axis=1)
        return [np.repeat(hidden[None, :, :], batch, axis=0).astype("float32")]


@pytest.fixture
def onnx_model(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> list[Any]:
    from tokenizers import Tokenizer
    from tokenizers.models import WordLevel
    from tokenizers.pre_tokenizers import Whitespace

    words = [
        "[PAD]",
        "[UNK]",
        "query",
        ":",
        "passage",
        "how",
        "heavy",
        "is",
        "it",
        "a",
        "b",
    ]
    tokenizer = Tokenizer(
        WordLevel({word: i for i, word in enumerate(words)}, unk_token="[UNK]")
    )
    tokenizer.pre_tokenizer = Whitespace()
    tokenizer.save(str(tmp_path / "tokenizer.json"))
    sessions: list[Any] = []

    class Options:
        def __init__(self) -> None:
            self.entries: dict[str, str] = {}

        def add_session_config_entry(self, key: str, value: str) -> None:
            self.entries[key] = value

    def session(path: str, options: Any, providers: list[str]) -> FakeSession:
        created = FakeSession(path, options, providers)
        sessions.append(created)
        return created

    module = types.ModuleType("onnxruntime")
    module.__dict__.update(
        SessionOptions=Options,
        ExecutionMode=types.SimpleNamespace(ORT_SEQUENTIAL="sequential"),
        InferenceSession=session,
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", module)
    monkeypatch.setattr(
        "huggingface_hub.hf_hub_download",
        lambda repo, filename, revision: str(tmp_path / "tokenizer.json"),
    )
    return sessions


def test_the_vps_query_encoder_runs_one_thread_without_spinning(
    onnx_model: list[Any],
) -> None:
    OnnxEmbedder(OPEN_MODELS[E5_SMALL])

    options = onnx_model[0].options
    assert (options.intra_op_num_threads, options.inter_op_num_threads) == (1, 1)
    assert options.entries == {
        "session.intra_op.allow_spinning": "0",
        "session.inter_op.allow_spinning": "0",
    }


def test_cls_pooling_takes_the_first_token_and_normalizes(
    onnx_model: list[Any],
) -> None:
    import numpy as np

    vector = np.frombuffer(
        OnnxEmbedder(OPEN_MODELS[ARCTIC_M]).embed_query("how heavy is it"), "<f4"
    )

    assert vector == pytest.approx(np.array([1, 1]) / np.sqrt(2))


def test_mean_pooling_averages_the_tokens_the_mask_keeps(onnx_model: list[Any]) -> None:
    import numpy as np

    e5 = OnnxEmbedder(OPEN_MODELS[E5_SMALL])
    # "query : a" -> 3 tokens: mean of (1,1), (2,1), (3,1) = (2, 1); in a batch with a
    # longer passage the padding must not count.
    short, longer = e5.embed_documents([Passage("t", "a"), Passage("t", "a b a b")])

    assert np.frombuffer(short, "<f4") == pytest.approx(np.array([2, 1]) / np.sqrt(5))
    assert np.frombuffer(longer, "<f4") == pytest.approx(
        np.array([3.5, 1]) / np.sqrt(13.25)
    )


def test_without_a_key_there_is_no_gemini_query_encoder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # No OpenRouter credentials anywhere: no key in the process env and no
    # credentials file (the owner's real file must not leak into tests).
    monkeypatch.delenv("AIHUBMIX_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(embedding, "_OPENROUTER_FILE", tmp_path / "absent.env")

    assert query_encoder("gemini-embedding-2") is None


def test_the_gemini_encoder_defaults_to_openrouter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LINKER_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("AIHUBMIX_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
    monkeypatch.setattr(embedding, "_OPENROUTER_FILE", tmp_path / "absent.env")

    encoder = query_encoder("gemini-embedding-2")

    assert isinstance(encoder, embedding.GeminiEmbedder)
    assert encoder.model == "google/gemini-embedding-2"
    assert encoder._url == "https://openrouter.ai/api/v1/embeddings"
    assert encoder.fingerprint["model"] == "gemini-embedding-2"


def test_aihubmix_serves_only_behind_the_explicit_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_EMBEDDING_PROVIDER", "aihubmix")
    monkeypatch.setenv("AIHUBMIX_API_KEY", "k")
    monkeypatch.setenv("AIHUBMIX_BASE_URL", "https://aihubmix.example")

    encoder = query_encoder("gemini-embedding-2")

    assert isinstance(encoder, embedding.GeminiEmbedder)
    assert encoder.model == "gemini-embedding-2"
    assert encoder._url == "https://aihubmix.example/v1/embeddings"


def test_an_unknown_model_has_no_query_encoder() -> None:
    assert query_encoder("voyage-4") is None


def test_an_openrouter_base_already_carries_v1() -> None:
    api = FakeApi()

    GeminiEmbedder("k", "https://openrouter.example/api/v1/", urlopen=api).embed_query(
        "q"
    )

    assert api.requests[0]["url"] == "https://openrouter.example/api/v1/embeddings"


def _write_env(path: pathlib.Path, *lines: str) -> pathlib.Path:
    path.write_text("\n".join(lines) + "\n")
    return path


def test_credentials_read_the_owner_file_when_the_env_has_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # index.eval.rerank reads the DeepSeek escalation key through this helper:
    # the environment first, the owner's file second (the 401 the file fixes).
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    found = embedding.credentials(
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com",
        _write_env(tmp_path / "deepseek.env", "DEEPSEEK_API_KEY=file-key"),
    )

    assert found == ("https://api.deepseek.com", "file-key")
