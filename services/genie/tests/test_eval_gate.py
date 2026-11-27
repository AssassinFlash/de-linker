"""`just eval` fails on a regression against the recorded baseline, and only then."""

from pathlib import Path

import pytest

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


def test_current_woo_scope_and_withdrawn_refusals() -> None:
    from unittest.mock import Mock

    from index.eval.goldset import Question
    from index.eval.scope import (
        coverage_failures,
        publication_cases,
        require_same_source,
    )
    from linker_genie.knowledge import KnowledgeSearch
    from linker_genie.publication import PublicationChanged, Snapshot

    questions = [
        Question(str(i), "de", text, "brand", model, "", "text", "")
        for i, (model, text) in enumerate(
            [
                ("Current", "Current question"),
                ("Retired", "Retired question"),
                ("Old label", "Another question about Retired"),
                ("Unknown", "Question about an accessory used with Current"),
            ]
        )
    ]
    source = Snapshot("source", {42: {"model": "Current"}}, {}, "compat", "identity")
    authority = Mock()
    authority.identify.return_value = {
        "current": "published",
        "retired": "unavailable",
        "old label": "unknown",
        "unknown": "unknown",
    }
    authority.identify_text.side_effect = lambda text, **kw: (
        {"retired": "unavailable"} if "Retired" in text else {"current": "published"}
    )
    index = Mock(source_revision="source", model_identity_revision="identity")
    search = KnowledgeSearch(lambda: index, authority)
    cases = publication_cases(questions, authority, source, search)
    assert [c.refused for c in cases] == [None, True, True, None]
    assert cases[2].model_status == "unknown" and cases[2].withdrawn_models == [
        "retired"
    ]
    index.search.assert_not_called()
    assert coverage_failures(cases, source, {"current": [42]}) == []
    assert "inconsistent Woo / index" in coverage_failures(cases, source, {})[0]
    require_same_source(index, source)
    index.model_identity_revision = "old"
    with pytest.raises(PublicationChanged):
        require_same_source(index, source)
    broken = Mock()
    broken.search.return_value = {"hits": []}
    failures = coverage_failures(
        publication_cases(questions, authority, source, broken),
        source,
        {"current": [42]},
    )
    assert [f.split(":")[0] for f in failures] == ["1", "2"]
    broken.search.side_effect = PublicationChanged(
        "Woo publication changed during the operation"
    )
    with pytest.raises(PublicationChanged, match="Woo publication changed"):
        publication_cases(questions, authority, source, broken)


def test_custom_golden_diagnostic_cannot_publish_passing_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    from unittest.mock import Mock

    from index.eval import run
    from index.eval.goldset import GOLDEN_PATH
    from index.eval.metrics import Score
    from linker_genie.publication import Snapshot

    custom = tmp_path / "subset.jsonl"
    question = json.loads(GOLDEN_PATH.read_text().splitlines()[0])
    custom.write_text(json.dumps(question))
    model = question["model"]
    source = Snapshot("s", {1: {"model": model}}, {}, "", "m")
    authority = Mock()
    authority.snapshot.return_value = source
    authority.identify.return_value = {model.casefold(): "published"}
    for name in ["eval.json", "eval-publication.json"]:
        (tmp_path / name).write_text("original")
    monkeypatch.setattr(run, "current", lambda: authority)
    index = Mock(version="v", source_revision="s", model_identity_revision="m")
    monkeypatch.setattr(run, "DocumentIndex", lambda *a, **k: index)
    monkeypatch.setattr(run, "product_ids_by_model", lambda p: {model.casefold(): [1]})
    monkeypatch.setattr(run, "evaluate", lambda *a: [Score(1, True)])
    assert (
        run.main(["--index", str(tmp_path / "index.sqlite"), "--golden", str(custom)])
        == 2
    )
    assert json.loads((tmp_path / "eval-diagnostic.json").read_text())["failures"] == []
    assert all(
        (tmp_path / name).read_text() == "original"
        for name in ["eval.json", "eval-publication.json"]
    )
