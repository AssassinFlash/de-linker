"""Run the #332 system-failure battery against the local c332 instance.

Usage:
    uv run --locked python run_faults.py [evidence_dir] [--only M500-EN,VPS-DOWN]

Evidence stays under ~/de-linker-data. This script does not call de-linker.com.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

import stack
from client import (
    cookie_opener,
    describe,
    proxy_body,
    request_json,
    turn_body,
)
from faults import TINY_JPEG, FaultServer
from grade import grade, healthy
from redact import redact
from sse import parse_sse

PRODUCT_EN = "Do you stock the SAJ H2-10K-T2?"
PRODUCT_DE = "Haben Sie den SAJ H2-10K-T2 auf Lager?"
DOC_EN = "What is the maximum PV input power of the SAJ H2-10K-T2? Use the datasheet."
PROXY_TURN = stack.WP + "/wp-json/linker-ai/v1/genie/turn"
PROXY_THREAD = stack.WP + "/wp-json/linker-ai/v1/genie/conversation"
SERVICE_TURN = stack.GENIE + "/assistant/turn"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "evidence",
        nargs="?",
        default=str(Path.home() / "de-linker-data/campaign-332/evidence"),
    )
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)
    only = {item for item in args.only.split(",") if item}
    evidence = Path(args.evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    out = evidence / "cases.jsonl"
    if not only:
        out.write_text("")
    token = stack.service_token()
    rows: list[dict[str, Any]] = []

    def keep(row: dict[str, Any]) -> None:
        graded = grade(redact(row))
        rows.append(graded)
        with out.open("a") as handle:
            handle.write(json.dumps(graded, ensure_ascii=False) + "\n")
        print(f"{graded['id']}: {graded['verdict']}", flush=True)

    def wanted(case_id: str) -> bool:
        return not only or case_id in only

    try:
        if wanted("BASE-EN"):
            keep(control("BASE-EN", PRODUCT_EN, "en", token))
        if wanted("BASE-DOC"):
            keep(control("BASE-DOC", DOC_EN, "en", token, allow_measurements=True))
        if wanted("RATE-BURST"):
            keep(burst(token))
        if wanted("ATT-LIMIT"):
            keep(attachment_limit(token))
        if wanted("SSE-CUT"):
            keep(sse_case("SSE-CUT", "cut", token))
        if wanted("SSE-RESET"):
            keep(sse_case("SSE-RESET", "reset", token))
        if wanted("VPS-DOWN"):
            keep(vps_down(token))
        if wanted("VPS-KILL"):
            keep(vps_kill(token))
        if wanted("REDIS-FLAP"):
            keep(redis_flap(token))
        if wanted("REDIS-DOWN"):
            keep(redis_down(token))
        if wanted("AB-500"):
            keep(ability("AB-500", "500", token))
        if wanted("AB-TIMEOUT"):
            keep(ability_timeout(token))
        if any(
            wanted(item)
            for item in ("M500-EN", "M500-DE", "M500-DOC", "M-EMPTY", "M-429", "M-SLOW")
        ):
            chat(token, only, keep)
        if wanted("JEV-502"):
            keep(jev(token))
        if wanted("IDX-MISS") or wanted("IDX-BAD"):
            index_cases(token, only, keep)
    finally:
        print("restoring c332", flush=True)
        stack.restore()
    defects = [row["id"] for row in rows if row["verdict"] == "defect"]
    summary = {
        "pass": sum(1 for row in rows if row["verdict"] == "pass"),
        "defect": len(defects),
        "defects": defects,
    }
    (evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0


def control(
    case_id: str,
    question: str,
    locale: str,
    token: str,
    allow_measurements: bool = False,
) -> dict[str, Any]:
    before = stack.max_turn_id()
    row = ask_proxy(case_id, question, locale, token)
    row.update(
        {
            "id": case_id,
            "kind": "control",
            "fault": "none",
            "question": question,
            "allow_measurements": allow_measurements,
            "layer": "control",
            "precedent": "unfaulted path",
        }
    )
    row.update(_log(question, before))
    return row


def burst(token: str) -> dict[str, Any]:
    children = []
    for index in range(1, 7):
        question = f"{PRODUCT_EN} Burst {index}."
        before = stack.max_turn_id()
        child = ask_service(f"RATE-{index}", question, "en", token, timeout=180)
        child["id"] = f"RATE-{index}"
        child.update(_log(question, before))
        children.append(child)
    return {
        "id": "RATE-BURST",
        "kind": "burst",
        "fault": "six sequential turns, no injected limiter",
        "question": PRODUCT_EN,
        "children": children,
        "layer": "infrastructure",
        "precedent": "须自行设计 — dossier §1.15 has no rate-limit UX; the product rate limit is the hourly file allowance",
        "explicit_channel": "customer",
    }


def attachment_limit(token: str) -> dict[str, Any]:
    stack.seed_upload_limit(20)
    try:
        jpeg = TINY_JPEG.decode() if isinstance(TINY_JPEG, bytes) else TINY_JPEG
        refused = ask_proxy(
            "ATT-LIMIT",
            "Please read this nameplate.",
            "en",
            token,
            attachment={"name": "plate.jpg", "type": "image/jpeg", "data": jpeg},
            timeout=30,
        )
        typed = ask_proxy("ATT-AFTER", PRODUCT_EN, "en", token)
    finally:
        stack.clear_upload_limit()
    refused.update(
        {
            "id": "ATT-LIMIT",
            "kind": "fault",
            "fault": "upload counter seeded to the hourly ceiling (20), then one JPEG",
            "question": "Please read this nameplate.",
            "layer": "infrastructure",
            "precedent": "复刻 — hourly file allowance is this repo's own limit (Attachments::LIMIT 20); uxpatterns recovery is a visible refusal",
            "explicit_channel": "customer",
            "retry": {
                "ok": healthy(typed),
                "http": typed.get("http"),
                "answer_text": typed.get("answer_text"),
            },
        }
    )
    return refused


def sse_case(case_id: str, cut: str, token: str) -> dict[str, Any]:
    proxy = FaultServer("cut", upstream=stack.GENIE, cut=cut)
    url = proxy.start()
    before = stack.max_turn_id()
    try:
        stack.set_genie_url(url)
        jar, opener = cookie_opener()
        result = request_json(
            PROXY_TURN,
            proxy_body(PRODUCT_EN, "en", None),
            {},
            180,
            opener,
        )
        row = describe(result)
        stored = _read_thread(opener)
    finally:
        stack.set_genie_url(stack.GENIE)
        proxy.stop()
    logged = _log(PRODUCT_EN, before)
    retry = ask_proxy(case_id + "-RETRY", PRODUCT_EN, "en", token)
    row.update(logged)
    # Thread::answer renders assistant text only when the stored stream
    # contains done. A cut stream's block is not a shown answer.
    shown = bool(stored.get("assistant_text")) and stored.get("done") is True
    row.update(
        {
            "id": case_id,
            "kind": "fault",
            "fault": f"proxy {cut} of the service SSE",
            "question": PRODUCT_EN,
            "layer": "UI 状态",
            "precedent": "须自行设计 — dossier §1.15",
            "explicit_channel": "customer",
            "partial_shown": shown,
            "reload_hides_error": bool(stored.get("user_messages"))
            and stored.get("done") is not True
            and not shown,
            "stored": stored,
            "cookie_count": len(list(jar)),
            "retry": {
                "ok": healthy(retry),
                "http": retry.get("http"),
                "answer_text": retry.get("answer_text"),
            },
        }
    )
    return row


def vps_down(token: str) -> dict[str, Any]:
    stack.stop_genie()
    try:
        row = ask_proxy("VPS-DOWN", PRODUCT_EN, "en", token, timeout=20)
    finally:
        stack.start_genie()
    retry = ask_proxy("VPS-DOWN-RETRY", PRODUCT_EN, "en", token)
    row.update(
        {
            "id": "VPS-DOWN",
            "kind": "fault",
            "fault": "local genie process stopped before the turn",
            "question": PRODUCT_EN,
            "layer": "基础设施",
            "precedent": "须自行设计 — dossier §1.15 VPS down; uxpatterns error state is the pattern language",
            "explicit_channel": "customer",
            "retry": {
                "ok": healthy(retry),
                "http": retry.get("http"),
                "answer_text": retry.get("answer_text"),
            },
        }
    )
    return row


def vps_kill(token: str) -> dict[str, Any]:
    holder: dict[str, Any] = {}
    before = stack.max_turn_id()

    def call() -> None:
        holder["row"] = ask_proxy("VPS-KILL", PRODUCT_EN, "en", token, timeout=90)

    thread = threading.Thread(target=call)
    thread.start()
    time.sleep(3)
    stack.stop_genie()
    thread.join(timeout=100)
    stack.start_genie()
    row = holder.get("row") or {
        "http": None,
        "transport_error": "client thread missing",
        "answer_text": "",
    }
    logged = _log(PRODUCT_EN, before)
    retry = ask_proxy("VPS-KILL-RETRY", PRODUCT_EN, "en", token)
    row.update(
        {
            "id": "VPS-KILL",
            "kind": "fault",
            "fault": "genie killed 3s after the proxy request started",
            "question": PRODUCT_EN,
            "layer": "基础设施",
            "precedent": "须自行设计 — dossier §1.15 restart window",
            "explicit_channel": "customer",
            "retry": {
                "ok": healthy(retry),
                "http": retry.get("http"),
                "answer_text": retry.get("answer_text"),
            },
        }
    )
    row.update(logged)
    return row


def redis_flap(token: str) -> dict[str, Any]:
    holder: dict[str, Any] = {}
    before = stack.max_turn_id()

    def call() -> None:
        holder["row"] = ask_proxy("REDIS-FLAP", PRODUCT_EN, "en", token, timeout=90)

    thread = threading.Thread(target=call)
    thread.start()
    time.sleep(2)
    try:
        stack.redis_restart()
    finally:
        thread.join(timeout=100)
        stack.ensure_redis()
    row = holder.get("row") or {
        "http": None,
        "answer_text": "",
        "transport_error": "missing",
    }
    logged = _log(PRODUCT_EN, before)
    # A flap that still answers is a pass: graceful cache, real facts allowed.
    if healthy(row):
        row["kind"] = "control"
        row["allow_measurements"] = True
        retry: dict[str, Any] | None = None
    else:
        row["kind"] = "fault"
        again = ask_proxy("REDIS-FLAP-RETRY", PRODUCT_EN, "en", token)
        retry = {
            "ok": healthy(again),
            "http": again.get("http"),
            "answer_text": again.get("answer_text"),
        }
    row.update(logged)
    row.update(
        {
            "id": "REDIS-FLAP",
            "fault": "brew services restart redis about 2s into the turn",
            "question": PRODUCT_EN,
            "layer": "基础设施",
            "precedent": "复刻 — WP_REDIS_GRACEFUL (spec 5 / #103); failure must still be explicit if the turn dies",
            "explicit_channel": "customer",
            "retry": retry,
        }
    )
    return row


def redis_down(token: str) -> dict[str, Any]:
    before = stack.max_turn_id()
    stack.redis_stop()
    try:
        row = ask_proxy("REDIS-DOWN", PRODUCT_EN, "en", token, timeout=70)
    finally:
        stack.ensure_redis()
    logged = _log(PRODUCT_EN, before)
    if healthy(row):
        row["kind"] = "control"
        row["allow_measurements"] = True
        retry: dict[str, Any] | None = None
    else:
        row["kind"] = "fault"
        again = ask_proxy("REDIS-DOWN-RETRY", PRODUCT_EN, "en", token)
        retry = {
            "ok": healthy(again),
            "http": again.get("http"),
            "answer_text": again.get("answer_text"),
        }
    row.update(logged)
    row.update(
        {
            "id": "REDIS-DOWN",
            "fault": "redis stopped for the whole turn, then started again",
            "question": PRODUCT_EN,
            "layer": "基础设施",
            "precedent": "复刻 — WP_REDIS_GRACEFUL",
            "explicit_channel": "customer",
            "retry": retry,
        }
    )
    return row


def ability(case_id: str, mode: str, token: str) -> dict[str, Any]:
    before = stack.max_turn_id()
    stack.set_ability_mode(mode)
    try:
        row = ask_service(case_id, PRODUCT_EN, "en", token, timeout=180)
    finally:
        stack.clear_ability_mode()
    logged = _log(PRODUCT_EN, before)
    retry = ask_service(case_id + "-RETRY", PRODUCT_EN, "en", token, timeout=180)
    row.update(logged)
    row.update(
        {
            "id": case_id,
            "kind": "fault",
            "fault": f"search-products answers {mode}",
            "question": PRODUCT_EN,
            "layer": "工具",
            "precedent": "复刻 — ability 5xx retries then DEGRADED (#103); a success-shaped card without the outage is the §1.15 gap",
            "explicit_channel": "customer",
            "retry": {
                "ok": healthy(retry),
                "http": retry.get("http"),
                "answer_text": retry.get("answer_text"),
            },
        }
    )
    return row


def ability_timeout(token: str) -> dict[str, Any]:
    before = stack.max_turn_id()
    stack.set_ability_mode("timeout")
    try:
        row = ask_proxy("AB-TIMEOUT", PRODUCT_EN, "en", token, timeout=90)
        late = _wait_log(PRODUCT_EN, 45, before)
    finally:
        stack.clear_ability_mode()
    retry = ask_proxy("AB-TIMEOUT-RETRY", PRODUCT_EN, "en", token)
    row.update(late)
    row["retry"] = {
        "ok": healthy(retry),
        "http": retry.get("http"),
        "answer_text": retry.get("answer_text"),
    }
    row.update(
        {
            "id": "AB-TIMEOUT",
            "kind": "fault",
            "fault": "search-products sleeps 25s; client times out at 20s, three attempts",
            "question": PRODUCT_EN,
            "layer": "工具",
            "precedent": "须自行设计 — proxy budget is 60s (Proxy::TURN_BUDGET); the ability timeout stack can outlive it",
            "explicit_channel": "customer",
        }
    )
    return row


def chat(token: str, only: set[str], keep: Any) -> None:
    stub = FaultServer("chat", mode="500", slow_s=65)
    url = stub.start()
    try:
        stack.restart_genie({"GENIE_BASE_URL": url})
        plan = [
            ("M500-EN", "500", PRODUCT_EN, "en"),
            ("M500-DE", "500", PRODUCT_DE, "de"),
            ("M500-DOC", "500", DOC_EN, "en"),
            ("M-EMPTY", "empty", PRODUCT_EN, "en"),
            ("M-429", "429", PRODUCT_EN, "en"),
        ]
        for case_id, mode, question, locale in plan:
            if only and case_id not in only:
                continue
            stub.set_mode(mode)
            before = stack.max_turn_id()
            row = ask_service(case_id, question, locale, token, timeout=120)
            row.update(_log(question, before))
            row.update(
                {
                    "id": case_id,
                    "kind": "fault",
                    "fault": f"chat completions mode {mode}",
                    "question": question,
                    "layer": "基础设施",
                    "precedent": "部分复刻 — #103 DEGRADED when nothing is citable; dossier §1.15 says the customer-facing state for a model 5xx is still 须自行设计",
                    "explicit_channel": "customer",
                }
            )
            keep(row)
        if not only or "M-SLOW" in only:
            stub.set_mode("slow")
            before = stack.max_turn_id()
            row = ask_proxy("M-SLOW", PRODUCT_EN, "en", token, timeout=90)
            stack.stop_genie()
            row.update(_log(PRODUCT_EN, before))
            row.update(
                {
                    "id": "M-SLOW",
                    "kind": "fault",
                    "fault": "chat completions sleeps 65s, past Proxy::TURN_BUDGET 60s",
                    "question": PRODUCT_EN,
                    "layer": "UI 状态",
                    "precedent": "须自行设计 — dossier §1.15",
                    "explicit_channel": "customer",
                }
            )
            keep(row)
    finally:
        stub.stop()
        stack.restart_genie()
    if not only or "M500-EN" in only:
        before = stack.max_turn_id()
        retry = ask_service("M500-RETRY", PRODUCT_EN, "en", token, timeout=180)
        # Attach the retry onto a small control row so a failed recovery is visible.
        keep(
            {
                "id": "M500-RETRY",
                "kind": "control",
                "fault": "chat stub removed, same product question",
                "question": PRODUCT_EN,
                "layer": "control",
                "precedent": "retry after the fault is cleared",
                **retry,
                **_log(PRODUCT_EN, before),
            }
        )


def jev(token: str) -> dict[str, Any]:
    stub = FaultServer("openrouter")
    url = stub.start()
    try:
        before = stack.max_turn_id()
        stack.restart_genie(
            {
                "OPENROUTER_BASE_URL": url + "/api/v1",
                "OPENROUTER_API_KEY": "local-fault-not-a-real-key",
            }
        )
        row = ask_service("JEV-502", PRODUCT_EN, "en", token, timeout=180)
    finally:
        stub.stop()
        stack.restart_genie()
    row.update(_log(PRODUCT_EN, before))
    row.update(
        {
            "id": "JEV-502",
            "kind": "fault",
            "fault": "OpenRouter /systemone answers 502; key is a local dummy",
            "question": PRODUCT_EN,
            "layer": "Jev 路由",
            "precedent": "复刻 — spec 13: Jev failure is the one allowed degradation; jev_error in meta; chat model stays deepseek-flash",
            "explicit_channel": "meta",
            "allow_measurements": True,
        }
    )
    return row


def index_cases(token: str, only: set[str], keep: Any) -> None:
    missing = Path("/tmp/c332-no-such-index.sqlite")
    missing.unlink(missing_ok=True)
    bad = Path("/tmp/c332-bad-index.sqlite")
    bad.write_bytes(b"this is not a sqlite index" + b"\x00" * 64)
    ran = False
    if not only or "IDX-MISS" in only:
        ran = True
        before = stack.max_turn_id()
        stack.restart_genie({"GENIE_INDEX": str(missing)})
        row = ask_service("IDX-MISS", DOC_EN, "en", token, timeout=180)
        row.update(_log(DOC_EN, before))
        row.update(
            {
                "id": "IDX-MISS",
                "kind": "fault",
                "fault": "GENIE_INDEX points at a path that is not a file",
                "question": DOC_EN,
                "layer": "检索",
                "precedent": "复刻 — spec 13: a failed document search ends the turn in the fallback and does not fall back to keywords",
                "explicit_channel": "customer",
            }
        )
        keep(row)
    if not only or "IDX-BAD" in only:
        ran = True
        before = stack.max_turn_id()
        stack.restart_genie({"GENIE_INDEX": str(bad)})
        row = ask_service("IDX-BAD", DOC_EN, "en", token, timeout=180)
        row.update(_log(DOC_EN, before))
        row.update(
            {
                "id": "IDX-BAD",
                "kind": "fault",
                "fault": "GENIE_INDEX is a file of garbage bytes",
                "question": DOC_EN,
                "layer": "检索",
                "precedent": "复刻 — spec 13 document-search failure is an explicit fallback",
                "explicit_channel": "customer",
            }
        )
        keep(row)
    if ran:
        stack.restart_genie()
        before = stack.max_turn_id()
        retry = ask_service("IDX-RETRY", DOC_EN, "en", token, timeout=180)
        keep(
            {
                "id": "IDX-RETRY",
                "kind": "control",
                "fault": "real index restored",
                "question": DOC_EN,
                "allow_measurements": True,
                "layer": "control",
                "precedent": "retry after the fault is cleared",
                **retry,
                **_log(DOC_EN, before),
            }
        )


def ask_service(
    case_id: str, question: str, locale: str, token: str, timeout: float
) -> dict[str, Any]:
    print(f"ask-service {case_id}", flush=True)
    result = request_json(
        SERVICE_TURN,
        turn_body(case_id, question, locale),
        {"X-Linker-Service-Token": token},
        timeout,
    )
    return describe(result)


def ask_proxy(
    case_id: str,
    question: str,
    locale: str,
    token: str,
    attachment: dict[str, str] | None = None,
    timeout: float = 90,
) -> dict[str, Any]:
    print(f"ask-proxy {case_id}", flush=True)
    del token
    result = request_json(
        PROXY_TURN, proxy_body(question, locale, attachment), {}, timeout
    )
    return describe(result)


def _read_thread(opener: urllib.request.OpenerDirector) -> dict[str, Any]:
    request = urllib.request.Request(PROXY_THREAD, method="GET")
    try:
        with opener.open(request, timeout=20) as reply:
            raw = reply.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw[:300]}
    if not isinstance(parsed, dict):
        return {}
    raw_messages = parsed.get("messages")
    messages: list[Any] = raw_messages if isinstance(raw_messages, list) else []
    raw_stream = parsed.get("stream")
    stream = raw_stream if isinstance(raw_stream, str) else ""
    parsed_stream = parse_sse(stream)
    user_messages = [
        item.get("content")
        for item in messages
        if isinstance(item, dict) and item.get("role") == "user"
    ]
    return {
        "user_messages": user_messages,
        "done": parsed_stream["done"],
        "assistant_text": parsed_stream["answer_text"],
        "event_names": parsed_stream["event_names"],
    }


def _log(question: str, after_id: int = 0) -> dict[str, object]:
    found = stack.latest_turn(question, after_id)
    understanding = found.get("understanding")
    if isinstance(understanding, str) and len(understanding) > 2000:
        found = dict(found)
        found["understanding"] = understanding[:2000]
    return found


def _wait_log(question: str, seconds: float, after_id: int = 0) -> dict[str, object]:
    deadline = time.monotonic() + seconds
    found: dict[str, object] = {}
    while time.monotonic() < deadline:
        found = _log(question, after_id)
        if found:
            return found
        time.sleep(1)
    return found


if __name__ == "__main__":
    sys.exit(main())
