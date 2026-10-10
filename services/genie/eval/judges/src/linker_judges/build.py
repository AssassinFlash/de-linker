"""Builds the blind adjudication file and its construction key from the seeds.

pairs.jsonl is what the human adjudicator and the judges see: question, reference,
answer, the two answers to compare, and an empty `human_label`. construction.jsonl
holds what the builder knows (answer class, expected labels, provenance) and is kept
apart so that adjudication stays blind (docs/specs/33-judge-bakeoff.md: 盲审).
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import templates
from .numbers import Quantity, parse_cell, show, tamper
from .pages import page_text, table_excerpt

HERE = Path(__file__).resolve().parents[2]
SEEDS = HERE / "data" / "seeds.json"
COPY = HERE / "data" / "copy.json"
PAIRS = HERE / "pairs.jsonl"
CONSTRUCTION = HERE / "construction.jsonl"
# Where #10 keeps our hosted PDFs (services/genie/index/paths.py); LINKER_DATA moves it.
PDF_DIR = Path(os.environ.get("LINKER_DATA", "~/de-linker-data")).expanduser() / "pdf"

# A third of the base questions decide the cascade threshold; the rest score it.
# Split by base question, so no question's other variants or language leak across.
CALIBRATION_SHARE = 1 / 3
SHUFFLE_SEED = 33

CORRECT, PARAPHRASE, TAMPER, WRONG_MODEL, OUT_OF_SCOPE = (
    "correct",
    "paraphrase_correct",
    "numeric_tamper",
    "wrong_model",
    "out_of_scope_answered",
)
GOOD = (CORRECT, PARAPHRASE)


@dataclass(frozen=True)
class Variant:
    base: str
    kind: str
    lang: str
    answer_class: str
    question: str
    reference: dict[str, Any]
    answer: str
    alternative_class: str
    alternative: str
    provenance: dict[str, Any]


def _stable(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)


def _datasheet_variants(
    seed: dict[str, Any], index: int, documents: dict[str, Any]
) -> list[Variant]:
    variants = []
    for lang in ("en", "de"):
        ref = seed["refs"][lang]
        document = documents[ref["doc"]]
        excerpt = table_excerpt(
            page_text(PDF_DIR / f"{ref['doc']}.pdf", ref["page"]),
            ref["anchor"],
            ref["occurrence"],
            ref["above"],
            ref["row"],
            ref["after"],
        )
        unit = seed["unit"]
        value = parse_cell(excerpt.values[ref["col"]], unit)
        alt = parse_cell(excerpt.values[ref["alt_col"]], unit)
        row_values = {parse_cell(cell, unit).value for cell in excerpt.values}
        if alt.value == value.value:
            raise ValueError(
                f"{seed['id']}/{lang}: the other model's value equals the target"
            )
        reference = {
            "document": document["title"],
            "page": ref["page"],
            "url": f"{document['url']}#page={ref['page']}",
            "text": excerpt.text,
        }
        provenance = {
            "sha256": ref["doc"],
            "page": ref["page"],
            "row": ref["row"],
            "model": ref["model"],
            "value": value.text,
            "other_model": ref["alt_model"],
            "other_value": alt.text,
        }
        variants += _numeric_variants(
            seed["id"],
            "datasheet",
            lang,
            seed["field"],
            seed["category"],
            ref["model"],
            value,
            alt,
            row_values,
            index,
            reference,
            provenance,
            ref["page"],
        )
    return variants


def _catalogue_variants(seed: dict[str, Any], index: int) -> list[Variant]:
    value_text, unit = seed["value"].split(" ", 1)
    alt_text, _ = seed["alt_value"].split(" ", 1)
    value, alt = Quantity(value_text, unit), Quantity(alt_text, unit)
    key = seed["field"]
    row_values = set()
    for result in seed["results"]:
        if key in result:
            row_values.add(Decimal(str(result[key]).split(" ", 1)[0]))
    reference = {"tool": "linker/search-products", "results": seed["results"]}
    provenance = {
        "source": "docs/research/2026-10-09/old-repo-live-catalogue-facts.md",
        "model": seed["model"],
        "value": seed["value"],
        "other_model": seed["alt_model"],
        "other_value": seed["alt_value"],
    }
    variants = []
    for lang in ("en", "de"):
        variants += _numeric_variants(
            seed["id"],
            "catalogue",
            lang,
            key,
            seed["category"],
            seed["model"],
            value,
            alt,
            row_values,
            index,
            reference,
            provenance,
            None,
        )
    return variants


def _numeric_variants(
    base: str,
    kind: str,
    lang: str,
    field: str,
    category: str,
    model: str,
    value: Quantity,
    alt: Quantity,
    row_values: set[Decimal],
    index: int,
    reference: dict[str, Any],
    provenance: dict[str, Any],
    page: int | None,
) -> list[Variant]:
    """The five answers to one question; styles rotate with the seed's position."""
    q = templates.question(field, category, model, lang)
    correct = templates.statement(field, category, model, show(value, lang), lang)
    para = templates.paraphrase(index % 4, field, category, model, value, lang, page)
    wrong = tamper(value, row_values | {alt.value})
    tampered = templates.styled(
        templates.statement(field, category, model, show(wrong, lang), lang),
        lang,
        index % 2 == 0,
    )
    swapped = templates.styled(
        templates.statement(field, category, model, show(alt, lang), lang),
        lang,
        index % 2 == 1,
    )
    beyond = (
        correct
        + " "
        + templates.OUT_OF_REMIT[lang][index % len(templates.OUT_OF_REMIT[lang])]
    )
    good_for_errors = (CORRECT, correct) if index % 2 == 0 else (PARAPHRASE, para)
    provenance = provenance | {
        "tampered_value": wrong.text,
        "paraphrase_style": index % 4,
    }
    rows = [
        (CORRECT, correct, (PARAPHRASE, para)),
        (PARAPHRASE, para, (CORRECT, correct)),
        (TAMPER, tampered, good_for_errors),
        (WRONG_MODEL, swapped, good_for_errors),
        (OUT_OF_SCOPE, beyond, good_for_errors),
    ]
    return [
        Variant(
            base, kind, lang, cls, q, reference, text, alt_cls, alt_text, provenance
        )
        for cls, text, (alt_cls, alt_text) in rows
    ]


def _out_of_scope_variants(
    seed: dict[str, Any], index: int, references: dict[tuple[str, str], dict[str, Any]]
) -> list[Variant]:
    variants = []
    for lang in ("en", "de"):
        text = seed[lang]
        source = seed["reference"]
        reference = references[(source["seed"], lang)] if "seed" in source else source
        provenance = {
            "topic": seed["id"],
            "reference_from": source.get("seed", source.get("tool")),
        }
        good = (
            (CORRECT, text["correct"])
            if index % 2 == 0
            else (PARAPHRASE, text["paraphrase"])
        )
        rows = [
            (CORRECT, text["correct"], (PARAPHRASE, text["paraphrase"])),
            (PARAPHRASE, text["paraphrase"], (CORRECT, text["correct"])),
            (OUT_OF_SCOPE, text["answered"], good),
        ]
        variants += [
            Variant(
                seed["id"],
                "out_of_scope",
                lang,
                cls,
                text["question"],
                reference,
                answer,
                alt_cls,
                alt,
                provenance,
            )
            for cls, answer, (alt_cls, alt) in rows
        ]
    return variants


def expected_labels(
    answer_class: str, alternative_class: str, position: str
) -> dict[str, Any]:
    """What the construction intends; the human label, not this, is the truth."""
    grounded = {CORRECT: 2, PARAPHRASE: 2, TAMPER: 0, WRONG_MODEL: 0, OUT_OF_SCOPE: 1}[
        answer_class
    ]
    appropriate = "no" if answer_class == OUT_OF_SCOPE else "yes"
    if answer_class in GOOD and alternative_class in GOOD:
        better = "equal"
    else:
        better = "B" if position == "A" else "A"
    return {"grounded": grounded, "appropriate": appropriate, "better_pick": better}


def build(force: bool = False) -> tuple[int, int]:
    """Writes the blind file and its key. Refuses to overwrite a file that already
    carries human labels (the truth axis) unless `force` is set."""
    if PAIRS.exists() and not force:
        labelled = sum(
            1
            for line in PAIRS.read_text().splitlines()
            if line.strip() and (json.loads(line).get("human_label") is not None)
        )
        if labelled:
            raise SystemExit(
                f"{PAIRS.name} already holds {labelled} human labels; "
                "rebuilding would erase the truth axis. Pass --force to rebuild anyway."
            )
    seeds = json.loads(SEEDS.read_text())
    documents = seeds["documents"]
    variants: list[Variant] = []
    references: dict[tuple[str, str], dict[str, Any]] = {}
    for index, seed in enumerate(seeds["datasheet"]):
        made = _datasheet_variants(seed, index, documents)
        variants += made
        for variant in made:
            references[(seed["id"], variant.lang)] = variant.reference
    for index, seed in enumerate(seeds["catalogue"], start=len(seeds["datasheet"])):
        variants += _catalogue_variants(seed, index)
    for index, seed in enumerate(seeds["out_of_scope"]):
        variants += _out_of_scope_variants(seed, index, references)

    calibration = _calibration_bases(seeds)
    rng = random.Random(SHUFFLE_SEED)
    rng.shuffle(variants)
    pairs, keys = [], []
    for number, variant in enumerate(variants, 1):
        pair_id = f"p{number:03d}"
        position = "A" if _stable(pair_id) % 2 == 0 else "B"
        answer_a, answer_b = (
            (variant.answer, variant.alternative)
            if position == "A"
            else (variant.alternative, variant.answer)
        )
        pairs.append(
            {
                "id": pair_id,
                "set": "qa",
                "lang": variant.lang,
                "split": "calibration" if variant.base in calibration else "test",
                "question": variant.question,
                "reference": variant.reference,
                "answer": variant.answer,
                "answer_a": answer_a,
                "answer_b": answer_b,
                "human_label": None,
            }
        )
        keys.append(
            {
                "id": pair_id,
                "base": variant.base,
                "kind": variant.kind,
                "answer_class": variant.answer_class,
                "alternative_class": variant.alternative_class,
                "answer_position": position,
                "expected": expected_labels(
                    variant.answer_class, variant.alternative_class, position
                ),
                "provenance": variant.provenance,
            }
        )
    copy_items = json.loads(COPY.read_text())["items"]
    order = list(range(len(copy_items)))
    rng.shuffle(order)
    for number, original in enumerate(order, 1):
        item = copy_items[original]
        item_id = f"c{number:02d}"
        pairs.append(
            {
                "id": item_id,
                "set": "copy",
                "lang": item["lang"],
                "split": "calibration" if _stable(item_id) % 3 == 0 else "test",
                "question": item["question"],
                "answer": item["answer"],
                "human_label": None,
            }
        )
        keys.append(
            {
                "id": item_id,
                "base": item_id,
                "kind": "copy",
                "answer_class": item["construction"],
                "expected": item["expected"],
            }
        )
    PAIRS.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in pairs))
    CONSTRUCTION.write_text(
        "".join(json.dumps(k, ensure_ascii=False) + "\n" for k in keys)
    )
    return len(variants), len(copy_items)


def _calibration_bases(seeds: dict[str, Any]) -> set[str]:
    """Per kind, the first third of base ids in hash order go to calibration."""
    chosen: set[str] = set()
    for kind in ("datasheet", "catalogue", "out_of_scope"):
        ids = sorted(
            (seed["id"] for seed in seeds[kind]),
            key=lambda base: _stable("split:" + base),
        )
        chosen.update(ids[: round(len(ids) * CALIBRATION_SHARE)])
    return chosen
