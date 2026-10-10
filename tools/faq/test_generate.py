"""Deterministic gates of tools/faq/generate.py (no network)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
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
