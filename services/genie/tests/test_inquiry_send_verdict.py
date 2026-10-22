"""The sending decision is bound, probabilistic and fail-closed across both judges."""

import asyncio
import json
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from linker_genie import inquiry_assessment as assessment


@pytest.fixture(autouse=True)
def isolated_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "off")


def binding(**changes: Any) -> assessment.Binding:
    return assessment.Binding(
        **{
            "protocol": "inquiry-mail-v1",
            "policy": "inquiry-mail-v1",
            "record_id": 17,
            "snapshot_sha256": "a" * 64,
            "purpose": "inquiry_mail",
            **changes,
        }
    )


def body(**changes: Any) -> assessment.AssessmentInput:
    return assessment.AssessmentInput(
        **{
            "state": {
                "submission": {
                    "billing": {"first_name": "Synthetic Ada", "company": "EPC"},
                    "message": "Bitte senden Sie das Datenblatt.",
                }
            },
            "binding": binding(),
            "remaining_seconds": 1,
            **changes,
        }
    )


def answers(
    label: str = "normal", basis: str = "business_request", confidence: float = 1
) -> dict[str, Any]:
    return {
        "classification": {"type": "choice", "choice": label, "confidence": confidence},
        "basis": {"type": "choice", "choice": basis, "confidence": confidence},
    }


def jev(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"model": "typesafe/jev-1.13-20260917", "answers": raw or answers()}


def deepseek(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "model": "deepseek-flash",
        "choices": [{"message": {"content": json.dumps(raw or answers())}}],
    }


def test_unestablished_dated_escalation_model_does_not_authorize() -> None:
    response = deepseek()
    response["model"] = "deepseek-flash-20261023"
    result = assessment._escalation(response)
    assert (result["decision"], result["reason"]) == ("unknown", "invalid_model")


@pytest.mark.parametrize(
    "change",
    [
        {"purpose": "other"},
        {"policy": "inquiry-observation-v1"},
        {"record_id": True},
        {"record_id": "17"},
        {"snapshot_sha256": "A" * 64},
        {"unexpected": "x"},
    ],
)
def test_invalid_native_binding_is_not_accepted(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        binding(**change)


def test_unbound_legacy_observation_and_structured_credentials_are_rejected() -> None:
    with pytest.raises(ValidationError):
        assessment.AssessmentInput.model_validate({"state": {}, "remaining_seconds": 1})
    with pytest.raises(ValidationError):
        body(state={"context": {"api_key": "never-forward-this"}})


@pytest.mark.parametrize(
    "change",
    [
        {"record_id": 18},
        {"purpose": "conversation_mail"},
        {"snapshot_sha256": "b" * 64},
    ],
)
def test_each_native_binding_is_echoed_without_cross_source_reuse(
    change: dict[str, Any],
) -> None:
    seen: list[dict[str, Any]] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=jev())

    source = body(binding=binding(**change))
    result = asyncio.run(
        assessment.assess(
            source, key="synthetic", transport=httpx.MockTransport(upstream)
        )
    )
    assert result["binding"] == source.binding.model_dump()
    assert result["binding"] != binding().model_dump()
    assert result["decision"] == "normal"
    assert seen[0]["state"] == source.state
    assert (
        "binding" not in seen[0]
    )  # Native identity is not evidence for a favourable model label.


@pytest.mark.parametrize(
    "raw",
    [
        answers(confidence=0.89),
        answers("unknown", "insufficient_context"),
        answers("normal", "fraud_or_phishing"),
    ],
)
def test_valid_primary_shortfall_uses_only_official_escalation(
    raw: dict[str, Any],
) -> None:
    seen: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json=jev(raw)
            if len(seen) == 1
            else deepseek(answers("malicious", "fraud_or_phishing")),
        )

    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert [str(request.url) for request in seen] == [
        assessment.ENDPOINT,
        assessment.ESCALATION_ENDPOINT,
    ]
    assert [json.loads(request.content)["model"] for request in seen] == [
        assessment.MODEL,
        assessment.ESCALATION_MODEL,
    ]
    assert (result["decision"], result["reason"]) == ("malicious", "escalated")
    assert result["raw"]["primary"]["answers"] == raw | {
        name: value | {"probabilities": {}} for name, value in raw.items()
    }
    assert result["raw"]["escalation"]["model"] == "deepseek-flash"


@pytest.mark.parametrize(
    "failure", ["http", "network", "invalid_model", "invalid_wire", "invalid_json"]
)
def test_provider_or_protocol_failure_never_changes_provider(failure: str) -> None:
    seen: list[str] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if failure == "network":
            raise httpx.ConnectError("private error details", request=request)
        if failure == "http":
            return httpx.Response(503, text="private failure body")
        if failure == "invalid_json":
            return httpx.Response(200, text="not json")
        raw = jev()
        if failure == "invalid_model":
            raw["model"] = "unapproved-model"
        else:
            raw["answers"]["classification"]["choice"] = ["normal"]
        return httpx.Response(200, json=raw)

    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert result["decision"] == "unknown"
    assert result["raw"]["escalation"] is None
    assert seen and set(seen) == {assessment.ENDPOINT}
    assert len(seen) == (2 if failure in {"http", "network"} else 1)
    assert "private" not in json.dumps(result)


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), -0.1, 1.1, True, "1", 10**400]
)
def test_invalid_confidence_never_produces_normal(value: Any) -> None:
    raw = jev()
    raw["answers"]["classification"]["confidence"] = value
    assert assessment.parse(raw)["decision"] == "unknown"


def test_probabilities_are_preserved_and_cap_an_inconsistent_confidence() -> None:
    raw = jev()
    raw["answers"]["classification"]["probabilities"] = {
        "normal": 0.6,
        "malicious": 0.3,
        "unknown": 0.1,
    }
    parsed = assessment.parse(raw)
    assert parsed["reason"] == "insufficient_confidence"
    assert (
        parsed["raw"]["classification"]["probabilities"]
        == raw["answers"]["classification"]["probabilities"]
    )
    raw["answers"]["classification"]["probabilities"] = {
        "normal": 0.1,
        "malicious": 0.8,
        "unknown": 0.1,
    }
    assert assessment.parse(raw)["reason"] == "conflict"


@pytest.mark.parametrize(
    ("declared", "selected", "other", "expected"),
    [
        (None, 0.93, 0.06, 0.93),  # Observed .99 mass: no upward normalization.
        (0.92, 0.93, 0.06, 0.92),
        (1.0, 0.89, 0.01, 0.89),  # Missing mass cannot cross the .90 threshold.
        (None, 0.95, 0.15, 0.95 / 1.10),
        (0.85, 0.95, 0.15, 0.85),
        (None, 1.0, 0.10, 1.0 / 1.10),
    ],
)
def test_probability_mass_only_lowers_effective_confidence(
    declared: float | None, selected: float, other: float, expected: float
) -> None:
    answer = {
        "choice": "normal",
        "confidence": declared,
        "probabilities": {"normal": selected, "malicious": other, "unknown": 0.0},
    }
    actual = assessment._confidence(answer)
    assert actual == pytest.approx(expected)
    assert actual is not None and actual <= selected
    if declared is not None:
        assert actual <= declared


@pytest.mark.parametrize(
    "probabilities",
    [
        None,
        {},
        {"normal": 0, "malicious": 0, "unknown": 0},
        {"normal": 1},
        {"normal": 1, "malicious": 0, "unknown": 0, "other": 0},
        {"normal": True, "malicious": 0, "unknown": 0},
        {"normal": float("nan"), "malicious": 0, "unknown": 0},
        {"normal": float("inf"), "malicious": 0, "unknown": 0},
        {"normal": -0.1, "malicious": 0, "unknown": 0},
        {"normal": 1.1, "malicious": 0, "unknown": 0},
        {"normal": "1", "malicious": 0, "unknown": 0},
    ],
)
def test_malformed_or_zero_mass_probabilities_remain_invalid(
    probabilities: Any,
) -> None:
    raw = jev()
    raw["answers"]["classification"]["probabilities"] = probabilities
    assert (assessment.parse(raw)["decision"], assessment.parse(raw)["reason"]) == (
        "unknown",
        "invalid_response",
    )


def test_observed_incomplete_mass_is_accepted_without_upward_confidence_or_switch() -> (
    None
):
    raw = answers("malicious", "fraud_or_phishing", confidence=0.92)
    raw["basis"]["probabilities"] = {
        "business_request": 0,
        "service_or_complaint": 0,
        "reporting_abuse": 0,
        "fraud_or_phishing": 0.93,
        "unsolicited_bulk_promotion": 0.04,
        "meaningless_abuse": 0.02,
        "insufficient_context": 0,
    }
    seen: list[str] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=jev(raw))

    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert (result["decision"], result["reason"]) == ("malicious", "classified")
    assert assessment._confidence(result["raw"]["primary"]["answers"]["basis"]) == 0.92
    assert seen == [assessment.ENDPOINT]
    assert result["raw"]["escalation"] is None


def test_excess_mass_cannot_turn_below_threshold_evidence_into_permission() -> None:
    raw = jev()
    raw["answers"]["classification"]["probabilities"] = {
        "normal": 0.95,
        "malicious": 0.15,
        "unknown": 0,
    }
    result = assessment.parse(raw)
    assert (result["decision"], result["reason"]) == (
        "unknown",
        "insufficient_confidence",
    )


@pytest.mark.parametrize(
    "raw",
    [
        answers(confidence=0.89),
        answers("normal", "fraud_or_phishing"),
        answers("unknown", "insufficient_context"),
    ],
)
def test_unresolved_escalation_never_produces_permission(raw: dict[str, Any]) -> None:
    seen = 0

    def upstream(request: httpx.Request) -> httpx.Response:
        nonlocal seen
        seen += 1
        return httpx.Response(
            200, json=jev(answers(confidence=0.5)) if seen == 1 else deepseek(raw)
        )

    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert result["decision"] == "unknown"
    assert seen == 2


def test_late_cancellation_resistant_escalation_cannot_allow_sending() -> None:
    async def upstream(request: httpx.Request) -> httpx.Response:
        if str(request.url) == assessment.ENDPOINT:
            await asyncio.sleep(0.01)
            return httpx.Response(200, json=jev(answers(confidence=0.5)))
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass  # Deliberately late successful provider response.
        return httpx.Response(200, json=deepseek())

    result = asyncio.run(
        assessment.assess(
            body(remaining_seconds=0.02),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert (result["decision"], result["reason"]) == ("unknown", "deadline")
    assert result["seconds"] < 0.5
    assert result["usage"]["primary"]["attempts"] == 1
    assert result["usage"]["escalation"]["attempts"] == 1


def test_absent_confidence_and_escalation_credentials_are_unknown() -> None:
    raw = answers()
    raw["basis"].pop("confidence")
    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="",
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=jev(raw))),
        )
    )
    assert (result["decision"], result["reason"]) == (
        "unknown",
        "escalation_missing_credentials",
    )


def test_escalation_budget_refusal_cannot_dispatch_or_allow(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    from linker_judges.budget import CAPACITIES

    ledger = tmp_path / "provider.sqlite"
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_MODE", "enforce")
    monkeypatch.setenv("LINKER_PROVIDER_BUDGET_PATH", str(ledger))
    monkeypatch.setitem(CAPACITIES, "deepseek", 0)
    seen: list[str] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=jev(answers(confidence=0.5)))

    result = asyncio.run(
        assessment.assess(
            body(),
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert (result["decision"], result["reason"]) == (
        "unknown",
        "escalation_provider_budget_quota",
    )
    assert seen == [assessment.ENDPOINT]
    assert result["usage"]["escalation"]["attempts"] == 0
    with sqlite3.connect(ledger) as db:
        assert db.execute("SELECT provider FROM dispatch").fetchall() == [("jev",)]


def test_conflicting_primary_can_be_resolved_as_normal_without_rewriting_source() -> (
    None
):
    source = body()
    seen: list[dict[str, Any]] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=jev(answers("normal", "fraud_or_phishing"))
            if len(seen) == 1
            else deepseek(),
        )

    result = asyncio.run(
        assessment.assess(
            source,
            key="synthetic",
            escalation_key="synthetic",
            transport=httpx.MockTransport(upstream),
        )
    )
    assert (result["decision"], result["reason"]) == ("normal", "escalated")
    assert json.loads(seen[1]["messages"][1]["content"]) == source.state
    assert result["binding"] == source.binding.model_dump()
