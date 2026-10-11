"""What the ability client sends, and where the customer's identity may ride.

The service calls the read-only abilities anonymously; the only identity it
ever carries is the shell's short-lived token, and only on the one ability
that answers about the browsing customer (docs/specs/13-genie.md §B, #16's
user-context passthrough).
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from linker_genie.abilities import (
    USER_CONTEXT_ABILITY,
    USER_CONTEXT_HEADER,
    AbilityClient,
    AbilityError,
)


class Recorder:
    """An httpx transport that answers like the abilities endpoint."""

    def __init__(self, status: int = 200, body: Any = None) -> None:
        self.requests: list[httpx.Request] = []
        self.status = status
        self.body = body if body is not None else {"result": {"ok": True}}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body, request=request)


def client_for(recorder: Recorder) -> AbilityClient:
    return AbilityClient(
        "http://wp.test", transport=httpx.MockTransport(recorder.handler)
    )


def test_a_read_only_call_carries_no_identity() -> None:
    recorder = Recorder()
    client = client_for(recorder)

    client.run("linker/search-products", {"lang": "en"})

    assert USER_CONTEXT_HEADER not in recorder.requests[0].headers


def test_the_customer_context_rides_only_the_inquiry_ability() -> None:
    recorder = Recorder()
    client = client_for(recorder)

    client.run(USER_CONTEXT_ABILITY, {}, "u123|1|signature")
    client.run("linker/get-product", {"product_id": 4107}, "u123|1|signature")

    assert recorder.requests[0].headers[USER_CONTEXT_HEADER] == "u123|1|signature"
    assert USER_CONTEXT_HEADER not in recorder.requests[1].headers


def test_without_a_context_even_the_inquiry_ability_stays_anonymous() -> None:
    recorder = Recorder()
    client = client_for(recorder)

    client.run(USER_CONTEXT_ABILITY, {})

    assert USER_CONTEXT_HEADER not in recorder.requests[0].headers


def test_a_login_gated_ability_answers_the_login_required_fact() -> None:
    recorder = Recorder(status=401, body={"code": "rest_forbidden"})
    client = client_for(recorder)

    assert client.run(USER_CONTEXT_ABILITY, {}) == {"error": "login_required"}


def test_a_refusal_that_is_not_a_login_requirement_is_an_error() -> None:
    recorder = Recorder(status=500, body={"message": "boom"})
    client = client_for(recorder)

    with pytest.raises(AbilityError):
        client.run("linker/search-products", {})
