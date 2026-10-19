"""The failure checks, locked before the live battery is read as a verdict."""

from __future__ import annotations

from grade import customer_visible_outage, grade


def test_http_error_is_explicit_and_passes_without_a_model_switch() -> None:
    row = grade(
        {
            "id": "VPS-DOWN",
            "kind": "fault",
            "http": 502,
            "error_code": "linker_genie_upstream",
            "error_message": "Genie did not answer.",
            "answer_text": "",
            "done": False,
            "retry": {"ok": True},
        }
    )
    assert row["verdict"] == "pass"
    assert row["reasons"] == []


def test_success_shaped_product_answer_hides_the_outage() -> None:
    row = grade(
        {
            "kind": "fault",
            "http": 200,
            "done": True,
            "answer_text": "Here are matching products from our range.",
            "blocks": [{"type": "cards", "product_ids": [1]}],
            "provider": "deepseek",
            "model": "deepseek-flash",
            "stream_prefix": "event: done",
        }
    )
    assert row["verdict"] == "defect"
    assert "failure is not visible to the customer" in row["reasons"]


def test_a_measurement_on_a_failed_turn_is_a_defect() -> None:
    row = grade(
        {
            "kind": "fault",
            "http": 200,
            "done": True,
            "answer_text": "I could not answer this time. The inverter is 10 kW.",
            "provider": "deepseek",
            "model": "deepseek-flash",
        }
    )
    assert any("measurement" in reason for reason in row["reasons"])


def test_unfinished_stream_counts_as_the_shell_error() -> None:
    row = {
        "http": 200,
        "done": False,
        "stream_prefix": "event: meta\n\n",
        "answer_text": "half an answer",
    }
    assert customer_visible_outage(row) is True


def test_reload_without_an_error_is_a_defect() -> None:
    row = grade(
        {
            "kind": "fault",
            "http": 200,
            "done": False,
            "stream_prefix": "event: block",
            "answer_text": "partial",
            "reload_hides_error": True,
            "provider": "deepseek",
            "model": "deepseek-flash",
            "retry": {"ok": True},
        }
    )
    assert row["verdict"] == "defect"
    assert any("reload" in reason for reason in row["reasons"])


def test_jev_failure_must_be_in_meta_and_must_not_switch_model() -> None:
    hidden = grade(
        {
            "kind": "fault",
            "explicit_channel": "meta",
            "http": 200,
            "done": True,
            "answer_text": "Yes, we stock it.",
            "meta": {},
            "provider": "deepseek",
            "model": "deepseek-flash",
            "allow_measurements": True,
        }
    )
    assert hidden["verdict"] == "defect"
    switched = grade(
        {
            "kind": "fault",
            "explicit_channel": "meta",
            "http": 200,
            "done": True,
            "answer_text": "Yes.",
            "meta": {"jev_error": "http 502"},
            "provider": "openrouter",
            "model": "other",
            "allow_measurements": True,
        }
    )
    assert any("chat model" in reason for reason in switched["reasons"])


def test_a_healthy_control_needs_a_finished_answer() -> None:
    row = grade(
        {
            "kind": "control",
            "http": 200,
            "done": True,
            "answer_text": "Yes, that model is listed.",
            "provider": "deepseek",
            "model": "deepseek-flash",
        }
    )
    assert row["verdict"] == "pass"


def test_a_healthy_burst_may_cite_a_catalogue_rating() -> None:
    row = grade(
        {
            "kind": "burst",
            "children": [
                {
                    "id": "RATE-1",
                    "http": 200,
                    "done": True,
                    "answer_text": "The H2-10K-T3 is 10 kW.",
                    "provider": "deepseek",
                    "model": "deepseek-flash",
                }
            ],
        }
    )
    assert row["verdict"] == "pass"


def test_an_unfinished_stream_does_not_publish_its_measurement() -> None:
    row = grade(
        {
            "kind": "fault",
            "http": 200,
            "done": False,
            "stream_prefix": "event: block",
            "answer_text": "SAJ H2-10K-T3 — 10 kW",
            "provider": "deepseek",
            "model": "deepseek-flash",
            "reload_hides_error": True,
            "retry": {"ok": True},
        }
    )
    assert row["verdict"] == "defect"
    assert any("reload" in reason for reason in row["reasons"])
    assert not any("measurement" in reason for reason in row["reasons"])


def test_burst_accepts_success_and_an_explicit_limit() -> None:
    row = grade(
        {
            "kind": "burst",
            "children": [
                {
                    "id": "RATE-1",
                    "http": 200,
                    "done": True,
                    "answer_text": "Listed.",
                    "provider": "deepseek",
                    "model": "deepseek-flash",
                },
                {
                    "id": "RATE-2",
                    "http": 429,
                    "answer_text": "",
                    "error_message": "rate limit",
                },
            ],
        }
    )
    assert row["verdict"] == "pass"
