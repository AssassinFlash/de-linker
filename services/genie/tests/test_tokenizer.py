"""HFTokenizer: counting and cutting in a real `tokenizers` tokenizer."""

from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

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
