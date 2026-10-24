"""The embedding model's tokenizer, for counting and cutting chunks in its own tokens."""

from __future__ import annotations

import hashlib

from tokenizers import Tokenizer

# The actual chunk tokenizer cached on the build Mac, measured 2026-10-24.
# Pin both its upstream commit and canonical tokenizers serialization so a moving
# repository default cannot silently change an already acknowledged recipe.
CHUNK_TOKENIZER = "BAAI/bge-m3"
CHUNK_TOKENIZER_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
CHUNK_TOKENIZER_SHA256 = (
    "dfbf70c4aa4fadbbc57a9f23f38b8c94d6c0aeb75e526b695564d559902ec69a"
)


class HFTokenizer:
    """A Hugging Face `tokenizers` tokenizer behind the chunker's Tokenizer protocol."""

    def __init__(self, tokenizer: Tokenizer) -> None:
        self._tokenizer = tokenizer

    @classmethod
    def from_pretrained(cls, repo: str) -> HFTokenizer:
        """Load the measured immutable chunk tokenizer, refusing changed bytes."""
        if repo != CHUNK_TOKENIZER:
            raise ValueError("knowledge builds require the pinned chunk tokenizer")
        tokenizer = Tokenizer.from_pretrained(repo, revision=CHUNK_TOKENIZER_REVISION)
        if (
            hashlib.sha256(tokenizer.to_str().encode()).hexdigest()
            != CHUNK_TOKENIZER_SHA256
        ):
            raise ValueError("chunk tokenizer differs from the preparation recipe")
        return cls(tokenizer)

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
