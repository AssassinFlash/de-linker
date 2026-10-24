"""The real HTTP adapter seam, bounded wire reads and independent decoded budgets."""

from __future__ import annotations

import gzip
from collections.abc import Callable
from io import BytesIO
from typing import Any

import pytest
import requests
from requests.adapters import BaseAdapter
from urllib3.exceptions import ReadTimeoutError

from linker_engine.planning.apify_transport import ApifyTransport
from linker_engine.planning.errors import LeaseLost, VersionUnavailable
from linker_engine.planning.weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from linker_engine.planning.worker import Control

from .test_weather_journal import plan


class Raw(BytesIO):
    def __init__(
        self,
        data: bytes,
        *,
        forbidden: bool = False,
        after_read: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(data)
        self.reads = 0
        self.forbidden = forbidden
        self.after_read = after_read

    def read1(self, amt: int = -1, *, decode_content: bool = False) -> bytes:
        assert not self.forbidden, "redirect/error body must not be read"
        assert decode_content is False
        self.reads += 1
        result = super().read1(amt)
        if self.after_read is not None:
            self.after_read()
        return result


class Adapter(BaseAdapter):
    def __init__(
        self,
        raw: Raw,
        *,
        status: int = 200,
        media: str = "application/json",
        encoding: str = "identity",
        error: Exception | None = None,
    ) -> None:
        self.raw = raw
        self.status = status
        self.media = media
        self.encoding = encoding
        self.error = error
        self.calls: list[requests.PreparedRequest] = []
        self.settings: list[dict[str, Any]] = []

    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        self.calls.append(request)
        self.settings.append(kwargs)
        if self.error is not None:
            raise self.error
        response = requests.Response()
        response.status_code = self.status
        response.headers.update(
            {"Content-Type": self.media, "Content-Encoding": self.encoding}
        )
        response.raw = self.raw
        response.request = request
        return response

    def close(self) -> None:
        self.raw.close()


def get(
    adapter: Adapter, *, limit: int = 100, guard: Callable[[], None] = lambda: None
):
    transport = ApifyTransport(
        lambda: "weather-fixture-only", plan().limits, adapter=adapter
    )
    try:
        return transport.request(
            "GET", "/v2/actor-runs/test", expected_status=200, limit=limit, guard=guard
        )
    finally:
        transport.close()


def test_direct_adapter_preserves_original_body_and_private_header_without_session_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Session request/redirect handling must not run")

    monkeypatch.setattr(requests.Session, "request", forbidden)
    monkeypatch.setattr(requests.Session, "resolve_redirects", forbidden)
    raw = Raw(b'{ "original" : 1 }\n')
    adapter = Adapter(raw)
    reply = get(adapter)
    assert reply.body == b'{ "original" : 1 }\n'
    assert reply.receipt()["encoded_bytes"] == reply.receipt()["decoded_bytes"] == 19
    request = adapter.calls[0]
    assert request.url == "https://api.apify.com/v2/actor-runs/test"
    assert request.headers["Authorization"] == "Bearer weather-fixture-only"
    assert (
        "token" not in request.url and request.headers["Accept-Encoding"] == "identity"
    )
    assert adapter.settings[0]["stream"] is True and adapter.settings[0]["timeout"] == (
        5,
        20,
    )
    assert raw.closed


@pytest.mark.parametrize("status", [301, 302, 307, 401, 404, 429, 500])
def test_non_success_response_is_closed_before_any_body_read(status: int) -> None:
    raw = Raw(b"unbounded private error/redirect body", forbidden=True)
    adapter = Adapter(raw, status=status)
    expected = (
        WeatherProviderUnavailable
        if status == 429 or status >= 500
        else WeatherProviderRejected
    )
    with pytest.raises(expected):
        get(adapter)
    assert raw.reads == 0 and raw.closed and len(adapter.calls) == 1


@pytest.mark.parametrize(
    "body,encoding", [(b"a" * 101, "identity"), (gzip.compress(b"a" * 10000), "gzip")]
)
def test_encoded_and_decoded_byte_budgets_are_enforced(
    body: bytes, encoding: str
) -> None:
    raw = Raw(body)
    adapter = Adapter(raw, encoding=encoding)
    with pytest.raises(WeatherResponseTooLarge):
        get(adapter, limit=100)
    assert raw.closed


def test_complete_gzip_is_decoded_once_and_receipt_keeps_both_lengths() -> None:
    original = b'{"payload":"' + b"a" * 1000 + b'"}'
    compressed = gzip.compress(original)
    reply = get(Adapter(Raw(compressed), encoding="gzip"), limit=2000)
    assert reply.body == original
    assert reply.encoded_bytes == len(compressed) and len(reply.body) == len(original)


@pytest.mark.parametrize(
    "payload",
    [
        gzip.compress(b"{}")[0:-3],
        gzip.compress(b"{}") + gzip.compress(b"{}"),
        b"invalid gzip",
    ],
)
def test_truncated_multiple_or_invalid_compression_fails(payload: bytes) -> None:
    with pytest.raises(WeatherResponseInvalid):
        get(Adapter(Raw(payload), encoding="gzip"))


@pytest.mark.parametrize(
    "media,encoding", [("text/html", "identity"), ("application/json", "br")]
)
def test_unexpected_format_fails_before_read(media: str, encoding: str) -> None:
    raw = Raw(b"not admitted", forbidden=True)
    with pytest.raises(WeatherResponseInvalid):
        get(Adapter(raw, media=media, encoding=encoding))
    assert raw.reads == 0


def test_checkpoint_interrupts_after_network_block_and_closes_body() -> None:
    control = Control()
    raw = Raw(b"{}", after_read=control.revoke)
    with pytest.raises(LeaseLost):
        get(Adapter(raw), guard=control.checkpoint)
    assert raw.reads == 1 and raw.closed


@pytest.mark.parametrize(
    "error",
    [
        requests.ConnectionError("private sentinel"),
        ReadTimeoutError(None, "https://api.apify.com", "private sentinel"),
    ],
)
def test_transport_failure_has_no_retry_or_private_exception_text(
    error: Exception,
) -> None:
    adapter = Adapter(Raw(b""), error=error)
    with pytest.raises(WeatherProviderUnavailable) as caught:
        get(adapter)
    assert "sentinel" not in str(caught.value) and len(adapter.calls) == 1


@pytest.mark.parametrize(
    "path,parameters",
    [
        ("https://example.invalid/", {}),
        ("/v2/actor-runs/../test", {}),
        ("/v2/actor-runs/test", {"token": "never-in-query"}),
    ],
)
def test_origin_and_secret_query_are_fixed_before_adapter(
    path: str, parameters: dict[str, str]
) -> None:
    adapter = Adapter(Raw(b"{}"))
    transport = ApifyTransport(lambda: "fixture-only", plan().limits, adapter=adapter)
    try:
        with pytest.raises(WeatherResponseInvalid):
            transport.request(
                "GET",
                path,
                expected_status=200,
                limit=100,
                guard=lambda: None,
                parameters=parameters,
            )
        assert adapter.calls == []
    finally:
        transport.close()


def test_empty_credential_does_not_send_a_request() -> None:
    adapter = Adapter(Raw(b"{}"))
    transport = ApifyTransport(lambda: "", plan().limits, adapter=adapter)
    try:
        with pytest.raises(VersionUnavailable):
            transport.request(
                "GET",
                "/v2/actor-runs/test",
                expected_status=200,
                limit=100,
                guard=lambda: None,
            )
        assert adapter.calls == []
    finally:
        transport.close()
