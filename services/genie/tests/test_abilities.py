"""What the ability client sends, where the customer's identity may ride, and
how a transiently failing ability call is retried.

The service holds no identity of its own; the only identity it ever carries is
the shell's short-lived token, and only on the abilities whose answer depends on
the browsing customer: the inquiry list, and the product abilities whose prices
follow the account (#242, docs/specs/13-genie.md 价格跟账号走).

The retry tests stand in for the storm: a Redis hiccup on the WordPress side
kills the ability's request mid-read, which the service sees as a 5xx or a
dropped connection. Three attempts ride the blip out; a call that still fails
raises AbilityError, which the turn cycle answers with the fallback.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from linker_genie.abilities import (
    ABILITY_ATTEMPTS,
    USER_CONTEXT_ABILITIES,
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


class Flaky:
    """A transport whose first `failures` calls raise like a dead connection
    (the service-side shape of the storm) and then answer like the endpoint."""

    def __init__(
        self, failures: int, error: Exception | None = None, status: int = 200
    ) -> None:
        self.requests: list[httpx.Request] = []
        self.failures = failures
        self.error = error or httpx.ConnectError("connection dropped")
        self.status = status

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if len(self.requests) <= self.failures:
            raise self.error
        return httpx.Response(
            self.status, json={"result": {"ok": True}}, request=request
        )


class Clock:
    """The injected sleep: records the backoff waits instead of taking them."""

    def __init__(self) -> None:
        self.waits: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


def client_for(recorder: Recorder | Flaky, clock: Clock | None = None) -> AbilityClient:
    return AbilityClient(
        "http://wp.test",
        transport=httpx.MockTransport(recorder.handler),
        sleep=clock or Clock(),
    )


def test_a_call_without_a_customer_carries_no_identity() -> None:
    recorder = Recorder()
    client = client_for(recorder)

    client.run("linker/search-products", {"lang": "en"})

    assert USER_CONTEXT_HEADER not in recorder.requests[0].headers


def test_the_customer_context_rides_the_abilities_that_answer_for_the_customer() -> (
    None
):
    """The inquiry list and the two product abilities with a commerce object
    answer with the customer's inquiries or prices; the comparison (no price),
    the compatibility contract, the sizing hint and the team sentence are the
    same for everybody and never see the token."""
    recorder = Recorder()
    client = client_for(recorder)
    token = "40|1792300000|signature"

    for name in (
        USER_CONTEXT_ABILITY,
        "linker/search-products",
        "linker/get-product",
        "linker/compare-products",
        "linker/check-compatibility",
        "linker/size-hint",
        "linker/handoff-team",
    ):
        client.run(name, {}, token)

    carried = [
        request.url.path.split("/abilities/")[1].removesuffix("/run")
        for request in recorder.requests
        if request.headers.get(USER_CONTEXT_HEADER) == token
    ]
    assert carried == [
        "linker/inquiry-status",
        "linker/search-products",
        "linker/get-product",
    ]
    assert set(USER_CONTEXT_ABILITIES) == set(carried)


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

    with pytest.raises(AbilityError) as caught:
        client.run("linker/search-products", {})
    assert caught.value.fatal is True


def test_a_dropped_connection_is_retried_until_the_ability_answers() -> None:
    """The storm's shape: the first two calls die in transport, the third
    lands. The waits follow the exponential backoff and no error escapes."""
    flaky = Flaky(failures=2)
    clock = Clock()
    client = client_for(flaky, clock)

    assert client.run("linker/search-products", {"lang": "en"}) == {"ok": True}
    assert len(flaky.requests) == ABILITY_ATTEMPTS
    assert clock.waits == [0.25, 0.5]


def test_a_blip_between_two_500s_still_lands() -> None:
    flaky = Flaky(
        failures=2, error=httpx.ReadError("Error while reading line from the server")
    )
    clock = Clock()
    client = client_for(flaky, clock)

    assert client.run("linker/get-product", {"product_id": 1, "lang": "de"}) == {
        "ok": True
    }
    assert len(flaky.requests) == 3


def test_a_connection_that_never_returns_raises_ability_error() -> None:
    flaky = Flaky(failures=ABILITY_ATTEMPTS)
    clock = Clock()
    client = client_for(flaky, clock)

    with pytest.raises(AbilityError, match="could not be reached") as caught:
        client.run("linker/search-products", {"lang": "en"})
    assert caught.value.fatal is True
    assert len(flaky.requests) == ABILITY_ATTEMPTS
    assert clock.waits == [0.25, 0.5]


def test_a_persistent_500_is_retried_then_reported() -> None:
    recorder = Recorder(status=500, body={"message": "boom"})
    clock = Clock()
    client = client_for(recorder, clock)

    with pytest.raises(AbilityError, match="returned 500") as caught:
        client.run("linker/search-products", {})
    assert caught.value.fatal is True
    assert len(recorder.requests) == ABILITY_ATTEMPTS
    assert clock.waits == [0.25, 0.5]


def test_a_4xx_answer_is_final_and_never_retried() -> None:
    recorder = Recorder(status=404, body={"code": "rest_not_found"})
    clock = Clock()
    client = client_for(recorder, clock)

    with pytest.raises(AbilityError, match="returned 404") as caught:
        client.run("linker/search-products", {})
    assert caught.value.fatal is False
    assert len(recorder.requests) == 1
    assert clock.waits == []


def test_the_ability_name_keeps_its_slash_raw() -> None:
    """LiteSpeed answers an encoded slash with 404 (measured 2026-10-14).

    Every ability name carries one (`linker/search-products`), and the
    production site sits behind that server — the raw path is what answers.
    """
    recorder = Recorder()
    client_for(recorder).run("linker/search-products", {"text": "GoodWe"})

    raw = recorder.requests[0].url.raw_path.decode()
    assert "/abilities/linker/search-products/run" in raw
    assert "%2F" not in raw
