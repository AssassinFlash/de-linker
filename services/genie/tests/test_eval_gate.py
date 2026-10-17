"""`just eval` fails on a regression against the recorded baseline, and only then."""

from index.eval.run import BASELINE, Summary, against_baseline, regressions


def _summary(setting: str, recall: float, accuracy: float) -> Summary:
    return Summary(setting, 984, recall, 0.0, 500, accuracy, {})


def _at_baseline() -> list[Summary]:
    return [_summary(name, *values) for name, values in BASELINE.items()]


def test_the_recorded_baseline_itself_passes() -> None:
    assert regressions(_at_baseline()) == []


def test_better_figures_pass() -> None:
    better = [
        _summary(s.setting, s.recall + 0.01, s.page_accuracy + 0.01)
        for s in _at_baseline()
    ]

    assert regressions(better) == []


def test_a_lower_recall_fails_and_says_by_how_much() -> None:
    summaries = _at_baseline()
    summaries[0] = _summary("vectors, by product", 539 / 984, 419 / 507)

    lines = regressions(summaries)

    assert lines == [
        "vectors, by product: recall@5 54.8% is below the baseline 54.9% by 0.1 points"
    ]


def test_a_lower_page_accuracy_fails() -> None:
    summaries = _at_baseline()
    summaries[1] = _summary("vectors, whole library", 541 / 984, 0.80)

    (line,) = regressions(summaries)

    assert line.startswith("vectors, whole library: citation page accuracy 80.0%")
    assert line.endswith("by 3.7 points")


def test_a_baseline_setting_that_was_not_measured_fails() -> None:
    keywords_only = [_summary("keywords, by product", 0.3, 0.9)]

    assert regressions(keywords_only) == [
        "vectors, by product: not measured (baseline is set for it)",
        "vectors, whole library: not measured (baseline is set for it)",
    ]


def test_the_report_shows_each_setting_beside_its_baseline() -> None:
    (first, second) = against_baseline(_at_baseline())

    assert first == (
        "vectors, by product: recall@5 54.9% (baseline 54.9%, +0.0), "
        "citation page accuracy 82.6% (baseline 82.6%, +0.0)"
    )
    assert second.startswith("vectors, whole library: recall@5 55.0%")


def test_the_baseline_is_the_recorded_measurement() -> None:
    """docs/acceptance/2026-10-17/257/golden-eval.md: 54.9 % / 82.6 %, 55.0 % / 83.7 %."""
    assert {name: (round(r, 3), round(a, 3)) for name, (r, a) in BASELINE.items()} == {
        "vectors, by product": (0.549, 0.826),
        "vectors, whole library": (0.550, 0.837),
    }
