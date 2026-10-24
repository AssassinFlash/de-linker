"""Supervise blocking DNS/TLS/HTTP work under the task's absolute deadline."""

from __future__ import annotations

import os
import selectors
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from .canonical import decode_object, encode
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

# Application cancellation polling and IPC allocation policy, not provider
# accuracy or service-level claims. Neither block may delay a task deadline.
CHECK_SECONDS = 0.05
BUFFER_BYTES = 64 * 1024
NETWORK_ENVIRONMENT = frozenset(
    name
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    )
    for name in (key, key.lower())
)
FAILURES = {
    error.code: error
    for error in (
        WeatherProviderRejected,
        WeatherProviderUnavailable,
        WeatherResponseInvalid,
        WeatherResponseTooLarge,
        WeatherDeadlineExceeded,
    )
}


class PvgisTransport:
    def close(self) -> None:
        # Each download owns and reaps its child in the same call.
        pass

    def _command(self, plan: WeatherFetchPlan, remaining: float) -> list[str]:
        return [
            sys.executable,
            "-m",
            "linker_engine.planning.weather_http_host",
            encode(plan.document()).decode(),
            str(remaining),
        ]

    def download(
        self,
        plan: WeatherFetchPlan,
        *,
        deadline: float,
        clock: Callable[[], float],
        guard: Callable[[], None],
    ) -> WeatherDownload:
        guard()
        remaining = min(deadline - clock(), plan.limits.max_elapsed_seconds)
        if remaining <= 0:
            raise WeatherDeadlineExceeded("weather download deadline has passed")
        # The monotonic bound also prevents a backwards wall-clock adjustment
        # from extending the budget frozen in the durable task.
        monotonic_deadline = time.monotonic() + remaining
        environment = {
            key: value
            for key, value in os.environ.items()
            if key in NETWORK_ENVIRONMENT
        }
        environment.update(
            PYTHONPATH=str(Path(__file__).resolve().parents[2]),
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONNOUSERSITE="1",
        )
        try:
            process = subprocess.Popen(
                self._command(plan, remaining),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=environment,
                close_fds=True,
            )
        except OSError as error:
            raise WeatherProviderUnavailable(
                "weather transfer could not start"
            ) from error
        assert process.stdout is not None
        content = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    guard()
                    remaining = min(
                        deadline - clock(), monotonic_deadline - time.monotonic()
                    )
                    if remaining <= 0:
                        raise WeatherDeadlineExceeded(
                            "weather download deadline has passed"
                        )
                    if not selector.select(min(CHECK_SECONDS, remaining)):
                        continue
                    chunk = os.read(process.stdout.fileno(), BUFFER_BYTES)
                    if not chunk:
                        break
                    content.extend(chunk)
                    if (
                        len(content)
                        > plan.limits.max_response_bytes
                        + plan.limits.max_metadata_bytes
                        + 1
                    ):
                        raise WeatherResponseTooLarge(
                            "weather transfer exceeds its byte budget"
                        )
                    header_end = content.find(b"\n")
                    if header_end < 0 and len(content) > plan.limits.max_metadata_bytes:
                        raise WeatherResponseTooLarge(
                            "weather transfer metadata exceeds its byte budget"
                        )
            guard()
            if min(deadline - clock(), monotonic_deadline - time.monotonic()) <= 0:
                raise WeatherDeadlineExceeded("weather download deadline has passed")
            return self._result(plan, bytes(content))
        finally:
            # A body read, TLS handshake or DNS resolver may ignore an HTTP
            # inactivity timeout. Killing only our owned child bounds all of
            # them and lets cancellation/lease loss release the leased worker.
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()

    @staticmethod
    def _result(plan: WeatherFetchPlan, content: bytes) -> WeatherDownload:
        header, separator, body = content.partition(b"\n")
        if not separator or len(header) > plan.limits.max_metadata_bytes:
            raise WeatherProviderUnavailable("weather transfer ended without a receipt")
        metadata = decode_object(header)
        if (
            set(metadata) == {"schema_version", "error"}
            and metadata["schema_version"] == 1
        ):
            failure = FAILURES.get(str(metadata["error"]), WeatherProviderUnavailable)
            raise failure("official weather transfer failed")
        if (
            set(metadata) != {"schema_version", "capture", "provenance"}
            or metadata["schema_version"] != 1
            or not isinstance(metadata["provenance"], dict)
            or not body
        ):
            raise WeatherResponseInvalid("weather transfer receipt is incomplete")
        if len(body) > plan.limits.max_response_bytes:
            raise WeatherResponseTooLarge("weather response exceeds its byte budget")
        capture = PvgisCapture.read(metadata["capture"])
        if (
            capture.status != 200
            or not plan.request.matches_url(capture.requested_url)
            or not plan.request.matches_url(capture.loaded_url)
            or capture.capture_basis != "official_jrc_https_get_original_v1"
            or capture.source_identifiers
            != {"provider": "EC_JRC_PVGIS", "api_version": "5.3"}
        ):
            raise WeatherResponseInvalid("weather transfer source identity changed")
        return WeatherDownload(
            PvSource(
                body,
                plan.request,
                capture,
                plan.interpretation,
                encode(metadata["provenance"]),
            ),
            encode(capture.document()),
        )
