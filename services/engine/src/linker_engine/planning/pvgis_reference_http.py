"""Credential-free bounded JRC GET inside the owned supervised child.

The existing TMY transfer is the reference pattern; this adapter keeps the
seriescalc request/source types distinct instead of constructing a false TMY.
"""

from collections.abc import Callable
from datetime import UTC, datetime

import requests
from requests.adapters import BaseAdapter, HTTPAdapter
from urllib3.exceptions import HTTPError

from .pvgis_reference_download import ReferenceCapture
from .pvgis_request import PvgisRequest
from .pvgis_response import PvgisCapture
from .weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from .weather_fetch_plan import WeatherFetchLimits
from .weather_journal import WeatherDeadlineExceeded

# Same bounded streaming allocation policy as the existing official transfer.
BUFFER_BYTES = 64 * 1024


class PvgisReferenceHttp:
    def __init__(self, adapter: BaseAdapter | None = None) -> None:
        self.adapter = adapter if adapter is not None else HTTPAdapter(max_retries=0)
        self.settings = requests.Session()

    def close(self) -> None:
        self.adapter.close()
        self.settings.close()

    def download(
        self,
        request: PvgisRequest,
        limits: WeatherFetchLimits,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> ReferenceCapture:
        guard()
        remaining = deadline - clock()
        if remaining <= 0:
            raise WeatherDeadlineExceeded("reference acquisition deadline passed")
        prepared = requests.Request(
            "GET",
            request.url,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        ).prepare()
        network = self.settings.merge_environment_settings(
            request.url, {}, True, None, None
        )
        verify = network["verify"]
        if verify is False:
            raise WeatherProviderRejected(
                "official acquisition requires TLS verification"
            )
        try:
            response = self.adapter.send(
                prepared,
                stream=True,
                timeout=(
                    min(limits.connect_timeout_seconds, remaining),
                    min(limits.read_timeout_seconds, remaining),
                ),
                verify=True if verify is None else verify,
                cert=network["cert"],
                proxies=network["proxies"],
            )
            try:
                guard()
                if response.status_code in (429, 500, 502, 503, 504):
                    raise WeatherProviderUnavailable(
                        "official PVGIS source unavailable"
                    )
                if response.status_code != 200:
                    raise WeatherProviderRejected("official PVGIS request rejected")
                content_type = response.headers.get("Content-Type", "")
                if (
                    not request.matches_url(response.url or "")
                    or content_type.split(";", 1)[0].strip().lower()
                    != "application/json"
                    or response.headers.get("Content-Encoding", "identity").lower()
                    not in ("", "identity")
                ):
                    raise WeatherResponseInvalid(
                        "PVGIS response identity or format changed"
                    )
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    if not declared.isascii() or not declared.isdecimal():
                        raise WeatherResponseInvalid("invalid PVGIS response length")
                    if int(declared) > limits.max_response_bytes:
                        raise WeatherResponseTooLarge(
                            "PVGIS response exceeds byte budget"
                        )
                parts: list[bytes] = []
                size = 0
                while True:
                    guard()
                    chunk = response.raw.read1(
                        min(BUFFER_BYTES, limits.max_response_bytes - size + 1),
                        decode_content=False,
                    )
                    guard()
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limits.max_response_bytes:
                        raise WeatherResponseTooLarge(
                            "PVGIS response exceeds byte budget"
                        )
                    parts.append(chunk)
                if not size or (declared is not None and int(declared) != size):
                    raise WeatherResponseInvalid("PVGIS response body is incomplete")
                return ReferenceCapture(
                    b"".join(parts),
                    PvgisCapture(
                        schema_version=1,
                        requested_url=request.url,
                        loaded_url=response.url,
                        status=200,
                        content_type=content_type,
                        received_at_utc=datetime.fromtimestamp(
                            clock(), UTC
                        ).isoformat(),
                        capture_basis="official_jrc_https_get_original_v1",
                        source_identifiers={
                            "provider": "EC_JRC_PVGIS",
                            "api_version": "5.3",
                        },
                    ),
                )
            finally:
                response.close()
        except (requests.RequestException, HTTPError, OSError) as error:
            raise WeatherProviderUnavailable(
                "official PVGIS transfer failed"
            ) from error
