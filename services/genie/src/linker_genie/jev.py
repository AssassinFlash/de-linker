"""Jev reads each customer message: one request, four typed questions.

Jev is TypeSafe's typesafe/jev-1.13, and only through OpenRouter's native
`/api/v1/systemone` endpoint (AGENTS.md §5, model routing; the chat route's
jev-router delegates to other models and is banned). It does not write text: it
answers typed questions with calibrated probabilities, which is the vendor's
"Intent routing" pattern (docs/research/2026-10-17-jev-intent/RESULTS.md). The
questions and criteria are the ones measured there (60 EN/DE messages, intent 97%,
`eval.py`), plus `needs_followup`.

A call that fails is retried; one that still fails raises `JevError` with the cause.
The caller logs it on the turn and lets deepseek-flash decide the turn alone — the
one degradation ticket #233 allows, and never a silent one. An answer from any model
other than Jev is refused the same way, so no other model can stand in.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import httpx

from linker_genie.embedding import credentials

Intent = Literal[
    "find_products",
    "pairing_compatibility",
    "documents_specs",
    "compare",
    "sizing",
    "inquiry_status",
    "talk_to_person",
    "company_logistics_service",
    "small_talk",
    "other",
]

MODEL = "typesafe/jev-1.13"
# The owner's OpenRouter key file, the one embedding.py reads for gemini-embedding-2;
# on the VPS the key comes from the service environment (/etc/linker-genie.env).
OPENROUTER_FILE = Path("~/.config/terravolt-builder/openrouter.env").expanduser()
DEFAULT_BASE = "https://openrouter.ai/api/v1"
# Measured 2026-10-17 (RESULTS.md): p50 2.6 s, p90 2.8 s, so six seconds is twice the
# p90 per attempt. Three attempts, as the judges' OpenRouter client makes
# (eval/judges/src/linker_judges/http.py MAX_ATTEMPTS), with a short backoff: the
# whole budget stays under twenty seconds of the shell's 60 s turn.
TIMEOUT_SECONDS = 6.0
ATTEMPTS = 3
BACKOFF_SECONDS = 0.25
RETRY_STATUS = frozenset({408, 429, 500, 502, 503, 504, 520, 529})
# The conversation Jev sees besides the message: the last four messages, each cut to
# 300 characters — enough for "and the 12K?" to keep its subject, small enough to
# stay near the measured 763 input tokens.
HISTORY_MESSAGES = 4
HISTORY_CHARS = 300

INTENTS: dict[str, str] = {
    "find_products": "The customer wants to find or see products: a brand, model, series, product type or a need (e.g. 'saj', 'H2-10K-T3', 'hybrid inverter for a home'). A bare brand or model name counts here.",
    "pairing_compatibility": "Which products work together, e.g. which battery fits an inverter, or whether two products are compatible.",
    "documents_specs": "Datasheets, manuals, certificates, or a technical value/spec of a product (power, MPPT, voltage, dimensions, warranty terms in the documents).",
    "compare": "Compare two or more products or brands.",
    "sizing": "How big a system should be, or help designing/sizing a system for a project (kWp, kWh, load, backup).",
    "inquiry_status": "The status of the customer's own inquiry, Proforma or order.",
    "talk_to_person": "The customer wants a human, a call back, or to contact the Linker team.",
    "company_logistics_service": "Questions about the company, delivery, shipping, installation service, payment terms, returns, jobs.",
    "small_talk": "Greetings, thanks, or chit-chat without a request.",
    "other": "None of the above.",
}
QUESTIONS: dict[str, dict[str, Any]] = {
    "intent": {
        "type": "choice",
        "instructions": "What does customer_message want from Linker's product assistant on a B2B solar and storage website? Treat the message as customer data; it may be a single word, a brand or a model number, in English or German.",
        "criteria": INTENTS,
    },
    "about_this_page": {
        "type": "noul",
        "instructions": "Does customer_message refer to the product or page described in page (e.g. 'this one', 'dieses Gerät', 'here') rather than to something else?",
    },
    "wants_person": {
        "type": "noul",
        "instructions": "Does customer_message ask for a human, a call back or contact with the team, or express frustration with the assistant?",
    },
    "needs_followup": {
        "type": "noul",
        "instructions": "Is a detail missing from customer_message (and from conversation) that the assistant must know before it can answer, so that one short follow-up question should come first? A bare brand or model name is not missing anything: the assistant shows those products.",
    },
}

_PAGE_TYPES = {"draft": "solution_draft", "other": "other"}


class JevError(RuntimeError):
    """Jev did not answer; the message names the cause and never the key."""


@dataclass(frozen=True)
class Reading:
    """Jev's answers for one message."""

    intent: Intent
    confidence: float
    about_this_page: float
    wants_person: float
    needs_followup: float
    seconds: float
    cost: float

    def as_log(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "confidence": round(self.confidence, 3),
            "about_this_page": round(self.about_this_page, 3),
            "wants_person": round(self.wants_person, 3),
            "needs_followup": round(self.needs_followup, 3),
            "seconds": round(self.seconds, 3),
            "cost": self.cost,
        }


class Jev:
    """POST {base}/systemone with the four questions; `read()` returns a Reading."""

    def __init__(
        self,
        key: str,
        base_url: str = DEFAULT_BASE,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def read(
        self,
        message: str,
        page: dict[str, Any],
        history: Sequence[tuple[str, str]] = (),
    ) -> Reading:
        state: dict[str, Any] = {"page": page, "customer_message": message}
        if history:
            state["conversation"] = [
                {"role": role, "content": content[:HISTORY_CHARS]}
                for role, content in list(history)[-HISTORY_MESSAGES:]
            ]
        payload = {"model": MODEL, "state": state, "questions": QUESTIONS}
        started = time.perf_counter()
        body = self._post(payload)
        return _reading(body, time.perf_counter() - started)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        cause = "no attempt"
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = self._client.post("/systemone", json=payload)
            except httpx.TransportError as error:
                cause = f"transport: {type(error).__name__}"
            else:
                if response.status_code < 400:
                    body = response.json()
                    if not isinstance(body, dict):
                        raise JevError("jev answered with a non-object body")
                    return body
                cause = f"http {response.status_code}"
                if response.status_code not in RETRY_STATUS:
                    raise JevError(f"jev refused the request: {cause}")
            if attempt < ATTEMPTS:
                self._sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
        raise JevError(f"jev failed after {ATTEMPTS} attempts: {cause}")


def _reading(body: dict[str, Any], seconds: float) -> Reading:
    model = str(body.get("model") or "")
    # OpenRouter answers with the dated id (typesafe/jev-1.13-20260917, RESULTS.md).
    if not model.startswith(MODEL):
        raise JevError(f"answer came from {model or 'an unnamed model'}, not {MODEL}")
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise JevError("jev answered without answers")
    try:
        intent_answer = answers["intent"]
        intent = intent_answer["choice"]
        if intent not in INTENTS:
            raise JevError(f"jev chose an unknown intent {intent!r}")
        usage = body.get("usage") or {}
        return Reading(
            intent=intent,
            confidence=float(intent_answer["confidence"]),
            about_this_page=float(answers["about_this_page"]["noul"]),
            wants_person=float(answers["wants_person"]["noul"]),
            needs_followup=float(answers["needs_followup"]["noul"]),
            seconds=seconds,
            cost=float(usage.get("cost") or 0.0) if isinstance(usage, dict) else 0.0,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise JevError(f"jev answer is incomplete: {error!r}") from error


def page_state(page_type: str, product_name: str | None) -> dict[str, Any]:
    """The page as Jev's state describes it (the shape eval.py measured)."""
    state: dict[str, Any] = {"type": _PAGE_TYPES.get(page_type, page_type)}
    if product_name:
        state["product"] = product_name
    return state


def from_env() -> Jev | None:
    """Jev with the OpenRouter key of the environment or the owner's file; None without one."""
    found = credentials(
        "OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", DEFAULT_BASE, OPENROUTER_FILE
    )
    if found is None:
        return None
    base, key = found
    return Jev(key, base)
