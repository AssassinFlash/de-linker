"""Official-origin streaming and failure contracts; no research credentials."""

from __future__ import annotations

import io
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import pytest
import requests
from requests.adapters import BaseAdapter
from urllib3.response import HTTPResponse

from linker_engine.planning.pvgis_transport import PvgisTransport
from linker_engine.planning.weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from linker_engine.planning.weather_fetch_plan import (
    WeatherFetchLimits,
    WeatherFetchPlan,
)
from linker_engine.planning.weather_journal import WeatherDeadlineExceeded

from .test_pv_profile import LIMITS
from .test_pvgis_tmy import interpretation, raw, request


def plan() -> WeatherFetchPlan:
    # Isolated operational test budgets; no engineering or provider SLA claim.
    return WeatherFetchPlan(
        schema_version=1,
        kind="pvgis_tmy_official_https_acquisition_v1",
        request=request(),
        interpretation=interpretation(),
        limits=WeatherFetchLimits(
            max_response_bytes=2_000_000,
            max_metadata_bytes=100_000,
            max_weather_rows=9000,
            connect_timeout_seconds=5,
            read_timeout_seconds=20,
            max_elapsed_seconds=60,
        ),
    )


@dataclass
class Reply:
    status: int
    body: bytes
    headers: dict[str, str] = field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    loaded_url: str | None = None


class SequenceAdapter(BaseAdapter):
    def __init__(
        self, *replies: Reply, on_send: Callable[[], None] | None = None
    ) -> None:
        self.replies = list(replies)
        self.calls: list[requests.PreparedRequest] = []
        self.on_send = on_send
        self.closed = False

    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        self.calls.append(request)
        assert request.method == "GET"
        assert request.url and request.url.startswith(
            "https://re.jrc.ec.europa.eu/api/v5_3/tmy?"
        )
        assert (
            "Authorization" not in request.headers and "Cookie" not in request.headers
        )
        assert stream is True and verify is not False
        if self.on_send:
            self.on_send()
        reply = self.replies.pop(0)
        response = requests.Response()
        response.status_code = reply.status
        response.headers.update(reply.headers)
        response.url = reply.loaded_url or request.url
        response.request = request
        response.raw = HTTPResponse(body=io.BytesIO(reply.body), preload_content=False)
        return response

    def close(self) -> None:
        self.closed = True


def test_one_official_get_needs_no_research_or_service_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("APIFY_TOKEN", "APIFY_API_TOKEN", "GENIE_SERVICE_TOKEN"):
        monkeypatch.setenv(name, "synthetic-never-forward")
    adapter = SequenceAdapter(Reply(200, raw()))
    transport = PvgisTransport(adapter=adapter)
    downloaded = transport.download(
        plan(), deadline=60, clock=lambda: 0, guard=lambda: None
    )
    assert downloaded.source.content == raw()
    assert (
        downloaded.source.capture.capture_basis == "official_jrc_https_get_original_v1"
    )
    assert len(adapter.calls) == 1
    assert b"synthetic-never-forward" not in downloaded.transport_json
    downloaded.source.weather(LIMITS)
    transport.close()
    assert adapter.closed


@pytest.mark.parametrize("status", [301, 302, 403, 404])
def test_redirects_and_rejections_are_not_followed(status: int) -> None:
    adapter = SequenceAdapter(
        Reply(status, b"denied", {"Location": "https://foreign.invalid"})
    )
    with pytest.raises(WeatherProviderRejected):
        PvgisTransport(adapter=adapter).download(
            plan(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
    assert len(adapter.calls) == 1


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_transient_source_failure_is_explicit_and_not_retried_by_transport(
    status: int,
) -> None:
    adapter = SequenceAdapter(Reply(status, b"unavailable"))
    with pytest.raises(WeatherProviderUnavailable):
        PvgisTransport(adapter=adapter).download(
            plan(), deadline=60, clock=lambda: 0, guard=lambda: None
        )
    assert len(adapter.calls) == 1


@pytest.mark.parametrize(
    "reply",
    [
        Reply(200, b"<html>refused</html>", {"Content-Type": "text/html"}),
        Reply(
            200,
            b"compressed",
            {"Content-Type": "application/json", "Content-Encoding": "gzip"},
        ),
        Reply(200, b"{}", {"Content-Type": "application/json", "Content-Length": "1"}),
        Reply(200, b"{}", loaded_url="https://foreign.invalid/tmy"),
        Reply(200, b""),
    ],
)
def test_wrong_original_identity_or_incomplete_body_is_not_accepted(
    reply: Reply,
) -> None:
    with pytest.raises(WeatherResponseInvalid):
        PvgisTransport(adapter=SequenceAdapter(reply)).download(
            plan(), deadline=60, clock=lambda: 0, guard=lambda: None
        )


def test_streaming_byte_budget_and_original_elapsed_deadline() -> None:
    selected = plan()
    selected = selected.model_copy(
        update={
            "limits": selected.limits.model_copy(
                update={"max_response_bytes": 10, "max_metadata_bytes": 5}
            )
        }
    )
    adapter = SequenceAdapter(Reply(200, b"x" * 11))
    with pytest.raises(WeatherResponseTooLarge):
        PvgisTransport(adapter=adapter).download(
            selected, deadline=60, clock=lambda: 0, guard=lambda: None
        )
    empty = SequenceAdapter()
    with pytest.raises(WeatherDeadlineExceeded):
        PvgisTransport(adapter=empty).download(
            plan(), deadline=60, clock=lambda: 60, guard=lambda: None
        )
    assert not empty.calls
