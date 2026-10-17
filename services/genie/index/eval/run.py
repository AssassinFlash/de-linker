"""Evaluation (`just eval`): recall@5 and citation page accuracy of the golden set.

Runs every golden question against a built index: the production path first (by
product: narrowed to the products that sell the question's model, vectors when the
index has them), then the whole library, then keywords only. Prints a Markdown table
and writes `eval.json` next to the index. Fails when a vector setting falls below
the recorded baseline (`BASELINE`, docs/specs/10-knowledge-index.md 验收 (a)), and says
by how much.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from index.eval.goldset import GOLDEN_PATH, Question, load
from index.eval.metrics import Score, score
from index.paths import INDEX_DIR
from linker_genie.embedding import GeminiEmbedder
from linker_genie.retrieval import DocumentIndex

RECALL_AT = 5
# The no-regression gate (docs/specs/10-knowledge-index.md 验收 (a)): setting ->
# (recall@5, citation page accuracy) that a build may not fall below. Measured on
# index 20261016T072222Z with the 984-question golden set, issue #257
# (docs/acceptance/2026-10-17/257/golden-eval.md): found 540 and 541 of 984, cited
# page right for 419 of 507 and 422 of 504. Raise it when a build does better;
# never lower it without a ruling.
BASELINE: dict[str, tuple[float, float]] = {
    "vectors, by product": (540 / 984, 419 / 507),
    "vectors, whole library": (541 / 984, 422 / 504),
}


@dataclass
class Summary:
    """The scores of one setting, overall and per language."""

    setting: str
    questions: int
    recall: float
    mrr: float
    cited: int
    page_accuracy: float
    per_lang: dict[str, tuple[int, float, float]]


def summarize(
    setting: str, questions: Sequence[Question], scores: Sequence[Score]
) -> Summary:
    def part(
        items: Sequence[tuple[Question, Score]],
    ) -> tuple[int, float, float, int, float]:
        n = len(items)
        found = sum(1 for _, item in items if item.rank is not None)
        mrr = sum(1 / item.rank for _, item in items if item.rank is not None)
        cited = [
            item.cited_page_correct
            for _, item in items
            if item.cited_page_correct is not None
        ]
        return (
            n,
            found / n if n else 0.0,
            mrr / n if n else 0.0,
            len(cited),
            (sum(cited) / len(cited) if cited else 0.0),
        )

    pairs = list(zip(questions, scores, strict=True))
    n, recall, mrr, cited, accuracy = part(pairs)
    per_lang = {}
    for lang in sorted({question.lang for question in questions}):
        lang_n, lang_recall, _, _, lang_accuracy = part(
            [pair for pair in pairs if pair[0].lang == lang]
        )
        per_lang[lang] = (lang_n, lang_recall, lang_accuracy)
    return Summary(setting, n, recall, mrr, cited, accuracy, per_lang)


def regressions(
    summaries: Sequence[Summary],
    baseline: dict[str, tuple[float, float]] = BASELINE,
) -> list[str]:
    """One line per baseline setting that was not measured or fell below its floor.

    Equal to the baseline passes: the evaluation is deterministic for one index and
    golden set (docs/acceptance/2026-10-11/16i/), so a rerun reproduces it exactly.
    """
    measured = {summary.setting: summary for summary in summaries}
    lines = []
    for setting, (recall, accuracy) in baseline.items():
        summary = measured.get(setting)
        if summary is None:
            lines.append(f"{setting}: not measured (baseline is set for it)")
            continue
        for name, value, floor in (
            ("recall@5", summary.recall, recall),
            ("citation page accuracy", summary.page_accuracy, accuracy),
        ):
            if value < floor:
                lines.append(
                    f"{setting}: {name} {value:.1%} is below the baseline "
                    f"{floor:.1%} by {(floor - value) * 100:.1f} points"
                )
    return lines


def against_baseline(
    summaries: Sequence[Summary],
    baseline: dict[str, tuple[float, float]] = BASELINE,
) -> list[str]:
    """Each baseline setting's figures beside its floor, with the difference."""
    measured = {summary.setting: summary for summary in summaries}
    lines = []
    for setting, (recall, accuracy) in baseline.items():
        summary = measured.get(setting)
        if summary is not None:
            lines.append(
                f"{setting}: recall@5 {summary.recall:.1%} (baseline {recall:.1%}, "
                f"{(summary.recall - recall) * 100:+.1f}), citation page accuracy "
                f"{summary.page_accuracy:.1%} (baseline {accuracy:.1%}, "
                f"{(summary.page_accuracy - accuracy) * 100:+.1f})"
            )
    return lines


def product_ids_by_model(index_path: Path) -> dict[str, list[int]]:
    """Model designation (case-folded) -> IDs of the products that sell it."""
    db = sqlite3.connect(f"file:{index_path}?mode=ro", uri=True)
    try:
        found: dict[str, list[int]] = {}
        for product_id, model in db.execute("SELECT product_id, model FROM products"):
            found.setdefault(str(model).casefold(), []).append(int(product_id))
        return found
    finally:
        db.close()


def evaluate(
    index: DocumentIndex,
    questions: Sequence[Question],
    products: dict[str, list[int]] | None,
) -> list[Score]:
    # An API encoder encodes the whole golden set in batched requests (a minute)
    # instead of one request per question (an hour); local encoders stay per query.
    vectors: dict[str, bytes] = {}
    if isinstance(index.encoder, GeminiEmbedder):
        texts = list(dict.fromkeys(question.question for question in questions))
        print(f"encoding {len(texts)} queries in batches…", file=sys.stderr, flush=True)
        vectors = dict(zip(texts, index.encoder.embed_queries(texts), strict=True))
    scores = []
    for question in questions:
        ids = products.get(question.model.casefold()) if products is not None else None
        hits = index.search(
            question.question,
            question.lang,
            product_ids=ids,
            k=RECALL_AT,
            query_vector=vectors.get(question.question),
            # The ranking alone: neighbours follow their hit and would count as
            # ranks past k (retrieval.with_page_neighbours).
            neighbours=False,
        )
        scores.append(score(hits, question.evidence))
    return scores


def table(summaries: Sequence[Summary]) -> str:
    lines = [
        "| Setting | Questions | Recall@5 | MRR@5 | Cited | Page accuracy | Recall@5 EN / DE | Page accuracy EN / DE |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in summaries:
        en, de = (
            item.per_lang.get("en", (0, 0.0, 0.0)),
            item.per_lang.get("de", (0, 0.0, 0.0)),
        )
        lines.append(
            f"| {item.setting} | {item.questions} | {item.recall:.1%} | {item.mrr:.3f} | {item.cited} "
            f"| {item.page_accuracy:.1%} | {en[1]:.1%} / {de[1]:.1%} | {en[2]:.1%} / {de[2]:.1%} |"
        )
    return "\n".join(lines)


def latest_build(root: Path = INDEX_DIR) -> Path:
    builds = sorted((root / "builds").glob("*/index.sqlite"))
    if not builds:
        raise FileNotFoundError(
            f"no built index under {root / 'builds'}; run `just index`"
        )
    return builds[-1]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate a built index on the golden set."
    )
    parser.add_argument(
        "--index", type=Path, default=None, help="index.sqlite (default: latest build)"
    )
    parser.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    args = parser.parse_args(argv)
    index_path = args.index or latest_build()
    questions = load(args.golden)
    products = product_ids_by_model(index_path)
    hybrid = DocumentIndex(index_path)
    keyword = DocumentIndex(index_path, encoder=None)
    # The production path first: Genie asks about a model it has resolved to products
    # (docs/specs/13-genie.md, linker/search-knowledge takes product_ids), so the search
    # narrows to those products' documents; with vectors when the index has them.
    mode, index = (
        ("vectors", hybrid) if hybrid.encoder is not None else ("keywords", keyword)
    )
    settings = [
        (f"{mode}, by product", index, products),
        (f"{mode}, whole library", index, None),
    ]
    if hybrid.encoder is not None:
        settings += [
            ("keywords, by product", keyword, products),
            ("keywords, whole library", keyword, None),
        ]
    summaries = []
    for name, index, by_product in settings:
        summaries.append(
            summarize(name, questions, evaluate(index, questions, by_product))
        )
        print(f"{name}: done", file=sys.stderr, flush=True)
    scoped = sum(1 for question in questions if question.model.casefold() in products)
    report = table(summaries)
    print(
        f"Index {hybrid.version} ({hybrid.embedding_model}); golden set {len(questions)} questions, "
        f"{scoped} with products for their model.\n"
    )
    print(report)
    (index_path.parent / "eval.json").write_text(
        json.dumps([summary.__dict__ for summary in summaries], indent=1),
        encoding="utf-8",
    )
    print("\n" + "\n".join(against_baseline(summaries)))
    failed = regressions(summaries)
    if failed:
        print("\nBelow the baseline:\n" + "\n".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
