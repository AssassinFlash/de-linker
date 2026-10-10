"""The adjudication file, its construction key and the human labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .build import CONSTRUCTION, PAIRS
from .rubric import questions_for


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_items(path: Path = PAIRS) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in read_jsonl(path)}


def load_construction(path: Path = CONSTRUCTION) -> dict[str, dict[str, Any]]:
    return {key["id"]: key for key in read_jsonl(path)}


def state(item: dict[str, Any]) -> dict[str, Any]:
    """What a judge sees: the item without its id, split, label or the reference's URL."""
    if item["set"] == "copy":
        return {"question": item["question"], "answer": item["answer"]}
    reference = {k: v for k, v in item["reference"].items() if k != "url"}
    return {
        "question": item["question"],
        "reference": reference,
        "answer": item["answer"],
        "answer_a": item["answer_a"],
        "answer_b": item["answer_b"],
    }


def load_labels(
    items: dict[str, dict[str, Any]], labels_file: Path | None
) -> dict[str, dict[str, str]]:
    """Human labels as strings, from a labels file (id + label) or the items themselves."""
    source: dict[str, Any] = {}
    if labels_file is not None:
        for row in read_jsonl(labels_file):
            source[row["id"]] = row["human_label"]
    else:
        source = {item_id: item.get("human_label") for item_id, item in items.items()}
    return {
        item_id: {name: str(value) for name, value in label.items()}
        for item_id, label in source.items()
        if label is not None
    }


def label_problems(
    items: dict[str, dict[str, Any]], labels: dict[str, dict[str, str]]
) -> list[str]:
    """Why the labels are not ready for the formal run: missing items and invalid values."""
    problems = []
    for item_id, item in items.items():
        label = labels.get(item_id)
        if label is None:
            problems.append(f"{item_id}: no human_label")
            continue
        for question in questions_for(item["set"]):
            value = label.get(question.name)
            if value not in question.labels():
                problems.append(
                    f"{item_id}: {question.name}={value!r}, expected one of {question.labels()}"
                )
    return problems
