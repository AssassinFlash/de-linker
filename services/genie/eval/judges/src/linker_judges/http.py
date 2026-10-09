"""JSON over HTTP with timing, retries and the aihubmix credentials.

The key is read from the environment, or from the file the owner keeps it in, and is
only ever placed in the Authorization header: it is not logged, returned or raised.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# docs/specs/33-judge-bakeoff.md: the key lives here and never enters the repository.
CREDENTIALS_FILE = Path("~/.config/terravolt-builder/aihubmix.env").expanduser()

# A transient failure is retried at most three times, as in the JEV-as-a-Judge protocol
# (arXiv:2609.26550 §4); every attempt is kept in the record.
MAX_ATTEMPTS = 3
RETRY_STATUS = frozenset({429, 500, 502, 503, 504, 520, 529})


class HttpError(RuntimeError):
    """A request that failed after its retries; the message never carries the key."""


@dataclass(frozen=True)
class Response:
    body: dict[str, Any]
    seconds: float
    attempts: int
    started_at: float


def aihubmix_credentials() -> tuple[str, str]:
    """(base URL, key) from the environment, else from the owner's credentials file."""
    values = dict(os.environ)
    if "AIHUBMIX_API_KEY" not in values and CREDENTIALS_FILE.exists():
        for line in CREDENTIALS_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                name = name.strip().removeprefix("export ").strip()
                values.setdefault(name, value.strip().strip("'\""))
    key = values.get("AIHUBMIX_API_KEY", "")
    if not key:
        raise HttpError(f"AIHUBMIX_API_KEY is not set and {CREDENTIALS_FILE} has none")
    base = values.get("AIHUBMIX_BASE_URL", "https://aihubmix.com").rstrip("/")
    return base, key


def post_json(
    url: str, body: dict[str, Any], key: str | None = None, timeout: float = 300.0
) -> Response:
    """POST `body`; retry transient failures; return the parsed body and the wall time.

    `seconds` is the last attempt's time from sending to the full response; a proxy or
    a local server's queue is part of it. `started_at` is that attempt's Unix time.
    """
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    # A local judge server must not be routed through the machine's HTTP proxy.
    local = url.startswith(("http://127.0.0.1", "http://localhost"))
    opener = urllib.request.build_opener(
        *([urllib.request.ProxyHandler({})] if local else [])
    )
    failure = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        started = time.time()
        clock = time.perf_counter()
        try:
            with opener.open(request, timeout=timeout) as reply:
                raw = reply.read()
            seconds = time.perf_counter() - clock
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise HttpError(f"{url}: response is not a JSON object")
            return Response(parsed, seconds, attempt, started)
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            failure = f"HTTP {error.code}: {detail}"
            if error.code not in RETRY_STATUS:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            failure = f"{type(error).__name__}: {error}"
        if attempt < MAX_ATTEMPTS:
            time.sleep(2.0 * attempt)
    raise HttpError(f"{url}: {failure}")
