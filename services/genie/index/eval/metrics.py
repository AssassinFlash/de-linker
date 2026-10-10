"""Scoring one search result list against a golden question.

- recall@k: one of the top k chunks lies on a gold page (document sha256 + physical
  page) of the question.
- citation page accuracy: of the questions whose top k contain a chunk from a gold
  document that carries the gold quote, the share where the first such chunk - the one
  an answer would cite for that quote - lies on the gold page. It checks the page
  every citation shows, separately from whether retrieval found the page.

A quote is found in a chunk when its words appear in order within one line of the
chunk or two adjacent lines (a table row is a line; the card's rule for table quotes is
"the printed row label plus the value, in the order the page prints them", which may
skip the other models' columns in between).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from index.eval.goldset import Evidence
from linker_genie.retrieval import DocumentHit

_WORD = re.compile(r"[^\W_]+")
_FOLD = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def words(text: str) -> list[str]:
    """Lower-case words and numbers, NFKC-folded; punctuation separates them."""
    return _WORD.findall(unicodedata.normalize("NFKC", text).translate(_FOLD).lower())


def _in_order(needle: Sequence[str], haystack: Sequence[str]) -> bool:
    position = 0
    for word in haystack:
        if position < len(needle) and word == needle[position]:
            position += 1
    return position == len(needle)


def quote_in(quote: str, text: str) -> bool:
    """Whether the quote's words appear in order within one or two adjacent lines."""
    needle = words(quote)
    if not needle:
        return False
    lines = text.split("\n")
    for index, line in enumerate(lines):
        window = line if index + 1 == len(lines) else f"{line} {lines[index + 1]}"
        if _in_order(needle, words(window)):
            return True
    return False


@dataclass(frozen=True)
class Score:
    """One question's outcome."""

    rank: int | None
    cited_page_correct: bool | None


def score(hits: Sequence[DocumentHit], evidence: Sequence[Evidence]) -> Score:
    """Rank of the first chunk on a gold page, and whether the cited page is right."""
    gold_pages = {(item.doc_sha256, item.page) for item in evidence}
    rank = next(
        (
            position
            for position, hit in enumerate(hits, start=1)
            if (hit.doc_sha256, hit.page) in gold_pages
        ),
        None,
    )
    cited: bool | None = None
    for hit in hits:
        quotes = [item for item in evidence if item.doc_sha256 == hit.doc_sha256]
        if any(quote_in(item.quote, hit.text) for item in quotes):
            cited = (hit.doc_sha256, hit.page) in gold_pages
            break
    return Score(rank=rank, cited_page_correct=cited)
