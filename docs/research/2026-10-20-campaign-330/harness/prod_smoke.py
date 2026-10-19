"""Production smoke for #330. This client writes, then deletes what it wrote.

POST /wp-json/linker-ai/v1/genie/turn goes through Proxy::turn, which opens a
private conversation and stores the turn. A production host is refused unless
`--confirm-production` is passed. Each probe records the conversation id, the
turn id, the observed final URL (`geturl()`, after redirects), the redirect
chain, and the selected response headers, then DELETEs that conversation.
Inquiry and contact routes are not called.

The 2026-10-19 run did none of this: it POSTed ten turns, synthesised the URL
as SITE+ROUTE, and left conversations 7444–7453 (turn rows 90–99) in place.
This file does not claim that run, or any later one, was read-only.
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

from run_battery import answer_text, parse_stream, shown_ids

ROUTE = "/wp-json/linker-ai/v1/genie/turn"
DELETE_ROUTE = "/wp-json/linker-ai/v1/genie/conversations"
# de-linker.com is the public site. Anything else, including a local instance
# of the same route, is not this gate.
PRODUCTION_HOSTS = frozenset({"de-linker.com", "www.de-linker.com"})
# Headers the smoke is willing to cite. A name absent from the response is
# omitted; it is not filled in from another probe.
SELECTED_HEADERS = (
    "Date",
    "Server",
    "X-Powered-By",
    "Content-Type",
    "X-Robots-Tag",
    "Link",
    "Location",
)
# Client socket timeout. The site proxy stops at 60 s
# (plugins/linker-tools includes/Genie/Proxy.php `post()`, `'timeout' => 60.0`,
# prices.SHELL_TIMEOUT). 180 is the original trial client's bound
# (services/genie/eval/baseline/run.py: the trial script used 180), so the
# client is still waiting when a slow proxy returns its own 60 s timeout.
# It does not extend that proxy timeout.
PROD_TIMEOUT = 180.0

# One representative per class plus one DE mirror; all also ran locally.
PROBES: list[dict[str, Any]] = [
    {
        "id": "S1-A-EN",
        "local": "A1-EN",
        "locale": "en",
        "messages": [
            {
                "role": "user",
                "content": "Do you have the SAJ H2-1OK-T3? Letter O, I never know.",
            }
        ],
    },
    {
        "id": "S2-B-EN",
        "local": "B1-EN",
        "locale": "en",
        "messages": [{"role": "user", "content": "\U0001f50b\u26a1?"}],
    },
    {
        "id": "S3-E-EN",
        "local": "E1-EN",
        "locale": "en",
        "messages": [{"role": "user", "content": "is the gw10k eta g20 single-phase?"}],
    },
    {
        "id": "S4-F-EN",
        "local": "F1-EN",
        "locale": "en",
        "messages": [{"role": "user", "content": "Is the SAJ GW10K-ETA-G20 in stock?"}],
    },
    {
        "id": "S5-G-EN",
        "local": "G1-EN",
        "locale": "en",
        "messages": [
            {"role": "user", "content": "Do you have the GW50K-ETA-G20 in stock?"}
        ],
    },
    {
        "id": "S6-H-EN",
        "local": "H3-EN",
        "locale": "en",
        "messages": [
            {
                "role": "user",
                "content": "Which of B2-5.0-HV1, B2-10.0-HV1 and B2-15.0-HV1 "
                "has the most usable kWh?",
            }
        ],
    },
    {
        "id": "S7-I-EN",
        "local": "I3-EN",
        "locale": "en",
        "messages": [
            {
                "role": "user",
                "content": "I have 8 kWp on the roof and use 4000 kWh a year, "
                "three-phase.",
            }
        ],
    },
    {
        "id": "S8-J-EN",
        "local": "J3-EN",
        "locale": "en",
        "messages": [
            {"role": "user", "content": "I want the GW10K-EHA-G20 but three-phase."}
        ],
    },
    {
        "id": "S9-E-DE",
        "local": "E1-DE",
        "locale": "de",
        "messages": [{"role": "user", "content": "ist der gw10k eta g20 dreiphasig?"}],
    },
    {
        "id": "S10-A-DE",
        "local": "A1-DE",
        "locale": "de",
        "messages": [
            {
                "role": "user",
                "content": "Haben Sie den SAJ H2-1OK-T3? Ich meine das Buchstaben-O.",
            }
        ],
    },
]


class RedirectRecord(urllib.request.HTTPRedirectHandler):
    """Remembers each hop. urllib follows the redirect; http.client does not,
    which is why the old smoke stored SITE+ROUTE and called it the final URL."""

    def __init__(self) -> None:
        super().__init__()
        self.hops: list[dict[str, object]] = []

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
        # urllib follows 301/302/303 and turns a POST into a GET. It refuses
        # 307/308 on POST (request.py redirect_request), which would hide the
        # URL the site actually answered. Those two keep the method and body.
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
    host = (urllib.parse.urlparse(site).hostname or "").lower()
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
    """DELETE the conversation this probe's cookie opened. Not an email."""
    url = f"{site.rstrip('/')}{DELETE_ROUTE}/{conversation_id}"
    request = urllib.request.Request(url, method="DELETE")
    try:
        with opener.open(request, timeout=30) as reply:
            reply.read()
            return int(reply.status)
    except urllib.error.HTTPError as failure:
        return int(failure.code)
    except urllib.error.URLError:
        return None


def probe(
    item: dict[str, Any],
    site: str,
    timeout: float,
) -> dict[str, Any]:
    """One POST. The conversation it creates is deleted before this returns."""
    jar = http.cookiejar.CookieJar()
    recorder = RedirectRecord()
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
    conversation_id: int | None = None
    result: dict[str, Any] = {}
    try:
        started = time.monotonic()
        with opener.open(request, timeout=timeout) as reply:
            # geturl() is the URL after redirects. The request URL is not.
            final_url = str(reply.geturl())
            header_pairs = [
                (str(key), str(value)) for key, value in reply.headers.items()
            ]
            status = int(reply.status)
            stream = reply.read().decode("utf-8", "replace")
        duration = time.monotonic() - started
        envelope: dict[str, Any] = {}
        try:
            parsed = json.loads(stream)
            if isinstance(parsed, dict):
                envelope = parsed
        except json.JSONDecodeError:
            envelope = {}
        raw_id = envelope.get("conversation_id")
        if isinstance(raw_id, int):
            conversation_id = raw_id
        inner = envelope.get("stream", "") if envelope else stream
        if not isinstance(inner, str):
            inner = stream
        meta, blocks = parse_stream(inner)
        turn_id = meta.get("turn_id") if meta else None
        result = {
            "probe": item["id"],
            "local_case": item["local"],
            "locale": item["locale"],
            "requested_url": url,
            "final_url": final_url,
            "redirect_chain": list(recorder.hops),
            "http": status,
            "selected_headers": selected_headers(header_pairs),
            "header_names": sorted({name for name, _value in header_pairs}),
            "conversation_id": conversation_id,
            "turn_id": turn_id,
            "delete_http": None,
            "writes_conversation": conversation_id is not None,
            "duration_s": round(duration, 1),
            "meta": meta,
            "blocks": blocks,
            "answer_text": answer_text(blocks),
            "product_ids": shown_ids(blocks),
            "stream": inner if len(inner) < 20000 else inner[:20000] + "…",
        }
        return result
    finally:
        if conversation_id is not None and result.get("delete_http") is None:
            result["delete_http"] = delete_conversation(opener, site, conversation_id)


def run(
    site: str,
    probes: list[dict[str, Any]] | None = None,
    timeout: float = PROD_TIMEOUT,
) -> list[dict[str, Any]]:
    return [
        probe(item, site, timeout)
        for item in (probes if probes is not None else PROBES)
    ]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site",
        default=os.environ.get("SITE", "https://de-linker.com"),
    )
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="required when --site is the public site: the POST writes a "
        "private conversation, which this client then deletes",
    )
    parser.add_argument(
        "--out",
        default=os.environ.get("SMOKE_OUT", "~/de-linker-data/campaign-330/smoke"),
    )
    arguments = parser.parse_args(argv)
    if is_production(arguments.site) and not arguments.confirm_production:
        print(
            "refusing: POST /genie/turn on the public site writes a private "
            "conversation. Pass --confirm-production to record the conversation "
            "id and turn id and delete the conversation afterwards. "
            "This client is not read-only.",
            file=sys.stderr,
        )
        return 2
    out_dir = Path(arguments.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = run(arguments.site)
    with (out_dir / "smoke.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    for result in results:
        route = result["meta"].get("route") if result["meta"] else None
        print(
            f"{result['probe']:<10} {result['http']} {result['duration_s']:>6}s "
            f"conversation={result['conversation_id']} turn={result['turn_id']} "
            f"deleted={result['delete_http']} route={route}"
        )
    print(f"evidence: {out_dir / 'smoke.jsonl'}")
    undeleted = [
        result["conversation_id"]
        for result in results
        if result.get("writes_conversation") and result.get("delete_http") != 200
    ]
    if undeleted:
        print(f"conversations not deleted: {undeleted}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
