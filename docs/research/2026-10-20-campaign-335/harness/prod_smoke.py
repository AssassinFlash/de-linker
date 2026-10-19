"""Production smoke for #335. This client writes, then deletes what it wrote.

Two question-only turns, one English and one German, through the public
proxy (`POST /wp-json/linker-ai/v1/genie/turn`). A production host is refused
unless `--confirm-production` is passed. The check is the requested host and
again the host after each redirect: a 307 or 308 keeps the POST body, so a
local URL that redirects to de-linker.com would write production. Each probe
records the final URL after redirects, the selected response headers
(including a LiteSpeed cache header when the site sends one), then DELETEs
that conversation.

No page is edited. Inquiry and contact routes are not called.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import client
import grade

ROUTE = "/wp-json/linker-ai/v1/genie/turn"
DELETE_ROUTE = "/wp-json/linker-ai/v1/genie/conversations"
READ_ROUTE = "/wp-json/linker-ai/v1/genie/conversation"
CONVERSATION_COOKIE = "linker_conversation"
PRODUCTION_HOSTS = frozenset({"de-linker.com", "www.de-linker.com"})
SELECTED_HEADERS = (
    "Date",
    "Server",
    "X-Powered-By",
    "Content-Type",
    "X-Robots-Tag",
    "Link",
    "Location",
    "X-LiteSpeed-Cache",
    "X-LiteSpeed-Cache-Control",
    "X-LiteSpeed-Tag",
)
# Client socket timeout. The site proxy stops at 60 s
# (plugins/linker-tools includes/Genie/Proxy.php `post()`, `'timeout' => 60.0`,
# prices.SHELL_TIMEOUT). 180 is the original trial client's bound
# (services/genie/eval/baseline/run.py: the trial script used 180), so the
# client is still waiting when a slow proxy returns its own 60 s timeout.
# It does not extend that proxy timeout.
PROD_TIMEOUT = 180.0

PROBES: list[dict[str, Any]] = [
    {
        "id": "P-EN",
        "locale": "en",
        "messages": [
            {"role": "user", "content": "Which batteries pair with the SAJ H2-10K-T3?"}
        ],
    },
    {
        "id": "P-DE",
        "locale": "de",
        "messages": [
            {
                "role": "user",
                "content": "Welche Batterien passen zum SAJ H2-10K-T3?",
            }
        ],
    },
]


class RedirectRecord(urllib.request.HTTPRedirectHandler):
    """Remembers each hop. A 307 or 308 on POST keeps the method and body.

    A hop whose host is the public site is not followed unless this probe
    was allowed to write production. Returning None leaves the 307/308
    response unfollowed, so the POST body is not sent there.
    """

    def __init__(self, *, allow_production: bool = False) -> None:
        super().__init__()
        self.allow_production = allow_production
        self.hops: list[dict[str, object]] = []
        self.blocked_production: str | None = None

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        self.hops.append({"status": code, "from": req.full_url, "location": newurl})
        if is_production(newurl) and not self.allow_production:
            self.blocked_production = newurl
            return None
        if code in (307, 308) and req.get_method() not in ("GET", "HEAD"):
            kept = {
                key: value
                for key, value in req.headers.items()
                if key.lower() != "content-length"
            }
            return urllib.request.Request(
                newurl.replace(" ", "%20"),
                data=req.data,
                headers=kept,
                origin_req_host=req.origin_req_host,
                unverifiable=True,
                method=req.get_method(),
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def is_production(site: str) -> bool:
    """True for the public site, including a trailing-dot or uppercase host."""
    host = (urllib.parse.urlparse(site).hostname or "").lower().rstrip(".")
    return host in PRODUCTION_HOSTS


def selected_headers(headers: list[tuple[str, str]]) -> dict[str, str]:
    by_lower = {name.lower(): value for name, value in headers}
    picked: dict[str, str] = {}
    for name in SELECTED_HEADERS:
        if name.lower() in by_lower:
            picked[name] = by_lower[name.lower()]
    return picked


def delete_conversation(
    opener: urllib.request.OpenerDirector, site: str, conversation_id: int
) -> int | None:
    """DELETE the conversation this probe's cookie opened.

    before_delete_post can call the service forget endpoint inside the proxy's
    60 s bound (Proxy::forget). The client waits PROD_TIMEOUT, the same 180 s
    as the turn, so that forget is not cut by an unsourced 30 s. 180 does not
    extend the proxy's 60 s.
    """
    url = f"{site.rstrip('/')}{DELETE_ROUTE}/{conversation_id}"
    request = urllib.request.Request(url, method="DELETE")
    try:
        with opener.open(request, timeout=PROD_TIMEOUT) as reply:
            reply.read()
            return int(reply.status)
    except urllib.error.HTTPError as failure:
        try:
            return int(failure.code)
        finally:
            failure.close()
    except urllib.error.URLError:
        return None


def cookie_conversation_id(jar: http.cookiejar.CookieJar) -> int | None:
    for cookie in jar:
        if cookie.name != CONVERSATION_COOKIE:
            continue
        head = (cookie.value or "").split(".", 1)[0]
        if head.isdigit() and int(head) > 0:
            return int(head)
    return None


def envelope_of(body: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    if not isinstance(parsed.get("conversation_id"), int):
        return None
    if parsed["conversation_id"] <= 0:
        return None
    if not isinstance(parsed.get("stream"), str):
        return None
    return parsed


def read_conversation_id(
    opener: urllib.request.OpenerDirector, site: str, timeout: float
) -> int | None:
    url = site.rstrip("/") + READ_ROUTE
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=timeout) as reply:
            body = reply.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as failure:
        try:
            body = failure.read().decode("utf-8", "replace")
        finally:
            failure.close()
    except urllib.error.URLError:
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    raw = parsed.get("conversation_id")
    if isinstance(raw, int) and raw > 0:
        return raw
    return None


def failed_probes(results: list[dict[str, Any]]) -> list[str]:
    failed: list[str] = []
    for result in results:
        probe_id = str(result.get("probe"))
        if result.get("error"):
            failed.append(probe_id)
        elif result.get("writes_conversation") and result.get("delete_http") != 200:
            failed.append(probe_id)
    return failed


def _reply_parts(reply: Any) -> tuple[int, str, list[tuple[str, str]], str]:
    status = int(getattr(reply, "status", None) or reply.code)
    final_url = str(reply.geturl())
    header_pairs = [(str(key), str(value)) for key, value in reply.headers.items()]
    body = reply.read().decode("utf-8", "replace")
    return status, final_url, header_pairs, body


def probe(
    item: dict[str, Any],
    site: str,
    timeout: float,
    *,
    allow_production: bool = False,
) -> dict[str, Any]:
    """One question-only POST. A known conversation is deleted afterwards.

    The requested host and the final host are both checked. A redirect to
    the public site is not followed unless `allow_production` is set.
    """
    if is_production(site) and not allow_production:
        return {
            "probe": item["id"],
            "locale": item["locale"],
            "question": item["messages"][-1]["content"],
            "requested_url": site.rstrip("/") + ROUTE,
            "final_url": site.rstrip("/") + ROUTE,
            "redirect_chain": [],
            "http": None,
            "selected_headers": {},
            "header_names": [],
            "conversation_id": None,
            "turn_id": None,
            "delete_http": None,
            "writes_conversation": False,
            "duration_s": None,
            "meta": None,
            "blocks": [],
            "answer_text": "",
            "answer_language": None,
            "error": "refusing: public site without --confirm-production",
        }
    jar = http.cookiejar.CookieJar()
    recorder = RedirectRecord(allow_production=allow_production)
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(jar), recorder
    )
    url = site.rstrip("/") + ROUTE
    body = json.dumps({"locale": item["locale"], "messages": item["messages"]}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    status: int | None = None
    final_url = url
    header_pairs: list[tuple[str, str]] = []
    raw_body = ""
    error: str | None = None
    conversation_id: int | None = None
    result: dict[str, Any] = {
        "probe": item["id"],
        "locale": item["locale"],
        "question": item["messages"][-1]["content"],
        "requested_url": url,
        "final_url": url,
        "redirect_chain": [],
        "http": None,
        "selected_headers": {},
        "header_names": [],
        "conversation_id": None,
        "turn_id": None,
        "delete_http": None,
        "writes_conversation": False,
        "duration_s": None,
        "meta": None,
        "blocks": [],
        "answer_text": "",
        "answer_language": None,
        "error": None,
    }
    started = time.monotonic()
    try:
        try:
            with opener.open(request, timeout=timeout) as reply:
                status, final_url, header_pairs, raw_body = _reply_parts(reply)
        except urllib.error.HTTPError as failure:
            try:
                status, final_url, header_pairs, raw_body = _reply_parts(failure)
            finally:
                failure.close()
            error = f"HTTP {status}"
        except urllib.error.URLError as failure:
            error = f"URLError: {failure.reason}"
        duration = time.monotonic() - started
        envelope = envelope_of(raw_body) if status == 200 else None
        if status == 200 and envelope is None:
            error = "HTTP 200 body is not a conversation envelope"
        elif status is not None and status != 200 and error is None:
            error = f"HTTP {status}"
        if recorder.blocked_production and not allow_production:
            error = (
                "refusing: a redirect would POST to the public site "
                f"({recorder.blocked_production}) without --confirm-production"
            )
        elif not allow_production and is_production(final_url):
            error = (
                "refusing: the final host is the public site "
                f"({final_url}) without --confirm-production"
            )
        inner = ""
        if envelope is not None:
            stream_value = envelope.get("stream", "")
            inner = stream_value if isinstance(stream_value, str) else ""
        if envelope is not None and isinstance(envelope.get("conversation_id"), int):
            conversation_id = int(envelope["conversation_id"])
        if conversation_id is None:
            conversation_id = cookie_conversation_id(jar)
        if conversation_id is None:
            conversation_id = read_conversation_id(opener, site, timeout)
        meta, blocks = client.parse_sse(inner) if inner else (None, [])
        turn_id = meta.get("turn_id") if meta else None
        answer = grade.visible_text(blocks)
        result.update(
            {
                "final_url": final_url,
                "redirect_chain": list(recorder.hops),
                "http": status,
                "selected_headers": selected_headers(header_pairs),
                "header_names": sorted({name for name, _value in header_pairs}),
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "writes_conversation": conversation_id is not None,
                "duration_s": round(duration, 1),
                "meta": meta,
                "blocks": blocks,
                "answer_text": answer,
                "answer_language": grade.language_of(answer) if answer else None,
                "error": error,
            }
        )
    except Exception as failure:  # noqa: BLE001 - one probe must not abort the run
        if recorder.blocked_production and not allow_production:
            error = (
                "refusing: a redirect would POST to the public site "
                f"({recorder.blocked_production}) without --confirm-production"
            )
        elif not allow_production and is_production(final_url):
            error = (
                "refusing: the final host is the public site "
                f"({final_url}) without --confirm-production"
            )
        result["error"] = error or f"{type(failure).__name__}: {failure}"
        if conversation_id is None:
            conversation_id = cookie_conversation_id(jar)
        if conversation_id is None:
            conversation_id = read_conversation_id(opener, site, timeout)
        result["conversation_id"] = conversation_id
        result["writes_conversation"] = conversation_id is not None
    finally:
        if isinstance(conversation_id, int) and result.get("delete_http") is None:
            result["delete_http"] = delete_conversation(opener, site, conversation_id)
            result["conversation_id"] = conversation_id
            result["writes_conversation"] = True
    return result


def run(
    site: str,
    probes: list[dict[str, Any]] | None = None,
    timeout: float = PROD_TIMEOUT,
    sink: Path | None = None,
    *,
    allow_production: bool = False,
) -> list[dict[str, Any]]:
    chosen = probes if probes is not None else PROBES
    results: list[dict[str, Any]] = []
    handle = None
    try:
        if sink is not None:
            sink.parent.mkdir(parents=True, exist_ok=True)
            handle = sink.open("w", encoding="utf-8")
        for item in chosen:
            result = probe(item, site, timeout, allow_production=allow_production)
            results.append(result)
            if handle is not None:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
        return results
    finally:
        if handle is not None:
            handle.close()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site", default=os.environ.get("SITE", "https://de-linker.com")
    )
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="required when --site is the public site: the POST writes a "
        "private conversation, which this client then deletes",
    )
    parser.add_argument(
        "--out",
        default=os.environ.get("SMOKE_OUT", "~/de-linker-data/campaign-335/smoke"),
    )
    arguments = parser.parse_args(argv)
    if is_production(arguments.site) and not arguments.confirm_production:
        print(
            "refusing: POST /genie/turn on the public site writes a private "
            "conversation. Pass --confirm-production to record the final URL "
            "and the response headers and delete the conversation afterwards. "
            "This client is not read-only.",
            file=sys.stderr,
        )
        return 2
    out_dir = Path(arguments.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    smoke_path = out_dir / "smoke.jsonl"
    results = run(
        arguments.site,
        sink=smoke_path,
        allow_production=arguments.confirm_production,
    )
    for result in results:
        meta = result.get("meta")
        route = meta.get("route") if isinstance(meta, dict) else None
        print(
            f"{result['probe']:<6} {result['http']} {result['duration_s']!s:>6}s "
            f"conversation={result['conversation_id']} turn={result['turn_id']} "
            f"deleted={result['delete_http']} route={route} "
            f"lang={result.get('answer_language')} error={result.get('error')}"
        )
        print(f"  final_url={result['final_url']}")
        print(f"  headers={json.dumps(result['selected_headers'], ensure_ascii=False)}")
    print(f"evidence: {smoke_path}")
    failed = failed_probes(results)
    if failed:
        print(f"probes failed: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
