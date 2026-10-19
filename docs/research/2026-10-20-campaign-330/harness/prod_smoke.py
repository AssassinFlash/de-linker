"""The production smoke of #330: <=10 probes through the site's own proxy.

Public Genie conversations send no email; nothing here touches the inquiry or
contact routes. Each probe records the final URL, the response headers
(frame-provenance discipline), the SSE stream and the duration, next to the
same case's local answer for the matched/mismatched call.
"""

from __future__ import annotations

import http.client
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

from run_battery import parse_stream, shown_ids, answer_text

SITE = os.environ.get("SITE", "https://de-linker.com")
ROUTE = "/wp-json/linker-ai/v1/genie/turn"

# One representative per class plus one DE mirror; all also ran locally.
PROBES: list[dict] = [
    {"id": "S1-A-EN", "local": "A1-EN", "locale": "en",
     "messages": [{"role": "user",
                   "content": "Do you have the SAJ H2-1OK-T3? Letter O, I never know."}]},
    {"id": "S2-B-EN", "local": "B1-EN", "locale": "en",
     "messages": [{"role": "user", "content": "\U0001F50B⚡?"}]},
    {"id": "S3-E-EN", "local": "E1-EN", "locale": "en",
     "messages": [{"role": "user", "content": "is the gw10k eta g20 single-phase?"}]},
    {"id": "S4-F-EN", "local": "F1-EN", "locale": "en",
     "messages": [{"role": "user", "content": "Is the SAJ GW10K-ETA-G20 in stock?"}]},
    {"id": "S5-G-EN", "local": "G1-EN", "locale": "en",
     "messages": [{"role": "user", "content": "Do you have the GW50K-ETA-G20 in stock?"}]},
    {"id": "S6-H-EN", "local": "H3-EN", "locale": "en",
     "messages": [{"role": "user",
                   "content": "Which of B2-5.0-HV1, B2-10.0-HV1 and B2-15.0-HV1 "
                               "has the most usable kWh?"}]},
    {"id": "S7-I-EN", "local": "I3-EN", "locale": "en",
     "messages": [{"role": "user",
                   "content": "I have 8 kWp on the roof and use 4000 kWh a year, "
                               "three-phase."}]},
    {"id": "S8-J-EN", "local": "J3-EN", "locale": "en",
     "messages": [{"role": "user",
                   "content": "I want the GW10K-EHA-G20 but three-phase."}]},
    {"id": "S9-E-DE", "local": "E1-DE", "locale": "de",
     "messages": [{"role": "user",
                   "content": "ist der gw10k eta g20 dreiphasig?"}]},
    {"id": "S10-A-DE", "local": "A1-DE", "locale": "de",
     "messages": [{"role": "user",
                   "content": "Haben Sie den SAJ H2-1OK-T3? Ich meine das Buchstaben-O."}]},
]


def probe(item: dict) -> dict:
    parsed = urllib.parse.urlparse(SITE)
    connection = (
        http.client.HTTPSConnection(parsed.netloc, timeout=180)
        if parsed.scheme == "https"
        else http.client.HTTPConnection(parsed.netloc, timeout=180)
    )
    body = json.dumps({"locale": item["locale"], "messages": item["messages"]})
    started = time.monotonic()
    try:
        connection.request(
            "POST", ROUTE, body=body,
            headers={"Content-Type": "application/json",
                     "Accept": "text/event-stream"},
        )
        reply = connection.getresponse()
        headers = dict(reply.getheaders())
        stream = reply.read().decode("utf-8", "replace")
        status = reply.status
    finally:
        connection.close()
    duration = time.monotonic() - started
    # The proxy wraps the service's SSE in a JSON envelope (Proxy::turn):
    # {"conversation_id": ..., "stream": "event: meta\ndata: ..."}.
    envelope = {}
    try:
        envelope = json.loads(stream)
    except json.JSONDecodeError:
        pass
    inner = envelope.get("stream", "") if envelope else stream
    meta, blocks = parse_stream(inner)
    return {
        "probe": item["id"], "local_case": item["local"], "locale": item["locale"],
        "final_url": SITE + ROUTE, "http": status, "headers": headers,
        "duration_s": round(duration, 1), "meta": meta, "blocks": blocks,
        "answer_text": answer_text(blocks), "product_ids": shown_ids(blocks),
        "stream": inner if len(inner) < 20000 else inner[:20000] + "…",
    }


def main() -> int:
    out_dir = Path(
        os.environ.get("SMOKE_OUT", "~/de-linker-data/campaign-330/smoke")
    ).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [probe(item) for item in PROBES]
    with (out_dir / "smoke.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    for result in results:
        print(f"{result['probe']:<10} {result['http']} {result['duration_s']:>6}s "
              f"ids={result['product_ids']} route={result['meta'].get('route') if result['meta'] else None}")
    print(f"evidence: {out_dir / 'smoke.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
