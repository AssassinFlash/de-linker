"""The pilot's cascade decision, per-turn question selection and offer form."""

from typing import Any

from linker_judges.rubric import APPROPRIATE, BETTER_PICK, GROUNDED, QA_QUESTIONS
from linker_judges.turns import (
    TURN_THRESHOLDS,
    answer_with_offers,
    cascade_answers,
    turns_questions,
    turns_state,
)


def _verdict(
    judge: str, grounded: str | None, confidence: float | None
) -> dict[str, Any]:
    return {
        "judge": judge,
        "answers": {
            "grounded": {"label": grounded, "confidence": confidence},
            "appropriate": {"label": "yes", "confidence": 0.99},
            "better_pick": {"label": "A", "confidence": 0.99},
        },
    }


def test_thresholds_are_the_recibrated_pilot_values() -> None:
    # Grounded 0.6: the #16 recalibration on the real-turn pilot (2026-10-11,
    # runs/pilot-20261011-v4) — the frozen #33 value 0.85 escalated 9/11 turns
    # on confidence alone; 0.6 keeps the same agreement at 3/11.
    assert TURN_THRESHOLDS == {
        "grounded": 0.6,
        "appropriate": 0.5,
        "better_pick": 0.6,
    }


def test_candidate_rows_ask_all_three_questions() -> None:
    assert turns_questions(True) == QA_QUESTIONS
    assert turns_questions(False) == (GROUNDED, APPROPRIATE)
    assert turns_questions(False) != QA_QUESTIONS
    assert BETTER_PICK.name == "better_pick"


def test_state_carries_answers_only_when_candidates_exist() -> None:
    with_candidates = turns_state(
        {
            "question": "q",
            "answer": "a",
            "reference": {},
            "cards": [1],
            "answer_a": "a",
            "answer_b": "b",
        }
    )
    assert with_candidates["answer_a"] == "a"
    assert with_candidates["answer_b"] == "b"

    without = turns_state(
        {"question": "q", "answer": "a", "reference": {}, "cards": []}
    )
    assert "answer_a" not in without
    assert "answer_b" not in without


def test_above_threshold_keeps_the_first_judge() -> None:
    labels, sources = cascade_answers(
        _verdict("jev", "2", 0.9), _verdict("deepseek", "0", 0.9), QA_QUESTIONS
    )
    assert labels["grounded"] == "2"
    assert sources["grounded"] == "jev"


def test_below_threshold_takes_the_fallback() -> None:
    labels, sources = cascade_answers(
        _verdict("jev", "2", 0.4), _verdict("deepseek", "1", 0.8), QA_QUESTIONS
    )
    assert labels["grounded"] == "1"
    assert sources["grounded"] == "deepseek"


def test_below_threshold_without_fallback_is_unresolved() -> None:
    labels, sources = cascade_answers(_verdict("jev", "2", 0.4), None, QA_QUESTIONS)
    assert labels["grounded"] is None
    assert sources["grounded"] == "unresolved"
    assert sources["appropriate"] == "jev"  # 0.99 ≥ 0.5


def test_missing_confidence_never_stands() -> None:
    labels, sources = cascade_answers(
        _verdict("jev", "2", None), _verdict("deepseek", "2", 0.5), QA_QUESTIONS
    )
    assert sources["grounded"] == "deepseek"


def test_a_page_row_names_its_own_product_apart() -> None:
    """The R5 form: the page's product is not a recommendation."""
    answer = answer_with_offers("The H2-10K-T3 pairs with these.", 4107, [4107, 2092])
    assert answer == (
        "The H2-10K-T3 pairs with these.\n\n"
        "This page's product: 4107.\n"
        "Recommended products: 2092."
    )


def test_a_row_without_a_page_states_only_its_recommendations() -> None:
    answer = answer_with_offers("Here are batteries.", None, [2092, 2067])
    assert answer == "Here are batteries.\n\nRecommended products: 2092, 2067."


def test_a_row_without_products_keeps_the_plain_answer() -> None:
    assert answer_with_offers("We do not install.", None, []) == "We do not install."


def test_the_wrong_pick_replaces_a_recommendation() -> None:
    real = answer_with_offers("These pair.", 4107, [4107, 2092, 2067])
    variant = answer_with_offers("These pair.", 4107, [4107, 2092, 2067], (2092, 6507))
    assert "This page's product: 4107." in variant
    assert "Recommended products: 6507, 2067." in variant
    assert variant != real


def test_the_wrong_pick_on_the_page_product_misattributes_the_page() -> None:
    """The source takes the role it displaces: a page-product swap claims the
    page itself is another model, not a silent no-op."""
    variant = answer_with_offers(
        "This is the HS3-5K.", 2198, [2198, 2199], (2198, 4107)
    )
    assert "This page's product: 4107." in variant
    assert "Recommended products: 2199." in variant
