"""Three normal production turns. No fault is injected. No mail is sent.

A production host is refused unless --confirm-production is passed. Each
probe records the final URL and selected response headers, then deletes
the conversation it opened.

    uv run --locked python prod_smoke.py --site https://de-linker.com --confirm-production
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

from client import describe, request_json
from redact import redact

ROUTE = "/wp-json/linker-ai/v1/genie/turn"
DELETE_ROUTE = "/wp-json/linker-ai/v1/genie/conversations"
READ_ROUTE = "/wp-json/linker-ai/v1/genie/conversation"
COOKIE = "linker_conversation"
PRODUCTION_HOSTS = frozenset({"de-linker.com", "www.de-linker.com"})
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
        with opener.open(request, timeout=180) as reply:
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
    request = urllib.request.Request(site.rstrip("/") + READ_ROUTE, method="GET")
    try:
        with opener.open(request, timeout=30) as reply:
            body = reply.read().decode("utf-8", "replace")
    except urllib.error.URLError:
        return None
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("conversation_id"), int):
        value = parsed["conversation_id"]
        return value if value > 0 else None
    return None


def probe(item: dict[str, str], site: str) -> dict[str, Any]:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    url = site.rstrip("/") + ROUTE
    result = request_json(
        url,
        {
            "locale": item["locale"],
            "messages": [{"role": "user", "content": item["content"]}],
            "page": {"type": "home"},
        },
        {},
        180,
        opener,
    )
    described = describe(result)
    conversation_id = cookie_id(jar) or read_id(opener, site)
    delete_http = None
    if conversation_id is not None:
        delete_http = delete_conversation(opener, site, conversation_id)
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
                "header_names": list(described.get("selected_headers", {})),
                **described,
            }
        ),
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
    if len(PROBES) > 5:
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
    failed = [
        row["probe"]
        for row in rows
        if row.get("http") != 200
        or row.get("done") is not True
        or row.get("delete_http") != 200
    ]
    print(json.dumps({"turns": len(rows), "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
