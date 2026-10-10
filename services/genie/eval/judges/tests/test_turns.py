"""The pilot's cascade decision and per-turn question selection."""

from typing import Any

from linker_judges.rubric import APPROPRIATE, BETTER_PICK, GROUNDED, QA_QUESTIONS
from linker_judges.turns import (
    TURN_THRESHOLDS,
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


def test_thresholds_are_the_formal_calibration_frozen() -> None:
    assert TURN_THRESHOLDS == {
        "grounded": 0.85,
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
