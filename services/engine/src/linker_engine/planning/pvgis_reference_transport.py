"""One owned subprocess per request; cancellation reaps only that subprocess."""

import os
import selectors
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from .canonical import decode_object, encode
from .pvgis_reference_download import ReferenceCapture
from .pvgis_request import PvgisRequest
from .pvgis_response import PvgisCapture
from .pvgis_transport import BUFFER_BYTES, CHECK_SECONDS, FAILURES, NETWORK_ENVIRONMENT
from .weather_fetch_errors import (
    WeatherProviderUnavailable,
    WeatherResponseInvalid,
    WeatherResponseTooLarge,
)
from .weather_fetch_plan import WeatherFetchLimits
from .weather_journal import WeatherDeadlineExceeded


class PvgisReferenceTransport:
    def close(self) -> None:
        pass

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
        remaining = min(deadline - clock(), limits.max_elapsed_seconds)
        if remaining <= 0:
            raise WeatherDeadlineExceeded("reference acquisition deadline passed")
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
                [
                    sys.executable,
                    "-m",
                    "linker_engine.planning.pvgis_reference_http_host",
                    encode(
                        {
                            "request": request.document(),
                            "limits": limits.model_dump(mode="json"),
                        }
                    ).decode(),
                    str(remaining),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=environment,
                close_fds=True,
            )
        except OSError as error:
            raise WeatherProviderUnavailable(
                "reference transfer could not start"
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
                            "reference acquisition deadline passed"
                        )
                    if not selector.select(min(CHECK_SECONDS, remaining)):
                        continue
                    chunk = os.read(process.stdout.fileno(), BUFFER_BYTES)
                    if not chunk:
                        break
                    content.extend(chunk)
                    if (
                        len(content)
                        > limits.max_response_bytes + limits.max_metadata_bytes + 1
                    ):
                        raise WeatherResponseTooLarge(
                            "reference transfer exceeds byte budget"
                        )
                    if (
                        content.find(b"\n") < 0
                        and len(content) > limits.max_metadata_bytes
                    ):
                        raise WeatherResponseTooLarge(
                            "reference receipt exceeds byte budget"
                        )
            guard()
            if min(deadline - clock(), monotonic_deadline - time.monotonic()) <= 0:
                raise WeatherDeadlineExceeded("reference acquisition deadline passed")
            return self._result(request, limits, bytes(content))
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()

    @staticmethod
    def _result(
        request: PvgisRequest, limits: WeatherFetchLimits, content: bytes
    ) -> ReferenceCapture:
        header, separator, body = content.partition(b"\n")
        if not separator or len(header) > limits.max_metadata_bytes:
            raise WeatherProviderUnavailable("reference transfer ended without receipt")
        metadata = decode_object(header)
        if (
            set(metadata) == {"schema_version", "error"}
            and metadata["schema_version"] == 1
        ):
            failure = FAILURES.get(str(metadata["error"]), WeatherProviderUnavailable)
            raise failure("official PVGIS transfer failed")
        if (
            set(metadata) != {"schema_version", "capture"}
            or metadata["schema_version"] != 1
            or not body
        ):
            raise WeatherResponseInvalid("reference receipt is incomplete")
        if len(body) > limits.max_response_bytes:
            raise WeatherResponseTooLarge("reference response exceeds byte budget")
        capture = PvgisCapture.read(metadata["capture"])
        if (
            capture.status != 200
            or capture.content_type.split(";", 1)[0].strip().lower()
            != "application/json"
            or not request.matches_url(capture.requested_url)
            or not request.matches_url(capture.loaded_url)
            or capture.capture_basis != "official_jrc_https_get_original_v1"
            or capture.source_identifiers
            != {"provider": "EC_JRC_PVGIS", "api_version": "5.3"}
        ):
            raise WeatherResponseInvalid("reference capture identity changed")
        return ReferenceCapture(body, capture)
