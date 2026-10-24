"""Fixed-origin authenticated HTTP with no redirects, retry or unbounded decode.

The pinned requests/urllib3 source contract is retained in the weather-transport
research. Use HTTPAdapter.send directly: Session's redirect preparation can
consume an entire redirect body even with stream=True/allow_redirects=False.
Raw read1 plus bounded gzip decoding provides a checkpoint per received block,
including compressed blocks that produce no output. Timeouts are connection
and read inactivity bounds; the caller's persisted deadline is checked between
network reads, not advertised as a hard real-time transport guarantee.
"""

from __future__ import annotations

import re
import zlib
from collections.abc import Callable
from typing import Literal

import requests
from requests.adapters import BaseAdapter, HTTPAdapter
from urllib3.exceptions import HTTPError

from .access import positive_integer
from .apify_response import ApifyResponse
from .canonical import Object, encode
from .errors import VersionUnavailable
from .weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from .weather_fetch_plan import WeatherFetchLimits

ORIGIN = "https://api.apify.com"
# An application streaming buffer, not a source/data accuracy threshold.
BUFFER_BYTES = 64 * 1024


class ApifyTransport:
    def __init__(
        self,
        credential: Callable[[], str],
        limits: WeatherFetchLimits,
        *,
        adapter: BaseAdapter | None = None,
    ) -> None:
        self._credential = credential
        self.limits = WeatherFetchLimits.read(limits.model_dump(mode="json"))
        self._adapter = adapter if adapter is not None else HTTPAdapter(max_retries=0)
        # Only use environment TLS/proxy settings. No Session request/redirect,
        # cookie or netrc authentication processing can replace the Bearer.
        self._settings = requests.Session()

    def ensure_credential(self) -> None:
        self._token()

    def _token(self) -> str:
        value = self._credential()
        if not isinstance(value, str) or not value or any(c.isspace() for c in value):
            raise VersionUnavailable("Apify credential is absent or malformed")
        return value

    def close(self) -> None:
        self._adapter.close()
        self._settings.close()

    def request(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        expected_status: int,
        limit: int,
        guard: Callable[[], None],
        parameters: dict[str, str] | None = None,
        body: Object | None = None,
    ) -> ApifyResponse:
        positive_integer(limit, "Apify response byte budget")
        if method not in ("GET", "POST") or limit > self.limits.max_response_bytes:
            raise WeatherResponseInvalid("unapproved Apify method or byte budget")
        if not re.fullmatch(r"/v2/[A-Za-z0-9/_-]+", path) or any(
            key.lower() in ("token", "authorization") for key in (parameters or {})
        ):
            raise WeatherResponseInvalid("unapproved Apify endpoint or query")
        guard()
        headers = {
            "Authorization": "Bearer " + self._token(),
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        prepared = requests.Request(
            method,
            ORIGIN + path,
            params=parameters,
            headers=headers,
            data=encode(body) if body is not None else None,
        ).prepare()
        settings = self._settings.merge_environment_settings(
            prepared.url or ORIGIN, {}, True, True, None
        )
        verify = settings["verify"]
        if verify is None:
            verify = True
        try:
            response = self._adapter.send(
                prepared,
                stream=True,
                timeout=(
                    self.limits.connect_timeout_seconds,
                    self.limits.read_timeout_seconds,
                ),
                verify=verify,
                cert=settings["cert"],
                proxies=settings["proxies"],
            )
            try:
                if response.status_code != expected_status:
                    # Reject a redirect before reading even one body byte.
                    # POST starts are classified as uncertain by the client.
                    if response.status_code == 429 or response.status_code >= 500:
                        raise WeatherProviderUnavailable(
                            "Apify returned a transient HTTP status"
                        )
                    raise WeatherProviderRejected(
                        "Apify returned an unexpected HTTP status"
                    )
                media_type = response.headers.get("Content-Type", "")
                if media_type.split(";", 1)[0].strip().lower() != "application/json":
                    raise WeatherResponseInvalid("Apify response is not JSON")
                encoding = (
                    response.headers.get("Content-Encoding", "identity").strip().lower()
                )
                if encoding not in ("identity", "gzip"):
                    raise WeatherResponseInvalid("unsupported Apify content encoding")
                decoder = (
                    zlib.decompressobj(16 + zlib.MAX_WBITS)
                    if encoding == "gzip"
                    else None
                )
                content = bytearray()
                received = 0
                while True:
                    guard()
                    chunk = response.raw.read1(
                        min(BUFFER_BYTES, limit - received + 1), decode_content=False
                    )
                    if not isinstance(chunk, bytes):
                        raise WeatherResponseInvalid(
                            "Apify transport did not return bytes"
                        )
                    guard()
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > limit:
                        raise WeatherResponseTooLarge(
                            "encoded Apify response exceeds its byte budget"
                        )
                    decoded = (
                        decoder.decompress(chunk, limit - len(content) + 1)
                        if decoder
                        else chunk
                    )
                    content.extend(decoded)
                    if len(content) > limit:
                        raise WeatherResponseTooLarge(
                            "decoded Apify response exceeds its byte budget"
                        )
                    if decoder and decoder.unused_data:
                        raise WeatherResponseInvalid(
                            "multiple or trailing gzip payloads are not admitted"
                        )
                if decoder and not decoder.eof:
                    raise WeatherResponseInvalid("truncated gzip response")
                if not content:
                    raise WeatherResponseInvalid("empty Apify response")
                return ApifyResponse(
                    bytes(content), response.status_code, media_type, encoding, received
                )
            finally:
                response.close()
        except (requests.RequestException, HTTPError, OSError):
            # Do not include exception strings/response bodies/proxy credentials.
            raise WeatherProviderUnavailable(
                "Apify transport did not complete"
            ) from None
        except zlib.error:
            raise WeatherResponseInvalid("invalid gzip response") from None
