"""Hands the verdicts to WordPress, where the team reads them.

`POST {GENIE_WP_URL}/wp-json/linker-ai/v1/genie/quality` with the shared token
(`GENIE_JUDGE_TOKEN` here, `LINKER_GENIE_JUDGE_TOKEN` in the site's
wp-config.php) in `X-Linker-Judge-Token` — not `Authorization: Bearer`, which
LiveCanvas decodes as a JWT on every REST request and dies on (QualityRoute). The site stores each verdict on its conversation, which is
what lets a finding be traced to the conversation it came from.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

from linker_genie.abilities import ABILITY_ATTEMPTS, ABILITY_BACKOFF

ROUTE = "/wp-json/linker-ai/v1/genie/quality"
HEADER = "X-Linker-Judge-Token"

# Seconds per request: the ability client's default against the same host
# (abilities.AbilityClient); a push is a few dozen small rows.
TIMEOUT = 20.0


class PushError(RuntimeError):
    """The site did not take the verdicts; the message never carries the token."""


class WordPress:
    def __init__(
        self,
        base_url: str,
        token: str,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = base_url.rstrip("/") + ROUTE
        self._token = token
        self._client = httpx.Client(timeout=TIMEOUT, transport=transport)
        self._sleep = sleep

    def push(
        self, judgments: list[dict[str, Any]], status: dict[str, Any]
    ) -> list[int]:
        """Send verdicts and the worker's status; return the turn ids the site stored."""
        body = {"judgments": judgments, "status": status}
        headers = {HEADER: self._token}
        failure = ""
        # The ability client's retry rule (same host, same tolerance): a 5xx
        # or a transport error is retried with doubling backoff; a 4xx is not.
        for attempt in range(1, ABILITY_ATTEMPTS + 1):
            try:
                response = self._client.post(self._url, json=body, headers=headers)
            except httpx.HTTPError as error:
                failure = f"{type(error).__name__}: {error}"
            else:
                if response.status_code == 200:
                    stored = response.json().get("stored", [])
                    return [int(turn_id) for turn_id in stored]
                failure = f"HTTP {response.status_code}: {response.text[:300]}"
                if response.status_code < 500:
                    break
            if attempt < ABILITY_ATTEMPTS:
                self._sleep(ABILITY_BACKOFF * 2 ** (attempt - 1))
        raise PushError(f"{self._url}: {failure}")
