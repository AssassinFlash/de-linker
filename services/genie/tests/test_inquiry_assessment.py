"""Inquiry labels share a deadline, never route to a different model."""

import asyncio
import copy
import json
from typing import Any

import httpx
import pytest

from linker_genie import inquiry_assessment as assessment
from linker_genie.jev import MODEL


def answer(label: str = "normal", basis: str = "business_request") -> dict[str, Any]:
    return {
        "model": "typesafe/jev-1.13-20260917",
        "answers": {
            "classification": {"type": "choice", "choice": label, "confidence": 1},
            "basis": {"type": "choice", "choice": basis},
        },
    }


def test_full_business_snapshot_and_native_channel_are_preserved() -> None:
    state = {
        "submission": {"name": "Synthetic Alex", "message": "Please contact me"},
        "attachments": [{"text": "project notes " * 1500}],
        "conversation": [{"role": "user", "content": "Please check the attached file"}],
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=answer())

    result = asyncio.run(
        assessment.assess(
            assessment.AssessmentInput(state=state, remaining_seconds=10),
            key="synthetic-key",
            transport=httpx.MockTransport(handler),
        )
    )
    assert result["label"] == "normal"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == assessment.ENDPOINT
    body = json.loads(request.content)
    assert body == {
        "model": MODEL,
        "questions": assessment.QUESTIONS,
        "state": state,
    }
    assert result["raw"]["classification"]["choice"] == "normal"


@pytest.mark.parametrize(
    ("label", "basis", "expected", "reason"),
    [
        ("normal", "reporting_abuse", "normal", "classified"),
        ("normal", "unsolicited_bulk_promotion", "uncertain", "conflict"),
        ("normal", "insufficient_context", "uncertain", "conflict"),
        ("suspected_spam", "business_request", "uncertain", "conflict"),
        ("suspected_spam", "fraud_or_phishing", "suspected_spam", "classified"),
        ("uncertain", "insufficient_context", "uncertain", "insufficient_context"),
    ],
)
def test_semantic_conflicts_are_undetermined(
    label: str, basis: str, expected: str, reason: str
) -> None:
    result = assessment.parse(answer(label, basis))
    assert (result["label"], result["reason"]) == (expected, reason)
    assert result["raw"]["classification"]["choice"] == label


@pytest.mark.parametrize("mutation", ["model", "missing", "type", "choice"])
def test_protocol_errors_do_not_become_normal(mutation: str) -> None:
    body = copy.deepcopy(answer())
    if mutation == "model":
        body["model"] = "another-model"
    elif mutation == "missing":
        body.pop("answers")
    elif mutation == "type":
        body["answers"]["classification"]["type"] = "text"
    else:
        body["answers"]["classification"]["choice"] = "invented"
    result = assessment.parse(body)
    assert result["label"] == "uncertain"
    assert result["reason"] in {"invalid_model", "invalid_response"}


def test_actual_async_deadline_cancels_a_slow_provider() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json=answer())

    result = asyncio.run(
        assessment.assess(
            assessment.AssessmentInput(state={}, remaining_seconds=0.02),
            key="synthetic-key",
            transport=httpx.MockTransport(handler),
        )
    )
    assert result["reason"] == "deadline"
    assert result["label"] == "uncertain"
    assert result["seconds"] < 0.5


def test_transient_retry_uses_same_channel_and_budget() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return (
            httpx.Response(503)
            if len(calls) == 1
            else httpx.Response(200, json=answer())
        )

    result = asyncio.run(
        assessment.assess(
            assessment.AssessmentInput(state={}, remaining_seconds=10),
            key="synthetic-key",
            transport=httpx.MockTransport(handler),
        )
    )
    assert result["label"] == "normal"
    assert calls == [assessment.ENDPOINT, assessment.ENDPOINT]


def test_missing_credentials_never_calls_any_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(assessment, "credentials", lambda *args: None)
    result = asyncio.run(
        assessment.assess(assessment.AssessmentInput(state={}, remaining_seconds=10))
    )
    assert (result["label"], result["reason"]) == ("uncertain", "missing_credentials")


def test_provider_failure_has_a_fixed_diagnostic_without_response_text() -> None:
    result = asyncio.run(
        assessment.assess(
            assessment.AssessmentInput(state={}, remaining_seconds=10),
            key="synthetic-key",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, text="private provider data")
            ),
        )
    )
    assert result["reason"] == "provider_http_401"
    assert "private provider data" not in json.dumps(result)


def test_invalid_json_is_explicit() -> None:
    result = asyncio.run(
        assessment.assess(
            assessment.AssessmentInput(state={}, remaining_seconds=10),
            key="synthetic-key",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text="not json")
            ),
        )
    )
    assert result["reason"] == "invalid_response"


def test_assessment_endpoint_requires_shell_identity_and_a_bounded_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from linker_genie import app as service

    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-shell-token")
    seen: list[assessment.AssessmentInput] = []

    async def fake(body: assessment.AssessmentInput) -> dict[str, Any]:
        seen.append(body)
        return assessment.undetermined("missing_credentials")

    monkeypatch.setattr(service, "assess", fake)
    client = TestClient(service.app)
    body = {"state": {"submission": "synthetic"}, "remaining_seconds": 8}
    assert client.post("/inquiries/assess", json=body).status_code == 401
    headers = {"X-Linker-Service-Token": "synthetic-shell-token"}
    assert (
        client.post("/inquiries/assess", json=body, headers=headers).status_code == 200
    )
    assert len(seen) == 1 and seen[0].remaining_seconds == 8
    body["remaining_seconds"] = 11
    assert (
        client.post("/inquiries/assess", json=body, headers=headers).status_code == 422
    )
    assert len(seen) == 1
