"""HTTP against one Genie service and the WordPress it reads.

The turn client posts the shell's body (`schema.TurnRequest`) at `POST /turn`
with `X-Linker-Service-Token` (gate.py). Page fetches are anonymous GETs, the
same read `page.py` does. Nothing here posts a contact or an inquiry.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

# The shell's proxy stops at 60 s (plugins/linker-tools includes/Genie/Proxy.php
# `post()`, `'timeout' => 60.0`, the same bound as prices.SHELL_TIMEOUT).
# 180 is the direct-service bound #330 used (services/genie/eval/baseline/run.py
# records that the trial script used 180), so a slow turn is recorded rather
# than cut. It does not extend the proxy's 60 s.
TURN_TIMEOUT = 180.0
# page.py TIMEOUT_SECONDS is 10 s for one LiveCanvas read (0.5–3.4 s measured
# 2026-10-18) and MAX_REDIRECTS is 3. 30 s is three of those reads, so this
# GET still finishes when a page follows that redirect budget. It is not a
# product timeout.
PAGE_TIMEOUT = 30.0
TOKEN_HEADER = "X-Linker-Service-Token"

_PROMPTS = re.compile(r"""data-prompts=(['"])(.*?)\1""", re.DOTALL)
_PAGE = re.compile(r"""data-page=(['"])(.*?)\1""", re.DOTALL)
# Polylang prints rel, href, then hreflang. Attribute order is not stable.
_LINK = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
_REL_ALTERNATE = re.compile(r"""\brel=["']alternate["']""", re.IGNORECASE)
_HREFLANG_DE = re.compile(r"""\bhreflang=["']de["']""", re.IGNORECASE)
_HREF = re.compile(r"""\bhref=["']([^"']+)["']""", re.IGNORECASE)
_H1 = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_MAIN = re.compile(r"<main\b[^>]*>(.*?)</main>", re.IGNORECASE | re.DOTALL)


def parse_sse(stream: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """SSE text into (meta, blocks). `done` and attachment events are dropped."""
    meta: dict[str, Any] | None = None
    blocks: list[dict[str, Any]] = []
    for event in stream.split("\n\n"):
        found = re.search(r"^data: (.+)$", event, re.MULTILINE)
        if not found:
            continue
        try:
            payload = json.loads(found.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("turn_id"), int):
            meta = payload
        elif isinstance(payload.get("type"), str):
            blocks.append(payload)
    return meta, blocks


class ServiceClient:
    """One Genie process. A turn is one POST; the caller keeps the thread."""

    def __init__(self, base: str, token: str, timeout: float = TURN_TIMEOUT) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self.timeout = timeout

    def turn(
        self,
        *,
        conversation_id: str,
        messages: list[dict[str, str]],
        locale: str,
        page: dict[str, Any],
    ) -> dict[str, Any]:
        body = {
            "conversation_id": conversation_id,
            "messages": messages,
            "locale": locale,
            "page_context": page,
            "user": {"logged_in": False, "partner": False},
        }
        raw = json.dumps(body).encode()
        request = urllib.request.Request(
            self.base + "/turn",
            data=raw,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                TOKEN_HEADER: self.token,
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:
                stream = reply.read().decode("utf-8", "replace")
                status = int(reply.status)
        except urllib.error.HTTPError as failure:
            stream = failure.read().decode("utf-8", "replace")
            status = int(failure.code)
            failure.close()
        duration = time.monotonic() - started
        meta, blocks = parse_sse(stream)
        return {
            "http": status,
            "duration_s": round(duration, 3),
            "request": body,
            "meta": meta,
            "blocks": blocks,
            "stream_bytes": len(stream),
        }


def fetch(url: str, timeout: float = PAGE_TIMEOUT) -> dict[str, Any]:
    """GET a page. The final URL is the one after redirects."""
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            body = reply.read().decode("utf-8", "replace")
            return {
                "url": str(reply.geturl()),
                "status": int(reply.status),
                "headers": {
                    key: value
                    for key, value in (
                        ("content-type", reply.headers.get("content-type")),
                        ("cache-control", reply.headers.get("cache-control")),
                    )
                    if value
                },
                "html": body,
                "error": None,
            }
    except urllib.error.HTTPError as failure:
        body = failure.read().decode("utf-8", "replace")
        failure.close()
        return {
            "url": str(failure.geturl() or url),
            "status": int(failure.code),
            "headers": {},
            "html": body,
            "error": f"HTTP {failure.code}",
        }
    except urllib.error.URLError as failure:
        return {
            "url": url,
            "status": 0,
            "headers": {},
            "html": "",
            "error": f"URLError: {failure.reason}",
        }


def _attr(html_text: str, pattern: re.Pattern[str]) -> str | None:
    found = pattern.search(html_text)
    if not found:
        return None
    return html.unescape(found.group(2))


def german_alternate(html_text: str) -> str | None:
    """The `hreflang=de` alternate, whatever order the attributes are in."""
    for tag in _LINK.findall(html_text):
        if _REL_ALTERNATE.search(tag) is None or _HREFLANG_DE.search(tag) is None:
            continue
        href = _HREF.search(tag)
        if href is not None:
            return html.unescape(href.group(1))
    return None


def mount(html_text: str) -> dict[str, Any]:
    """The dock's `data-prompts` and `data-page`, or an empty mount."""
    prompts_raw = _attr(html_text, _PROMPTS)
    page_raw = _attr(html_text, _PAGE)
    prompts: list[str] = []
    page: dict[str, Any] = {}
    if prompts_raw:
        try:
            parsed = json.loads(prompts_raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            prompts = [item for item in parsed if isinstance(item, str)]
    if page_raw:
        try:
            parsed_page = json.loads(page_raw)
        except json.JSONDecodeError:
            parsed_page = None
        if isinstance(parsed_page, dict):
            page = parsed_page
    return {
        "prompts": prompts,
        "page": page,
        "de_url": german_alternate(html_text),
    }


def h1_text(html_text: str) -> str:
    found = _H1.search(html_text)
    if not found:
        return ""
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub("", found.group(1)))).strip()


def main_text(html_text: str) -> str:
    """Visible text of `<main>`, tags removed. Empty when the page has none."""
    found = _MAIN.search(html_text)
    if not found:
        return ""
    text = _TAG.sub(" ", found.group(1))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def json_get(url: str, timeout: float = PAGE_TIMEOUT) -> Any:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as reply:
        return json.loads(reply.read().decode("utf-8", "replace"))
