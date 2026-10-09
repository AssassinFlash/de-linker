"""Agreement and the calibration-only cascade rule."""

from typing import Any

from linker_judges import metrics


def record(
    item: str, run: int, label: str, confidence: float, cost: float = 0.0
) -> dict[str, Any]:
    return {
        "item": item,
        "run": run,
        "seconds": 1.0,
        "cost_usd": cost,
        "error": None,
        "answers": {"grounded": {"label": label, "confidence": confidence}},
    }


LABELS = {f"i{n}": {"grounded": "2"} for n in range(4)}


def test_agreement_is_the_mean_over_runs_and_invalid_counts_as_wrong() -> None:
    records = [record("i0", 1, "2", 1), record("i1", 1, "0", 1)]
    records += [
        record("i0", 2, "2", 1),
        {**record("i1", 2, "2", 1), "answers": {"grounded": {"label": None}}},
    ]

    assert metrics.agreement(records, LABELS, ["i0", "i1"], ["grounded"]) == 0.5


def test_cascade_threshold_comes_from_calibration_and_escalates_unsure_items() -> None:
    # The first judge is right when confident and wrong when unsure; the fallback is always right.
    first = [record("i0", 1, "2", 0.95), record("i1", 1, "0", 0.4)]
    first += [record("i2", 1, "2", 0.97), record("i3", 1, "0", 0.3)]
    fallback = [record(f"i{n}", 1, "2", 1.0, cost=0.01) for n in range(4)]

    result = metrics.cascade(
        first, fallback, LABELS, ["i0", "i1"], ["i2", "i3"], ("grounded",)
    )

    assert result.thresholds["grounded"] == 0.5
    assert result.agreement == 1.0
    assert result.first_agreement == 0.5
    assert result.escalated_items == 0.5
    assert result.cost_per_thousand == 5.0
