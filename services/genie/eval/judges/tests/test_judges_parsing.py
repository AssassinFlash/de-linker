"""Judge outputs become labels exactly as the metrics expect them."""

import pytest

from linker_judges.judges import parse_chat, parse_system_one
from linker_judges.rubric import QA_QUESTIONS

# The shape aihubmix's /v1/systemone returned for jev-1.13 on 2026-10-09.
JEV_RESPONSE = {
    "grounded": {
        "type": "score",
        "score": 1.9,
        "legend": {"0": "c", "1": "n", "2": "s"},
        "probabilities": {"0": 0.02, "1": 0.06, "2": 0.92},
        "confidence": 0.87,
    },
    "appropriate": {"type": "noul", "noul": 0.2},
    "better_pick": {
        "type": "choice",
        "choice": "equal",
        "probabilities": {"A": 0.18, "B": 0.05, "equal": 0.77},
        "confidence": 0.66,
    },
}


def test_system_one_answers_become_labels_with_confidence() -> None:
    answers = parse_system_one(JEV_RESPONSE, QA_QUESTIONS)

    assert answers["grounded"].label == "2"
    assert answers["grounded"].confidence == 0.87
    assert answers["appropriate"].label == "no"
    assert answers["appropriate"].confidence is not None
    assert abs(answers["appropriate"].confidence - 0.6) < 1e-9
    assert answers["better_pick"].label == "equal"


def test_system_one_answer_outside_the_options_is_invalid() -> None:
    raw = dict(JEV_RESPONSE, better_pick={"type": "choice", "choice": "C"})

    assert parse_system_one(raw, QA_QUESTIONS)["better_pick"].label is None


def test_chat_reply_in_a_code_fence_is_read_and_off_schema_values_are_invalid() -> None:
    reply = '```json\n{"grounded": 0, "appropriate": "yes", "better_pick": "maybe", "reason": "x"}\n```'

    answers, reason = parse_chat(reply, QA_QUESTIONS)

    assert answers["grounded"].label == "0"
    assert answers["appropriate"].label == "yes"
    assert answers["better_pick"].label is None
    assert reason == "x"


# The two shapes OpenRouter's typesafe/jev-router returned on 2026-10-11:
# probabilities under their own key, or as the object's label-valued entries.
def test_chat_score_probabilities_become_a_label_with_confidence() -> None:
    reply = (
        '{"grounded": {"probabilities": {"0": 0.0, "1": 0.0, "2": 1.0}},'
        ' "confidence": 1.0, "reason": "matches"}'
    )

    answers, reason = parse_chat(reply, QA_QUESTIONS)

    assert answers["grounded"].label == "2"
    assert answers["grounded"].confidence == 1.0
    assert answers["grounded"].probabilities == {"0": 0.0, "1": 0.0, "2": 1.0}
    assert reason == "matches"


def test_chat_noul_probability_gets_the_typesafe_confidence() -> None:
    reply = '{"appropriate": {"yes": 0.99, "no": 0.01}, "reason": "in remit"}'

    answers, _ = parse_chat(reply, QA_QUESTIONS)

    assert answers["appropriate"].label == "yes"
    assert answers["appropriate"].confidence is not None
    assert abs(answers["appropriate"].confidence - 0.98) < 1e-9
    assert answers["appropriate"].probabilities == pytest.approx(
        {"yes": 0.99, "no": 0.01}
    )


def test_chat_choice_probabilities_fall_back_to_the_top_probability() -> None:
    reply = (
        '{"better_pick": {"choice": "A", "probabilities":'
        ' {"A": 0.7, "B": 0.1, "equal": 0.2}}, "reason": "a"}'
    )

    answers, _ = parse_chat(reply, QA_QUESTIONS)

    assert answers["better_pick"].label == "A"
    assert answers["better_pick"].confidence == 0.7


def test_chat_probabilities_entirely_outside_the_options_are_invalid() -> None:
    reply = '{"grounded": {"probabilities": {"3": 0.5, "4": 0.5}}, "reason": "x"}'

    answers, _ = parse_chat(reply, QA_QUESTIONS)

    assert answers["grounded"].label is None
    assert answers["grounded"].confidence is None
