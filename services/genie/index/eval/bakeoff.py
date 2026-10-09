"""Embedding bake-off: every candidate on the same golden set, chunks and fusion.

`python -m index.eval.bakeoff --index MODEL=PATH ... [--images] [--page-text MODEL]`
scores page rankings (a chunk ranking becomes a page ranking by each page's first
appearance; page-image and page-text rankings are pages already), so text, image and
fused settings compare on one unit:
- recall@5 and @10: a gold page among the first 5 / 10 pages;
- page accuracy: of the questions whose first 5 pages include a page of a gold
  document carrying the gold quote, the share where the first such page is a gold page
  (index.eval.metrics, applied to a page's chunk text);
- the same per language and for the figure questions.
Every fusion is reciprocal rank fusion with RETRIEVAL's k, of the rankings named in the
setting. Query vectors are computed once per model and question and timed.
docs/research/2026-10-09/embedding-bakeoff.md holds the results and the decision.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import numpy.typing as npt

from index.eval.goldset import GOLDEN_PATH, Question, load
from index.eval.metrics import quote_in
from index.eval.run import product_ids_by_model
from index.pages import PAGE_VECTORS
from linker_genie.embedding import GEMINI, Embedder, GeminiEmbedder, gemini_from_env
from linker_genie.retrieval import CANDIDATES, DocumentIndex, rrf

# Queries timed one by one for an API model; the rest are fetched in batches. 50 is the
# sample the VPS encoder benchmark times (index.eval.encoder_bench).
TIMED_API_QUERIES = 50

PageKey = tuple[str, int]
Ranking = list[PageKey]


@dataclass
class Pages:
    """The chunks of one index grouped by page."""

    of_rowid: dict[int, PageKey]
    text: dict[PageKey, str]

    @classmethod
    def read(cls, path: Path) -> Pages:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            of_rowid: dict[int, PageKey] = {}
            text: dict[PageKey, list[str]] = {}
            for rowid, sha, page, body in db.execute(
                "SELECT rowid, doc_sha256, page, text FROM chunks ORDER BY rowid"
            ):
                of_rowid[rowid] = (sha, page)
                text.setdefault((sha, page), []).append(body)
            return cls(of_rowid, {key: "\n".join(parts) for key, parts in text.items()})
        finally:
            db.close()

    def ranking(self, rowids: Sequence[int]) -> Ranking:
        """Pages in the order their first chunk appears."""
        return list(dict.fromkeys(self.of_rowid[rowid] for rowid in rowids))


class Matrix:
    """Page vectors searched exhaustively (pages, not chunks: page images, page text)."""

    def __init__(self, keys: list[PageKey], vectors: npt.NDArray[np.float32]) -> None:
        self.keys = keys
        self.vectors = vectors

    @classmethod
    def from_store(cls, path: Path) -> Matrix:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "SELECT doc_sha256, page, vector FROM pages ORDER BY doc_sha256, page"
            ).fetchall()
        finally:
            db.close()
        vectors = np.stack([np.frombuffer(row[2], dtype="<f4") for row in rows])
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        return cls([(row[0], row[1]) for row in rows], vectors.astype(np.float32))

    def ranking(self, query: bytes, documents: set[str] | None = None) -> Ranking:
        """The CANDIDATES nearest pages, among `documents` when given."""
        scores = self.vectors @ np.frombuffer(query, dtype="<f4")
        if documents is not None:
            allowed = np.array([key[0] in documents for key in self.keys])
            scores = np.where(allowed, scores, -np.inf)
        best = [
            index
            for index in np.argsort(-scores)[:CANDIDATES]
            if np.isfinite(scores[index])
        ]
        return [self.keys[index] for index in best]


@dataclass
class Score:
    rank: int | None
    cited_ok: bool | None


def score(ranking: Ranking, question: Question, pages: Pages) -> Score:
    gold = {(item.doc_sha256, item.page) for item in question.evidence}
    rank = next(
        (position for position, key in enumerate(ranking, start=1) if key in gold), None
    )
    cited: bool | None = None
    for key in ranking[:5]:
        quotes = [item.quote for item in question.evidence if item.doc_sha256 == key[0]]
        if any(quote_in(quote, pages.text.get(key, "")) for quote in quotes):
            cited = key in gold
            break
    return Score(rank, cited)


@dataclass
class Row:
    setting: str
    scores: dict[str, Score] = field(default_factory=dict)

    def subset(
        self, questions: Sequence[Question], keep: Callable[[Question], bool]
    ) -> dict[str, float | int]:
        chosen = [self.scores[question.id] for question in questions if keep(question)]
        cited = [item.cited_ok for item in chosen if item.cited_ok is not None]
        n = len(chosen)
        return {
            "n": n,
            "recall@5": sum(
                1 for item in chosen if item.rank is not None and item.rank <= 5
            )
            / n
            if n
            else 0.0,
            "recall@10": sum(
                1 for item in chosen if item.rank is not None and item.rank <= 10
            )
            / n
            if n
            else 0.0,
            "cited": len(cited),
            "page_accuracy": sum(cited) / len(cited) if cited else 0.0,
        }


class Encoders:
    """Query vectors per model, computed once and timed."""

    def __init__(self) -> None:
        self.vectors: dict[tuple[str, str], bytes] = {}
        self.seconds: dict[str, list[float]] = {}

    def encode(self, encoder: Embedder, text: str) -> bytes:
        key = (encoder.model, text)
        if key not in self.vectors:
            started = time.perf_counter()
            self.vectors[key] = encoder.embed_query(text)
            self.seconds.setdefault(encoder.model, []).append(
                time.perf_counter() - started
            )
        return self.vectors[key]

    def prefill(
        self, encoder: GeminiEmbedder, texts: Sequence[str], timed: int
    ) -> None:
        """An API model: time `timed` single queries, fetch the rest in batched requests."""
        for text in texts[:timed]:
            self.encode(encoder, text)
        rest = [text for text in texts if (encoder.model, text) not in self.vectors]
        for text, vector in zip(rest, encoder.embed_queries(rest), strict=True):
            self.vectors[(encoder.model, text)] = vector

    def latency(self) -> dict[str, dict[str, float]]:
        out = {}
        for model, values in self.seconds.items():
            ordered = sorted(values)
            out[model] = {
                "p50_ms": round(statistics.median(ordered) * 1000, 1),
                "p95_ms": round(
                    ordered[max(0, round(0.95 * len(ordered)) - 1)] * 1000, 1
                ),
            }
        return out


class Scopes:
    """What a question may retrieve: the whole library, or with --by-product the
    documents of the products that sell its model (the search's own narrowing)."""

    def __init__(self, base: DocumentIndex, pages: Pages, by_product: bool) -> None:
        self.base = base
        self.pages = pages
        self.products = product_ids_by_model(base.path) if by_product else {}
        self._rowids: dict[str, list[int] | None] = {}

    def rowids(self, question: Question) -> list[int] | None:
        if question.model not in self._rowids:
            ids = self.products.get(question.model.casefold())
            self._rowids[question.model] = self.base.scope(ids, None) if ids else None
        return self._rowids[question.model]

    def documents(self, question: Question) -> set[str] | None:
        rowids = self.rowids(question)
        return (
            None
            if rowids is None
            else {self.pages.of_rowid[rowid][0] for rowid in rowids}
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the embedding bake-off.")
    parser.add_argument(
        "--index",
        action="append",
        default=[],
        metavar="MODEL=PATH",
        help="a built index per text model",
    )
    parser.add_argument(
        "--images", action="store_true", help="add the gemini page-image ranking"
    )
    parser.add_argument(
        "--page-text",
        type=Path,
        metavar="STORE",
        help="page-text vector store (index.eval.page_vectors)",
    )
    parser.add_argument(
        "--by-product",
        action="store_true",
        help="narrow each question to its model's products",
    )
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    questions = load(args.golden)
    indexes = {
        model: Path(path) for model, path in (item.split("=", 1) for item in args.index)
    }
    base = DocumentIndex(next(iter(indexes.values())), encoder=None)
    pages = Pages.read(base.path)
    scopes = Scopes(base, pages, args.by_product)
    encoders = Encoders()
    rankings: dict[str, dict[str, Ranking]] = {}

    def rank(name: str, make: Callable[[Question], Ranking]) -> None:
        rankings[name] = {question.id: make(question) for question in questions}
        print(f"ranked: {name}", file=sys.stderr, flush=True)

    rank(
        "BM25",
        lambda q: pages.ranking(base.keyword_ranking(q.question, scopes.rowids(q))),
    )
    texts = list(dict.fromkeys(question.question for question in questions))
    for model, path in indexes.items():
        index = DocumentIndex(path)
        if isinstance(index.encoder, GeminiEmbedder):
            encoders.prefill(index.encoder, texts, TIMED_API_QUERIES)
        rank(f"dense {model}", dense_ranker(index, pages, encoders, scopes))
    if args.images:
        gemini = gemini_from_env()
        if gemini is None:
            raise SystemExit("--images needs AIHUBMIX_API_KEY and AIHUBMIX_BASE_URL")
        encoders.prefill(gemini, texts, TIMED_API_QUERIES)
        images = Matrix.from_store(PAGE_VECTORS)
        rank(f"{GEMINI} page images", matrix_ranker(images, gemini, encoders, scopes))
    if args.page_text:
        model = json.loads(args.page_text.with_suffix(".json").read_text())["model"]
        encoder = DocumentIndex(indexes[model]).encoder
        if encoder is None:
            raise SystemExit(f"{model}: no query encoder on this machine")
        text_pages = Matrix.from_store(args.page_text)
        rank(
            f"OCR page text {model}",
            matrix_ranker(text_pages, encoder, encoders, scopes),
        )

    settings: list[tuple[str, list[str]]] = [("BM25", ["BM25"])]
    for model in indexes:
        settings.append((f"dense {model}", [f"dense {model}"]))
        settings.append((f"BM25 + {model}", ["BM25", f"dense {model}"]))
    extra = [
        name
        for name in rankings
        if name.endswith("page images") or name.startswith("OCR page text")
    ]
    for name in extra:
        settings.append((name, [name]))
        for model in indexes:
            settings.append(
                (f"BM25 + {model} + {name}", ["BM25", f"dense {model}", name])
            )

    rows = []
    for name, parts in settings:
        row = Row(name)
        for question in questions:
            ranked = fuse([rankings[part][question.id] for part in parts])
            row.scores[question.id] = score(ranked, question, pages)
        rows.append(row)

    english = english_documents(base.path)

    def german_on_english(question: Question) -> bool:
        return question.lang == "de" and all(
            item.doc_sha256 in english for item in question.evidence
        )

    report = {
        "questions": len(questions),
        "by_product": args.by_product,
        "figure_questions": sum(
            1 for question in questions if question.kind == "figure"
        ),
        "query_latency_mac": encoders.latency(),
        "rows": [
            {
                "setting": row.setting,
                "all": row.subset(questions, lambda q: True),
                "en": row.subset(questions, lambda q: q.lang == "en"),
                "de": row.subset(questions, lambda q: q.lang == "de"),
                "de_question_en_document": row.subset(questions, german_on_english),
                "figure": row.subset(questions, lambda q: q.kind == "figure"),
            }
            for row in rows
        ],
    }
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    for row in report["rows"]:
        overall = row["all"]
        print(
            f"{row['setting']}: recall@5 {overall['recall@5']:.3f} "
            f"recall@10 {overall['recall@10']:.3f} page {overall['page_accuracy']:.3f}"
        )
    return 0


def english_documents(path: Path) -> set[str]:
    """Documents whose language, as the index records it, is English."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {
            row[0]
            for row in db.execute("SELECT sha256 FROM documents WHERE lang = 'en'")
        }
    finally:
        db.close()


def dense_ranker(
    index: DocumentIndex, pages: Pages, encoders: Encoders, scopes: Scopes
) -> Callable[[Question], Ranking]:
    """Pages of the chunks nearest to the question in one model's index."""
    encoder = index.encoder
    if encoder is None:
        raise SystemExit(f"{index.embedding_model}: no query encoder on this machine")

    def ranking(question: Question) -> Ranking:
        vector = encoders.encode(encoder, question.question)
        return pages.ranking(
            index.vector_ranking(question.question, scopes.rowids(question), vector)
        )

    return ranking


def matrix_ranker(
    matrix: Matrix, encoder: Embedder, encoders: Encoders, scopes: Scopes
) -> Callable[[Question], Ranking]:
    """Pages nearest to the question among page vectors (images or page text)."""

    def ranking(question: Question) -> Ranking:
        return matrix.ranking(
            encoders.encode(encoder, question.question), scopes.documents(question)
        )

    return ranking


def fuse(rankings: Sequence[Ranking]) -> Ranking:
    """Reciprocal rank fusion of page rankings (one ranking passes through unchanged)."""
    if len(rankings) == 1:
        return list(rankings[0])
    ids: dict[PageKey, int] = {}
    numbered = [
        [ids.setdefault(key, len(ids)) for key in ranking] for ranking in rankings
    ]
    keys = {number: key for key, number in ids.items()}
    return [keys[number] for number, _ in rrf(numbered)]


if __name__ == "__main__":
    sys.exit(main())
