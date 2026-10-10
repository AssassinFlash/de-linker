"""Deterministic gates of tools/faq/generate.py (no network)."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def load() -> Any:
    spec = importlib.util.spec_from_file_location("faq_generate", HERE / "generate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = load()


def test_model_digits_are_not_figures() -> None:
    passage = "Rated current 50 A. Maximum current 63 A at -25 to +30 C."
    answer = "The ATS1-T63-A has a rated current of 50 A and a maximum current of 63 A."
    assert gen.numbers_supported(answer, passage, skip=("ATS1-T63-A",))


def test_a_figure_missing_from_the_passage_fails() -> None:
    passage = "Rated current 50 A."
    answer = "Rated current is 50 A. Maximum current is 63 A."
    assert not gen.numbers_supported(answer, passage)


def test_german_decimal_matches_english_decimal() -> None:
    passage = "Nennstrom 15,9 A."
    answer = "Maximum output current of 15.9 A."
    assert gen.numbers_supported(answer, passage)


def test_du_form_is_banned() -> None:
    assert gen.banned_copy("The unit is 50 A.", "Du kannst 50 A anschließen")
    assert not gen.banned_copy("The unit is 50 A.", "Sie können 50 A anschließen.")


def test_not_x_but_y_is_banned() -> None:
    assert gen.banned_copy("This is not a meter but a gateway.", "Das ist ein Gateway.")


def test_flatten_merges_chunks_of_one_page() -> None:
    hits = [
        [
            {"url": "u", "page": 10, "text": "Weight 50.5 kg."},
            {"url": "u", "page": 10, "text": "Dimension 261*626*365 mm."},
            {"url": "u", "page": 11, "text": "Torque 6 Nm."},
        ]
    ]
    passages = gen.flatten_passages(hits)
    assert passages[("u", 10)] == "Weight 50.5 kg.\nDimension 261*626*365 mm."
    assert passages[("u", 11)] == "Torque 6 Nm."


def test_gate_judges_the_whole_cited_page_not_the_last_chunk() -> None:
    """The figure sits in the first chunk of the page; last-write-wins kept the second."""
    hits = [
        [
            {"url": "u", "page": 10, "text": "Weight 50.5 kg."},
            {"url": "u", "page": 10, "text": "Color: white."},
        ]
    ]
    item = {
        "status": "pass",
        "answer_en": "It weighs 50.5 kg.",
        "answer_de": "Es wiegt 50,5 kg.",
        "citation": {"url": "u", "page": 10},
    }
    assert gen.gate_item(item, gen.flatten_passages(hits)) == ("pass", "")
    # This is what the old last-write-wins flatten judged against:
    assert not gen.numbers_supported(item["answer_en"], "Color: white.")


def test_retrieve_ships_the_full_chunk_text() -> None:
    """The 1800-char cap on retrieved text (PR #58 review, defect A) must stay gone:
    four indexed chunks carry unit-bearing figures only beyond that cut."""
    assert "[1800]" not in inspect.getsource(gen.retrieve)
    assert "[:1800]" not in inspect.getsource(gen.retrieve)


def test_review_input_hides_gate_status_and_reasons() -> None:
    """The reviewer judges grounding, not the gate's or a previous verdict's opinion."""
    items = [
        {
            "question_en": "Q",
            "answer_en": "A",
            "answer_de": "A",
            "citation": {"url": "u", "page": 1},
            "_gate": "pass",
            "_gate_reason": "x",
            "status": "withdrawn",
            "review": "withdrawn",
            "reason": "old",
        }
    ]
    projected = gen.review_projection(items)
    assert set(projected[0]) == {"question_en", "answer_en", "answer_de", "citation"}
