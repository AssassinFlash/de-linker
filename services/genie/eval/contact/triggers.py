"""When Genie offers "Let Linker contact me", against the running service (#243).

    uv run python eval/contact/triggers.py http://127.0.0.1:9113 out.json

Posts each case of cases.json to POST /assistant/turn of a running Genie (`just serve
<instance>`: the phrase table, Jev on OpenRouter, deepseek-flash on the official API)
and reads the contact block of the answer. A thread posts its messages one turn after
another in one conversation, the answers in between, as the dock does; the service
reads the earlier offers from its own turn log. Prints one line per turn and exits 1
when any turn's offer differs from the expected one.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

DATA = json.loads((Path(__file__).resolve().parent / "cases.json").read_text())
PAGE = {"type": "home", "url": "http://127.0.0.1/", "title": "Linker"}
# One turn makes at most four ability calls of twenty seconds each and the model's
# own time: the proxy's sixty seconds (plugins/linker-tools Proxy::post), doubled.
TIMEOUT = 120.0


def turn(
    base: str, conversation: str, locale: str, messages: list[dict[str, str]]
) -> dict[str, Any]:
    started = time.monotonic()
    response = httpx.post(
        base.rstrip("/") + "/assistant/turn",
        json={
            "conversation_id": conversation,
            "messages": messages,
            "locale": locale,
            "page_context": PAGE,
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    meta: dict[str, Any] = {}
    blocks: list[dict[str, Any]] = []
    for event in response.text.split("\n\n"):
        name, _, rest = event.partition("\n")
        if not rest.startswith("data: "):
            continue
        payload = json.loads(rest[len("data: ") :])
        if name == "event: meta":
            meta = payload
        elif name == "event: block":
            blocks.append(payload)
    contact = next((b for b in blocks if b.get("type") == "contact"), None)
    return {
        "offer": contact["reason"] if contact else None,
        "route": meta.get("route"),
        "intent": meta.get("intent"),
        "jev_error": meta.get("jev_error"),
        "text": " ".join(b.get("text", "") for b in blocks if b.get("type") == "text"),
        "handoff": " ".join(
            b.get("summary", "") for b in blocks if b.get("type") == "handoff"
        ),
        "seconds": round(time.monotonic() - started, 1),
    }


def main() -> None:
    base, out = sys.argv[1], Path(sys.argv[2])
    rows: list[dict[str, Any]] = []
    for case in DATA["cases"]:
        got = turn(
            base,
            f"eval-243-{uuid.uuid4().hex[:8]}",
            case["locale"],
            [{"role": "user", "content": case["message"]}],
        )
        rows.append({**case, "got": got, "ok": got["offer"] == case["offer"]})
    for thread in DATA["threads"]:
        conversation = f"eval-243-{uuid.uuid4().hex[:8]}"
        messages: list[dict[str, str]] = []
        for index, (message, expected) in enumerate(
            zip(thread["messages"], thread["offers"], strict=True)
        ):
            messages.append({"role": "user", "content": message})
            got = turn(base, conversation, thread["locale"], messages)
            messages.append(
                {"role": "assistant", "content": got["text"] or got["handoff"]}
            )
            rows.append(
                {
                    "id": f"{thread['id']}#{index + 1}",
                    "locale": thread["locale"],
                    "message": message,
                    "offer": expected,
                    "got": got,
                    "ok": got["offer"] == expected,
                }
            )
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    for row in rows:
        mark = "ok  " if row["ok"] else "FAIL"
        print(
            f"{mark} {row['id']:<14} expected={row['offer']!s:<13} got={row['got']['offer']!s:<13} route={row['got']['route']} intent={row['got']['intent']} {row['got']['seconds']}s"
        )
    right = sum(row["ok"] for row in rows)
    print(f"{right}/{len(rows)} turns as expected")
    raise SystemExit(0 if right == len(rows) else 1)


if __name__ == "__main__":
    main()
