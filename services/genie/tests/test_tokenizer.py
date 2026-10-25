"""HFTokenizer: counting and cutting in a real `tokenizers` tokenizer."""

import hashlib
from typing import Any

import pytest
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from index import tokenizer as chunk_tokenizer
from index.tokenizer import HFTokenizer


def words_tokenizer(text: str) -> HFTokenizer:
    vocab = {
        word: index for index, word in enumerate(sorted(set(text.split())) + ["[UNK]"])
    }
    tokenizer = Tokenizer(WordLevel(vocab, unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    return HFTokenizer(tokenizer)


def test_count_is_the_number_of_tokens() -> None:
    sample = "Max Input Power 15 kW"

    assert words_tokenizer(sample).count(sample) == 5


def test_a_text_within_the_limit_stays_whole() -> None:
    sample = "Max Input Power 15 kW"

    assert words_tokenizer(sample).split(sample, 5) == [sample]


def test_a_long_text_is_cut_at_spaces_into_pieces_within_the_limit() -> None:
    sample = " ".join(f"word{i}" for i in range(23))
    tokenizer = words_tokenizer(sample)

    pieces = tokenizer.split(sample, 5)

    assert all(tokenizer.count(piece) <= 5 for piece in pieces)
    assert " ".join(pieces) == sample


def test_build_loads_the_immutable_tokenizer_pin_and_checks_actual_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = words_tokenizer("AC rated power 25000 W")._tokenizer
    calls = []

    class LocalTokenizer:
        @staticmethod
        def from_pretrained(repo: str, **kwargs: Any) -> Tokenizer:
            calls.append((repo, kwargs))
            return actual

    monkeypatch.setattr(chunk_tokenizer, "Tokenizer", LocalTokenizer)
    monkeypatch.setattr(
        chunk_tokenizer,
        "CHUNK_TOKENIZER_SHA256",
        hashlib.sha256(actual.to_str().encode()).hexdigest(),
    )
    assert (
        HFTokenizer.from_pretrained(chunk_tokenizer.CHUNK_TOKENIZER).count(
            "AC rated power"
        )
        == 3
    )
    assert calls == [
        (
            chunk_tokenizer.CHUNK_TOKENIZER,
            {"revision": chunk_tokenizer.CHUNK_TOKENIZER_REVISION},
        )
    ]
    monkeypatch.setattr(chunk_tokenizer, "CHUNK_TOKENIZER_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="preparation recipe"):
        HFTokenizer.from_pretrained(chunk_tokenizer.CHUNK_TOKENIZER)
