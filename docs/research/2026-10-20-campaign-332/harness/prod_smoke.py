"""Three normal production turns. No fault is injected. No mail is sent.

A production host is refused unless --confirm-production is passed, and
that mode also requires --evidence. Each probe records the final URL and
selected response headers, deletes the conversation it opened, then GETs
the thread and requires that the deleted id is not still the conversation.

    uv run --locked python prod_smoke.py --site https://de-linker.com --confirm-production \\
        --evidence "$HOME/de-linker-data/campaign-332/evidence/prod-smoke.jsonl"
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, cast

from client import cookie_opener, describe, request_json
from redact import redact

ROUTE = "/wp-json/linker-ai/v1/genie/turn"
DELETE_ROUTE = "/wp-json/linker-ai/v1/genie/conversations"
READ_ROUTE = "/wp-json/linker-ai/v1/genie/conversation"
COOKIE = "linker_conversation"
PRODUCTION_HOSTS = frozenset({"de-linker.com", "www.de-linker.com"})
# Campaign ceiling, not a product constant. This battery sends the three
# questions below; the guard refuses a longer tuple so a later edit cannot
# turn a confirmed production run into a load test.
SMOKE_CAP = 5
# Above Proxy::TURN_BUDGET (60s, plugins/linker-tools/includes/Genie/Proxy.php)
# so a slow healthy turn is recorded whole. The same budget covers the DELETE.
PROBE_TIMEOUT_S = 180.0
# GET /genie/conversation does no model call (Proxy::conversation). Thirty
# seconds is the harness read, not a turn budget.
READ_TIMEOUT_S = 30.0
PROBES = (
    {
        "id": "P1-EN",
        "locale": "en",
        "content": "Do you stock the SAJ H2-10K-T2?",
    },
    {
        "id": "P2-DE",
        "locale": "de",
        "content": "Haben Sie den SAJ H2-10K-T2 auf Lager?",
    },
    {
        "id": "P3-EN",
        "locale": "en",
        "content": "Which three-phase hybrid inverters do you list for a home?",
    },
)


def is_production(site: str) -> bool:
    host = (urllib.parse.urlparse(site).hostname or "").lower().rstrip(".")
    return host in PRODUCTION_HOSTS


def cookie_id(jar: http.cookiejar.CookieJar) -> int | None:
    for cookie in jar:
        if cookie.name != COOKIE:
            continue
        head = (cookie.value or "").split(".", 1)[0]
        if head.isdigit() and int(head) > 0:
            return int(head)
    return None


def delete_conversation(
    opener: urllib.request.OpenerDirector, site: str, conversation_id: int
) -> int | None:
    url = f"{site.rstrip('/')}{DELETE_ROUTE}/{conversation_id}"
    request = urllib.request.Request(url, method="DELETE")
    try:
        with opener.open(request, timeout=PROBE_TIMEOUT_S) as reply:
            reply.read()
            return int(reply.status)
    except urllib.error.HTTPError as failure:
        try:
            return int(failure.code)
        finally:
            failure.close()
    except urllib.error.URLError:
        return None


def read_id(opener: urllib.request.OpenerDirector, site: str) -> int | None:
    http, found = read_thread(opener, site)
    if http != 200:
        return None
    return found if isinstance(found, int) and found > 0 else None


def read_thread(
    opener: urllib.request.OpenerDirector, site: str
) -> tuple[int | None, int | None]:
    """GET the stored thread. `(None, None)` when the GET did not answer.

    Proxy::conversation returns 200 with conversation_id 0 once
    Conversations::delete has cleared the cookie. A body that still names
    the deleted id means the conversation is readable.
    """
    request = urllib.request.Request(site.rstrip("/") + READ_ROUTE, method="GET")
    try:
        with opener.open(request, timeout=READ_TIMEOUT_S) as reply:
            body = reply.read().decode("utf-8", "replace")
            http = int(reply.status)
    except urllib.error.HTTPError as failure:
        try:
            body = failure.read().decode("utf-8", "replace")
            http = int(failure.code)
        finally:
            failure.close()
    except urllib.error.URLError:
        return None, None
    return http, thread_id(body)


def thread_id(body: str) -> int | None:
    """The conversation_id in a thread GET, or None when the body has none."""
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    value = parsed.get("conversation_id") if isinstance(parsed, dict) else None
    if isinstance(value, int):
        return value
    return None


def deletion_holds(http: int | None, body_id: int | None, deleted: int) -> bool:
    """True when a GET no longer returns the conversation that was deleted.

    404 means the thread route refused the id. 200 with a different id
    (including 0, the empty guest thread) means the deleted post is gone.
    A 200 whose body has no parseable conversation_id does not count:
    the check could not see that the deleted id was gone.
    """
    if http == 404:
        return True
    if http != 200 or body_id is None:
        return False
    return body_id != deleted


def probe(item: dict[str, str], site: str) -> dict[str, Any]:
    jar, opener = cookie_opener()
    url = site.rstrip("/") + ROUTE
    result = request_json(
        url,
        {
            "locale": item["locale"],
            "messages": [{"role": "user", "content": item["content"]}],
            "page": {"type": "home"},
        },
        {},
        PROBE_TIMEOUT_S,
        opener,
    )
    described = describe(result)
    conversation_id = cookie_id(jar) or read_id(opener, site)
    delete_http = None
    read_http: int | None = None
    read_conversation_id: int | None = None
    holds = False
    if conversation_id is not None:
        delete_http = delete_conversation(opener, site, conversation_id)
        read_http, read_conversation_id = read_thread(opener, site)
        holds = deletion_holds(read_http, read_conversation_id, conversation_id)
    return cast(
        dict[str, Any],
        redact(
            {
                "probe": item["id"],
                "locale": item["locale"],
                "question": item["content"],
                "requested_url": url,
                "conversation_id": conversation_id,
                "delete_http": delete_http,
                "read_after_delete_http": read_http,
                "read_after_delete_id": read_conversation_id,
                "deletion_holds": holds,
                "header_names": list(described.get("selected_headers", {})),
                **described,
            }
        ),
    )


def failures_present(value: Any) -> bool:
    """True when SSE meta.failures is a non-empty list or a non-empty string."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def probe_failed(row: dict[str, Any]) -> bool:
    """A turn that is not a clean, deleted, non-fallback answer."""
    return (
        row.get("http") != 200
        or row.get("done") is not True
        or row.get("delete_http") != 200
        or row.get("fallback") is True
        or failures_present(row.get("failures"))
        or row.get("deletion_holds") is not True
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--confirm-production", action="store_true")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    if is_production(args.site) and not args.confirm_production:
        print("refusing production without --confirm-production", file=sys.stderr)
        return 2
    if args.confirm_production and not args.evidence:
        print("refusing a confirmed run without --evidence", file=sys.stderr)
        return 2
    if len(PROBES) > SMOKE_CAP:
        print("smoke is capped at 5 turns", file=sys.stderr)
        return 2
    rows = []
    for item in PROBES:
        rows.append(probe(item, args.site))
        print(rows[-1]["probe"], rows[-1].get("http"), flush=True)
    if args.evidence:
        path = Path(args.evidence)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        )
    failed = [row["probe"] for row in rows if probe_failed(row)]
    print(json.dumps({"turns": len(rows), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
