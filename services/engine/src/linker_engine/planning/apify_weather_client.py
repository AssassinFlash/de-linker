"""The only endpoints needed by a pinned, correlated weather acquisition.

Primary endpoint and source contracts are retained in weather-transport and
pv-managed-intake research. Provider/default/INPUT validation precedes capture;
only the single admitted run's own record is downloaded. No direct JRC fetch,
redirect, extraction-text fallback or arbitrary file URL is supported.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlsplit

from .apify_json import apify_json
from .apify_run import ApifyRun
from .apify_transport import ApifyTransport
from .canonical import Object, encode
from .errors import PlanningError
from .pv_source import PvSource
from .pvgis_response import PvgisCapture
from .weather_download import WeatherDownload
from .weather_fetch_errors import WeatherRemoteFailed, WeatherResponseInvalid
from .weather_fetch_plan import ACTOR_ID, BUILD_NUMBER, WeatherFetchPlan
from .weather_journal import WeatherStartUnknown
from .weather_submission import checked_effective_input, submission


def _provider_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9]+", value):
        raise WeatherResponseInvalid("provider identifier is not admitted")
    return value


class ApifyWeatherClient:
    def __init__(self, transport: ApifyTransport) -> None:
        self.transport = transport

    def _reply(self, body: bytes) -> ApifyRun:
        value = apify_json(body)
        if not isinstance(value, dict):
            raise WeatherResponseInvalid("provider run envelope required")
        return ApifyRun.from_provider(value.get("data"))

    def start(
        self, plan: WeatherFetchPlan, nonce: str, guard: Callable[[], None]
    ) -> ApifyRun:
        # The caller consumes the durable permit immediately before this call.
        # No exception authorizes a repeat of this POST, even malformed success.
        try:
            response = self.transport.request(
                "POST",
                f"/v2/acts/{ACTOR_ID}/runs",
                expected_status=201,
                limit=plan.limits.max_metadata_bytes,
                guard=guard,
                parameters={
                    "build": BUILD_NUMBER,
                    "timeout": str(plan.limits.actor_timeout_seconds),
                    "memory": str(plan.limits.actor_memory_mb),
                    "restartOnError": "false",
                    "waitForFinish": "0",
                    "maxTotalChargeUsd": str(plan.limits.max_total_charge_usd),
                },
                body=submission(plan, nonce),
            )
            return self._reply(response.body)
        except PlanningError:
            raise WeatherStartUnknown(
                "the start has no verified provider acknowledgement"
            ) from None

    def read(self, run_id: str, guard: Callable[[], None]) -> ApifyRun:
        response = self.transport.request(
            "GET",
            f"/v2/actor-runs/{_provider_id(run_id)}",
            expected_status=200,
            limit=self.transport.limits.max_metadata_bytes,
            guard=guard,
        )
        run = self._reply(response.body)
        if run.id != run_id:
            raise WeatherResponseInvalid("provider read returned a different run")
        return run

    def abort(self, run_id: str, guard: Callable[[], None]) -> ApifyRun:
        response = self.transport.request(
            "POST",
            f"/v2/actor-runs/{_provider_id(run_id)}/abort",
            expected_status=200,
            limit=self.transport.limits.max_metadata_bytes,
            guard=guard,
            parameters={"gracefully": "false"},
        )
        run = self._reply(response.body)
        if run.id != run_id:
            raise WeatherResponseInvalid("provider abort returned a different run")
        return run

    def verified_input(
        self,
        run: ApifyRun,
        plan: WeatherFetchPlan,
        nonce: str,
        guard: Callable[[], None],
    ) -> bytes:
        response = self.transport.request(
            "GET",
            f"/v2/key-value-stores/{run.store_id}/records/INPUT",
            expected_status=200,
            limit=plan.limits.max_metadata_bytes,
            guard=guard,
        )
        checked_effective_input(plan, nonce, apify_json(response.body))
        return response.body

    def _record(
        self, run: ApifyRun, plan: WeatherFetchPlan, body: bytes
    ) -> tuple[Object, str]:
        items = apify_json(body)
        if (
            not isinstance(items, list)
            or len(items) != 1
            or not isinstance(items[0], dict)
        ):
            raise WeatherResponseInvalid("one exact weather file capture required")
        record = items[0]
        crawl = record.get("crawl")
        if not isinstance(crawl, dict):
            raise WeatherResponseInvalid("weather file has no origin capture")
        requested, loaded, media = (
            record.get("url"),
            crawl.get("loadedUrl"),
            crawl.get("contentType"),
        )
        if (
            not isinstance(requested, str)
            or not plan.request.matches_url(requested)
            or not isinstance(loaded, str)
            or not plan.request.matches_url(loaded)
            or type(crawl.get("httpStatusCode")) is not int
            or crawl.get("httpStatusCode") != 200
            or not isinstance(media, str)
            or media.split(";", 1)[0].strip().lower() != "application/json"
            or type(crawl.get("depth")) is not int
            or crawl.get("depth") != 0
        ):
            raise WeatherResponseInvalid(
                "weather origin differs from the exact requested JSON response"
            )
        file_url = record.get("fileUrl")
        if not isinstance(file_url, str):
            raise WeatherResponseInvalid("weather record has no original file")
        parsed = urlsplit(file_url)
        prefix = f"/v2/key-value-stores/{run.store_id}/records/"
        if (
            parsed.scheme != "https"
            or parsed.netloc != "api.apify.com"
            or parsed.fragment
            or not parsed.path.startswith(prefix)
        ):
            raise WeatherResponseInvalid(
                "weather record is not in the acknowledged run's store"
            )
        key = parsed.path[len(prefix) :]
        if not re.fullmatch(r"file-[A-Za-z0-9_-]+", key):
            raise WeatherResponseInvalid("weather file record key is not admitted")
        # Never retain or follow the temporary signature query. The subsequent
        # request reconstructs this path on the fixed origin with private auth.
        selected: Object = {
            "url": requested,
            "crawl": {
                name: crawl.get(name)
                for name in (
                    "loadedUrl",
                    "loadedTime",
                    "httpStatusCode",
                    "depth",
                    "contentType",
                )
            },
            "file_store_id": run.store_id,
            "file_record_key": key,
        }
        return selected, key

    def download(
        self,
        run: ApifyRun,
        plan: WeatherFetchPlan,
        nonce: str,
        guard: Callable[[], None],
    ) -> WeatherDownload:
        if run.status != "SUCCEEDED":
            raise WeatherRemoteFailed("only a succeeded run can supply weather")
        effective = self.verified_input(run, plan, nonce, guard)
        dataset = self.transport.request(
            "GET",
            f"/v2/datasets/{run.dataset_id}/items",
            expected_status=200,
            limit=plan.limits.max_metadata_bytes,
            guard=guard,
            # Two detects unexpected extra records rather than truncating to a
            # misleading single success. This task admits exactly one record.
            parameters={"format": "json", "offset": "0", "limit": "2"},
        )
        selected, key = self._record(run, plan, dataset.body)
        original = self.transport.request(
            "GET",
            f"/v2/key-value-stores/{run.store_id}/records/{key}",
            expected_status=200,
            limit=plan.limits.max_response_bytes,
            guard=guard,
        )
        if not isinstance(apify_json(original.body), dict):
            raise WeatherResponseInvalid("original weather must be a JSON object")
        crawl = selected["crawl"]
        assert isinstance(crawl, dict)
        capture = PvgisCapture.read(
            {
                "schema_version": 1,
                "requested_url": selected["url"],
                "loaded_url": crawl["loadedUrl"],
                "status": crawl["httpStatusCode"],
                "content_type": crawl["contentType"],
                "received_at_utc": crawl["loadedTime"],
                "capture_basis": "pinned_apify_run_verified_input_dataset_and_authenticated_original_record",
                "source_identifiers": {
                    "apify_run_id": run.id,
                    "apify_actor_id": run.actor_id,
                    "apify_build_id": run.build_id,
                    "apify_build_number": run.build_number,
                    "apify_dataset_id": run.dataset_id,
                    "apify_key_value_store_id": run.store_id,
                    "apify_record_key": key,
                    "weather_intent_nonce": nonce,
                },
            }
        )
        # JRC usage terms and attribution retained in pv-inputs research.
        provenance: Object = {
            "label": "JRC PVGIS typical meteorological year",
            "basis": "official_jrc_original_acquired_through_pinned_apify",
            "rights_basis": "JRC PVGIS usage conditions; source/database attribution and private permanent original retention",
        }
        return WeatherDownload(
            PvSource(
                original.body,
                plan.request,
                capture,
                plan.interpretation,
                encode(provenance),
            ),
            encode(submission(plan, nonce)),
            effective,
            encode(selected),
            encode(
                {"dataset": dataset.receipt(), "original_record": original.receipt()}
            ),
        )
