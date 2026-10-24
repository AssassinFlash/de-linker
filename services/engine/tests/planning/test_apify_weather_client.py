"""Real transport and primary-capture bytes; provider responses are simulated."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from linker_engine.planning.apify_transport import ApifyTransport
from linker_engine.planning.apify_weather_client import ApifyWeatherClient
from linker_engine.planning.canonical import Object, encode
from linker_engine.planning.weather_fetch_errors import WeatherResponseInvalid
from linker_engine.planning.weather_journal import WeatherStartUnknown
from linker_engine.planning.weather_submission import submission

from .test_apify_transport import Raw
from .test_pvgis_tmy import raw, request
from .test_weather_journal import plan, remote

NONCE = "c" * 32
ROOT = Path(__file__).resolve().parents[4]


def effective(nonce: str = NONCE) -> Object:
    baseline = json.loads(
        (
            ROOT
            / "docs/research/2026-10-24-weather-transport/raw/weather-effective-input-baseline.json"
        ).read_bytes()
    )
    baseline.update(submission(plan(), nonce))
    return cast(Object, baseline)


def provider(status: str = "SUCCEEDED", **changes: Any) -> bytes:
    run = remote(status)
    selected = {
        "id": run.id,
        "actId": run.actor_id,
        "buildId": run.build_id,
        "buildNumber": run.build_number,
        "status": run.status,
        "defaultDatasetId": run.dataset_id,
        "defaultKeyValueStoreId": run.store_id,
        "startedAt": run.started_at,
        "finishedAt": run.finished_at,
    }
    selected.update(changes)
    return encode({"data": selected})


def record() -> Object:
    run = remote("SUCCEEDED")
    return {
        "url": request().url,
        "crawl": {
            "loadedUrl": request().url,
            "loadedTime": run.finished_at,
            "httpStatusCode": 200,
            "depth": 0,
            "contentType": "application/json; charset=utf-8",
        },
        "fileUrl": f"https://api.apify.com/v2/key-value-stores/{run.store_id}/records/file-weather?signature=fixture-private-query",
        "untrusted_extra": "must-not-retain",
    }


@dataclass
class Reply:
    status: int
    body: bytes
    after: Callable[[], None] | None = None
    error: Exception | None = None


class SequenceAdapter(BaseAdapter):
    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.calls: list[requests.PreparedRequest] = []
        self.raw: list[Raw] = []

    def send(
        self, request: requests.PreparedRequest, **kwargs: Any
    ) -> requests.Response:
        self.calls.append(request)
        assert self.replies, "unexpected extra provider request"
        reply = self.replies.pop(0)
        if reply.after is not None:
            reply.after()
        if reply.error is not None:
            raise reply.error
        response = requests.Response()
        response.status_code = reply.status
        response.headers["Content-Type"] = "application/json"
        response.raw = Raw(reply.body)
        self.raw.append(response.raw)
        response.request = request
        return response

    def close(self) -> None:
        for response in self.raw:
            response.close()


def client(*replies: Reply) -> tuple[ApifyWeatherClient, SequenceAdapter]:
    adapter = SequenceAdapter(*replies)
    return ApifyWeatherClient(
        ApifyTransport(lambda: "fixture-only", plan().limits, adapter=adapter)
    ), adapter


def test_start_pins_build_cost_and_one_correlated_source_without_secret_query() -> None:
    source, adapter = client(Reply(201, provider("READY")))
    try:
        acknowledged = source.start(plan(), NONCE, lambda: None)
        sent = adapter.calls[0]
        assert acknowledged.id == remote().id and len(adapter.calls) == 1
        assert json.loads(cast(bytes, sent.body)) == submission(plan(), NONCE)
        assert parse_qs(urlsplit(sent.url or "").query) == {
            "build": ["0.3.101"],
            "timeout": ["180"],
            "memory": ["1024"],
            "restartOnError": ["false"],
            "waitForFinish": ["0"],
            "maxTotalChargeUsd": ["0.05"],
        }
    finally:
        source.transport.close()


@pytest.mark.parametrize(
    "reply",
    [
        Reply(500, b"private-error"),
        Reply(201, b'{"data":{}}'),
        Reply(201, provider(buildId="wrong")),
        Reply(201, b'{"data":{},"data":{}}'),
    ],
)
def test_start_without_verified_ack_is_always_uncertain_and_never_retried(
    reply: Reply,
) -> None:
    source, adapter = client(reply)
    try:
        with pytest.raises(WeatherStartUnknown):
            source.start(plan(), NONCE, lambda: None)
        assert len(adapter.calls) == 1
    finally:
        source.transport.close()


def test_download_preserves_exact_originals_and_strips_temporary_dataset_access() -> (
    None
):
    exact_input = json.dumps(effective(), indent=2).encode()
    source, adapter = client(
        Reply(200, exact_input), Reply(200, encode([record()])), Reply(200, raw())
    )
    try:
        downloaded = source.download(remote("SUCCEEDED"), plan(), NONCE, lambda: None)
        assert downloaded.source.content == raw()
        assert downloaded.effective_input_json == exact_input
        assert (
            downloaded.source.capture.source_identifiers["weather_intent_nonce"]
            == NONCE
        )
        assert "signature" not in downloaded.selected_dataset_record_json.decode()
        assert b"untrusted_extra" not in downloaded.selected_dataset_record_json
        assert all("signature" not in (call.url or "") for call in adapter.calls)
        assert parse_qs(urlsplit(adapter.calls[1].url or "").query)["limit"] == ["2"]
        assert (
            adapter.calls[2].url
            == f"https://api.apify.com/v2/key-value-stores/{remote().store_id}/records/file-weather"
        )
        assert all(response.closed for response in adapter.raw)
    finally:
        source.transport.close()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data.update({"pageFunction": "untrusted code"}),
        lambda data: data.update({"unknownFutureField": "private"}),
        lambda data: data.update(
            {
                "proxyConfiguration": {
                    "proxyUrls": ["http://private:secret@proxy.invalid"]
                }
            }
        ),
        lambda data: data.update({"startUrls": [{"url": request().url}]}),
        lambda data: data.update(
            {"startUrls": submission(plan(), "d" * 32)["startUrls"]}
        ),
    ],
)
def test_unsafe_or_uncorrelated_effective_input_stops_before_dataset(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    data = cast(dict[str, Any], effective())
    mutate(data)
    source, adapter = client(Reply(200, encode(data)))
    try:
        with pytest.raises(WeatherResponseInvalid):
            source.download(remote("SUCCEEDED"), plan(), NONCE, lambda: None)
        assert len(adapter.calls) == 1
    finally:
        source.transport.close()


@pytest.mark.parametrize(
    "mode",
    [
        "empty",
        "extra",
        "foreign_store",
        "foreign_origin",
        "changed_location",
        "wrong_status",
        "wrong_type",
        "encoded_key",
    ],
)
def test_dataset_mismatch_never_downloads_a_record(mode: str) -> None:
    data = cast(dict[str, Any], record())
    items: list[Any] = [data]
    if mode == "empty":
        items = []
    elif mode == "extra":
        items = [data, data]
    elif mode == "foreign_store":
        data["fileUrl"] = (
            "https://api.apify.com/v2/key-value-stores/other/records/file-weather"
        )
    elif mode == "foreign_origin":
        data["fileUrl"] = (
            "https://other.invalid/v2/key-value-stores/other/records/file-weather"
        )
    elif mode == "changed_location":
        data["crawl"]["loadedUrl"] = "https://example.invalid/"
    elif mode == "wrong_status":
        data["crawl"]["httpStatusCode"] = True
    elif mode == "wrong_type":
        data["crawl"]["contentType"] = "text/html"
    elif mode == "encoded_key":
        data["fileUrl"] = cast(str, data["fileUrl"]).replace(
            "file-weather?", "file-%2fweather?"
        )
    source, adapter = client(Reply(200, encode(effective())), Reply(200, encode(items)))
    try:
        with pytest.raises(WeatherResponseInvalid):
            source.download(remote("SUCCEEDED"), plan(), NONCE, lambda: None)
        assert len(adapter.calls) == 2
    finally:
        source.transport.close()


def test_read_and_abort_require_the_requested_provider_identity() -> None:
    source, adapter = client(Reply(200, provider()), Reply(200, provider("ABORTING")))
    try:
        with pytest.raises(WeatherResponseInvalid):
            source.read("other", lambda: None)
        with pytest.raises(WeatherResponseInvalid):
            source.abort("other", lambda: None)
        assert [call.method for call in adapter.calls] == ["GET", "POST"]
    finally:
        source.transport.close()


def test_actual_http_200_rejection_is_not_a_successful_weather_capture() -> None:
    diagnostic = json.loads(
        (
            ROOT
            / "docs/acceptance/2026-10-24/548/weather-transport/actual/rejected-origin-1/dataset-diagnostic.json"
        ).read_bytes()
    )
    actual = diagnostic["items"][0]
    assert actual["crawl"]["httpStatusCode"] == 200
    assert actual["crawl"]["contentType"] == "text/html"
    source, adapter = client(
        Reply(200, encode(effective())),
        Reply(200, encode([{"url": actual["url"], "crawl": actual["crawl"]}])),
    )
    try:
        with pytest.raises(WeatherResponseInvalid):
            source.download(remote("SUCCEEDED"), plan(), NONCE, lambda: None)
        assert len(adapter.calls) == 2
    finally:
        source.transport.close()
