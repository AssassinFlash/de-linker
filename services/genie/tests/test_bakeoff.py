"""Bake-off scoring on pages: chunk rankings become page rankings, fusion, filters."""

import numpy as np

from index.eval.bakeoff import Matrix, Pages, fuse, score
from index.eval.goldset import Evidence, Question

A, B = "a" * 64, "b" * 64


def question(*gold: tuple[str, int, str]) -> Question:
    evidence = [Evidence(sha, page, quote, "m1") for sha, page, quote in gold]
    return Question(
        "q-en", "en", "q?", "GoodWe", "GW10K-ET", "EL-10", "text", "15 kW", evidence
    )


PAGES = Pages(
    of_rowid={1: (A, 1), 2: (A, 1), 3: (A, 2), 4: (B, 7)},
    text={
        (A, 1): "intro",
        (A, 2): "| Max. Input Power (kW) | 15 |",
        (B, 7): "Max. Input Power (kW) 15",
    },
)


def test_a_chunk_ranking_becomes_pages_in_order_of_first_appearance() -> None:
    assert PAGES.ranking([2, 1, 4, 3]) == [(A, 1), (B, 7), (A, 2)]


def test_fusion_of_one_ranking_is_that_ranking() -> None:
    assert fuse([[(A, 2), (A, 1)]]) == [(A, 2), (A, 1)]


def test_fusion_ranks_pages_found_by_both_rankings_first() -> None:
    assert fuse([[(A, 1), (A, 2)], [(B, 7), (A, 2)]])[0] == (A, 2)


def test_score_reports_rank_and_the_cited_pages_correctness() -> None:
    result = score(
        [(B, 7), (A, 1), (A, 2)], question((A, 2, "Max. Input Power (kW) 15")), PAGES
    )

    assert result.rank == 3
    assert (
        result.cited_ok is True
    )  # p.7 of B carries the quote but B is no gold document


def test_matrix_ranking_keeps_to_the_allowed_documents() -> None:
    vectors = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]], dtype=np.float32)
    matrix = Matrix(
        [(A, 1), (B, 2), (B, 3)],
        vectors / np.linalg.norm(vectors, axis=1, keepdims=True),
    )
    query = np.array([1.0, 0.0], dtype="<f4").tobytes()

    assert matrix.ranking(query)[:2] == [(A, 1), (B, 2)]
    assert matrix.ranking(query, documents={B}) == [(B, 2), (B, 3)]
