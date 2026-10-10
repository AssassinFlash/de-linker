"""The embedding model's tokenizer, for counting and cutting chunks in its own tokens."""

from __future__ import annotations

from tokenizers import Tokenizer


class HFTokenizer:
    """A Hugging Face `tokenizers` tokenizer behind the chunker's Tokenizer protocol."""

    def __init__(self, tokenizer: Tokenizer) -> None:
        self._tokenizer = tokenizer

    @classmethod
    def from_pretrained(cls, repo: str) -> HFTokenizer:
        """The tokenizer published with a model on the Hugging Face hub."""
        return cls(Tokenizer.from_pretrained(repo))

    def count(self, text: str) -> int:
        return len(self._tokenizer.encode(text, add_special_tokens=False).ids)

    def split(self, text: str, max_tokens: int) -> list[str]:
        """Pieces of at most `max_tokens` tokens, cut at a space where one is in reach."""
        offsets = self._tokenizer.encode(text, add_special_tokens=False).offsets
        if len(offsets) <= max_tokens:
            return [text]
        pieces = []
        start = 0
        token = 0
        while token < len(offsets):
            last = min(token + max_tokens, len(offsets)) - 1
            end = len(text) if last == len(offsets) - 1 else offsets[last][1]
            space = text.rfind(" ", start + 1, end + 1)
            if end < len(text) and space > start:
                end = space
            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)
            start = end
            while token < len(offsets) and offsets[token][0] < end:
                token += 1
        return pieces
