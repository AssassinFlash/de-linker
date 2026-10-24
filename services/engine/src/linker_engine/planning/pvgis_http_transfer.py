"""Credential-free official GET, confined to the supervised HTTP child process."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import requests
from requests.adapters import BaseAdapter, HTTPAdapter
from urllib3.exceptions import HTTPError

from .canonical import Object, encode
from .pv_source import PvSource
from .pvgis_response import PvgisCapture
from .weather_download import WeatherDownload
from .weather_fetch_errors import (
    WeatherProviderRejected,
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from .weather_fetch_plan import WeatherFetchPlan
from .weather_journal import WeatherDeadlineExceeded

# Streaming allocation policy reused from the validated transport; no weather
# accuracy or system-sizing threshold is implied by the 64 KiB buffer.
BUFFER_BYTES = 64 * 1024


class PvgisHttpTransfer:
    def __init__(self, *, adapter: BaseAdapter | None = None) -> None:
        self.adapter = adapter if adapter is not None else HTTPAdapter(max_retries=0)
        # Only merge proxy/CA settings. A Session.send/request call could apply
        # netrc auth, cookies, redirects or hidden retries; none is used here.
        self.settings = requests.Session()

    def close(self) -> None:
        self.adapter.close()
        self.settings.close()

    def download(
        self,
        plan: WeatherFetchPlan,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> WeatherDownload:
        guard()
        remaining = deadline - clock()
        if remaining <= 0:
            raise WeatherDeadlineExceeded("weather download deadline has passed")
        request = requests.Request(
            "GET",
            plan.request.url,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        ).prepare()
        network = self.settings.merge_environment_settings(
            plan.request.url, {}, True, None, None
        )
        verify = network["verify"]
        if verify is None:
            verify = True
        if verify is False:
            raise WeatherProviderRejected(
                "official weather access requires TLS verification"
            )
        try:
            response = self.adapter.send(
                request,
                stream=True,
                timeout=(
                    min(plan.limits.connect_timeout_seconds, remaining),
                    min(plan.limits.read_timeout_seconds, remaining),
                ),
                verify=verify,
                cert=network["cert"],
                proxies=network["proxies"],
            )
            try:
                guard()
                if response.status_code in (429, 500, 502, 503, 504):
                    raise WeatherProviderUnavailable(
                        "official weather source is unavailable"
                    )
                if response.status_code != 200:
                    raise WeatherProviderRejected(
                        "official weather source rejected the request"
                    )
                content_type = response.headers.get("Content-Type", "")
                if (
                    not plan.request.matches_url(response.url or "")
                    or content_type.split(";", 1)[0].strip().lower()
                    != "application/json"
                    or response.headers.get("Content-Encoding", "identity").lower()
                    not in ("", "identity")
                ):
                    raise WeatherResponseInvalid(
                        "official weather response identity or format changed"
                    )
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    if not declared.isascii() or not declared.isdecimal():
                        raise WeatherResponseInvalid("invalid weather response length")
                    if int(declared) > plan.limits.max_response_bytes:
                        raise WeatherResponseTooLarge(
                            "weather response exceeds the configured byte budget"
                        )
                parts: list[bytes] = []
                size = 0
                while True:
                    guard()
                    chunk = response.raw.read1(
                        min(BUFFER_BYTES, plan.limits.max_response_bytes - size + 1),
                        decode_content=False,
                    )
                    guard()
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > plan.limits.max_response_bytes:
                        raise WeatherResponseTooLarge(
                            "weather response exceeds the configured byte budget"
                        )
                    parts.append(chunk)
                if declared is not None and size != int(declared):
                    raise WeatherResponseInvalid(
                        "weather response length differs from its header"
                    )
                if not size:
                    raise WeatherResponseInvalid("weather response is empty")
                received = datetime.fromtimestamp(clock(), UTC).isoformat()
                capture = PvgisCapture(
                    schema_version=1,
                    requested_url=plan.request.url,
                    loaded_url=response.url,
                    status=200,
                    content_type=content_type,
                    received_at_utc=received,
                    capture_basis="official_jrc_https_get_original_v1",
                    source_identifiers={
                        "provider": "EC_JRC_PVGIS",
                        "api_version": "5.3",
                    },
                )
                receipt = encode(capture.document())
                if len(receipt) > plan.limits.max_metadata_bytes:
                    raise WeatherResponseTooLarge(
                        "weather capture exceeds the configured metadata budget"
                    )
                provenance: Object = {
                    "label": "JRC PVGIS typical meteorological year",
                    "basis": "official_jrc_https_original",
                    "rights_basis": "JRC PVGIS usage conditions; source/database attribution and private permanent original retention",
                }
                return WeatherDownload(
                    PvSource(
                        b"".join(parts),
                        plan.request,
                        capture,
                        plan.interpretation,
                        encode(provenance),
                    ),
                    receipt,
                )
            finally:
                response.close()
        except (requests.RequestException, HTTPError, OSError) as error:
            # Exception text can include proxy credentials or response details.
            raise WeatherProviderUnavailable(
                "official weather download failed"
            ) from error
