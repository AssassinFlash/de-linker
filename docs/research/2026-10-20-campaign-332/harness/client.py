"""HTTP helpers for the local Genie service and the WordPress proxy."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from typing import Any

from sse import parse_sse

SELECTED = (
    "Date",
    "Server",
    "Content-Type",
    "X-Powered-By",
    "X-Robots-Tag",
    "Cache-Control",
)


def selected_headers(headers: list[tuple[str, str]]) -> dict[str, str]:
    by_lower = {name.lower(): value for name, value in headers}
    picked: dict[str, str] = {}
    for name in SELECTED:
        if name.lower() in by_lower:
            picked[name] = by_lower[name.lower()]
    return picked


def turn_body(case_id: str, question: str, locale: str) -> dict[str, Any]:
    return {
        "conversation_id": case_id,
        "messages": [{"role": "user", "content": question}],
        "locale": locale,
        "page_context": {
            "type": "home",
            "url": "http://127.0.0.1/",
            "title": "Linker",
        },
        "user": {"logged_in": False, "partner": False},
    }


def proxy_body(
    question: str, locale: str, attachment: dict[str, str] | None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "locale": locale,
        "messages": [{"role": "user", "content": question}],
        "page": {"type": "home", "url": "http://127.0.0.1/", "title": "Linker"},
    }
    if attachment is not None:
        body["attachments"] = [attachment]
    return body


class HttpResult:
    def __init__(
        self,
        http: int | None,
        final_url: str,
        headers: list[tuple[str, str]],
        raw: str,
        error: str | None,
        seconds: float,
    ) -> None:
        self.http = http
        self.final_url = final_url
        self.headers = headers
        self.raw = raw
        self.error = error
        self.seconds = seconds


def request_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    opener: urllib.request.OpenerDirector | None = None,
) -> HttpResult:
    data = json.dumps(payload).encode()
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            **headers,
        },
        method="POST",
    )
    started = time.monotonic()
    open_call = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_call(request, timeout=timeout) as reply:
            raw = reply.read().decode("utf-8", "replace")
            pairs = [(str(key), str(value)) for key, value in reply.headers.items()]
            status = int(getattr(reply, "status", None) or reply.code)
            return HttpResult(
                status,
                str(reply.geturl()),
                pairs,
                raw,
                None,
                time.monotonic() - started,
            )
    except urllib.error.HTTPError as failure:
        raw = failure.read().decode("utf-8", "replace")
        pairs = [(str(key), str(value)) for key, value in failure.headers.items()]
        try:
            return HttpResult(
                int(failure.code),
                str(failure.geturl()),
                pairs,
                raw,
                None,
                time.monotonic() - started,
            )
        finally:
            failure.close()
    except (urllib.error.URLError, TimeoutError, ConnectionError) as failure:
        return HttpResult(None, url, [], "", str(failure), time.monotonic() - started)


def cookie_opener() -> tuple[CookieJar, urllib.request.OpenerDirector]:
    jar = CookieJar()
    return jar, urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def wp_error(raw: str) -> tuple[str, str]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return "", raw[:300]
    if not isinstance(parsed, dict):
        return "", raw[:300]
    code = parsed.get("code")
    message = parsed.get("message")
    return (
        code if isinstance(code, str) else "",
        message if isinstance(message, str) else "",
    )


def stream_of(raw: str) -> str:
    """The SSE text, whether the body is the stream or the proxy envelope."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(parsed, dict):
        stream = parsed.get("stream")
        if isinstance(stream, str):
            return stream
    return raw


def describe(result: HttpResult) -> dict[str, Any]:
    """Fields shared by every case record. The token header is not copied."""
    code, message = (
        wp_error(result.raw) if result.http and result.http >= 400 else ("", "")
    )
    stream = "" if result.http and result.http >= 400 else stream_of(result.raw)
    parsed = parse_sse(stream) if stream else parse_sse("")
    record: dict[str, Any] = {
        "http": result.http,
        "final_url": result.final_url,
        "selected_headers": selected_headers(result.headers),
        "seconds": round(result.seconds, 3),
        "transport_error": result.error,
        "error_code": code,
        "error_message": message,
        "event_names": parsed["event_names"],
        "meta": parsed["meta"],
        "blocks": parsed["blocks"],
        "done": parsed["done"],
        "answer_text": parsed["answer_text"],
        "stream_prefix": stream[:4000],
    }
    if isinstance(parsed["meta"], dict):
        record["fallback"] = parsed["meta"].get("fallback")
        record["failures"] = parsed["meta"].get("failures")
        record["jev_error"] = parsed["meta"].get("jev_error")
        record["route"] = parsed["meta"].get("route")
        record["turn_id"] = parsed["meta"].get("turn_id")
    return record
