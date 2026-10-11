"""The judges: System One decision models and chat LLMs, behind one call.

A System One judge (an open decision model served by llama.cpp's /v1/systemone) returns
typed answers with probabilities. A chat judge (TypeSafe's Jev through OpenRouter, an
LLM through aihubmix, or an open LLM served by llama.cpp) gets the same questions in
a prompt and replies in JSON with calibrated probabilities. Either way one call
evaluates one item.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .http import (
    HttpError,
    aihubmix_credentials,
    deepseek_credentials,
    openrouter_credentials,
    post_json,
)
from .rubric import Question, chat_messages

Kind = Literal["system_one", "chat"]
AIHUBMIX = "aihubmix"
OPENROUTER = "openrouter"
DEEPSEEK = "deepseek"
REMOTES = (AIHUBMIX, OPENROUTER, DEEPSEEK)


def chat_url(base: str) -> str:
    """The chat-completions URL under an OpenAI-compatible base. OpenRouter's
    base already ends in /v1 (https://openrouter.ai/api/v1); aihubmix's and a
    llama.cpp server's do not."""
    base = base.rstrip("/")
    return base + (
        "/chat/completions" if base.endswith("/v1") else "/v1/chat/completions"
    )


@dataclass(frozen=True)
class Judge:
    name: str
    kind: Kind
    model: str
    endpoint: str
    """`OPENROUTER` (the Jev first pass since 2026-10-11), `AIHUBMIX`,
    `DEEPSEEK` (owner ruling 2026-10-11: the escalation judge goes
    direct to the official API), or the base URL of a local llama.cpp server."""
    price_in: float = 0.0
    """USD per million input tokens — the fallback rate when the endpoint does not
    report a call's own cost (OpenRouter does; the jev-router's backend varies per
    call, so its reported number is the honest one)."""
    price_out: float = 0.0
    temperature: float | None = None
    json_mode: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    weights: str = "closed"
    """"closed", or the open checkpoint and its quantization."""

    @property
    def local(self) -> bool:
        return self.endpoint not in REMOTES


@dataclass(frozen=True)
class Answer:
    label: str | None
    """One of the question's labels, or None when the judge's output was invalid."""
    confidence: float | None = None
    probabilities: dict[str, float] | None = None


@dataclass(frozen=True)
class Verdict:
    answers: dict[str, Answer]
    seconds: float
    attempts: int
    started_at: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    model_reported: str
    reason: str | None = None
    error: str | None = None


def call(
    judge: Judge, state: dict[str, Any], questions: tuple[Question, ...]
) -> Verdict:
    """One evaluation of one item; failures come back as a verdict with `error` set
    (and the wall-clock start time of the attempt, so outage windows stay provable)."""
    started = time.time()
    if judge.local:
        base, key = judge.endpoint.rstrip("/"), None
    elif judge.endpoint == DEEPSEEK:
        base, key = deepseek_credentials()
    elif judge.endpoint == OPENROUTER:
        base, key = openrouter_credentials()
    else:
        base, key = aihubmix_credentials()
    try:
        if judge.kind == "system_one":
            body: dict[str, Any] = {
                "model": judge.model,
                "state": state,
                "questions": {q.name: q.system_one() for q in questions},
            }
            response = post_json(base + "/v1/systemone", body, key)
            answers = parse_system_one(response.body.get("answers", {}), questions)
            usage = response.body.get("usage", {})
            tokens_in, tokens_out = (
                int(usage.get("input_tokens", 0)),
                int(usage.get("output_tokens", 0)),
            )
            reason = None
        else:
            body = {"model": judge.model, "messages": chat_messages(state, questions)}
            if judge.temperature is not None:
                body["temperature"] = judge.temperature
            if judge.json_mode:
                body["response_format"] = {"type": "json_object"}
            body.update(judge.extra)
            response = post_json(chat_url(base), body, key)
            content = response.body["choices"][0]["message"].get("content") or ""
            answers, reason = parse_chat(content, questions)
            usage = response.body.get("usage", {})
            tokens_in, tokens_out = (
                int(usage.get("prompt_tokens", 0)),
                int(usage.get("completion_tokens", 0)),
            )
    except (HttpError, KeyError, IndexError, ValueError) as error:
        empty = {q.name: Answer(None) for q in questions}
        return Verdict(empty, 0.0, 0, started, 0, 0, 0.0, "", error=str(error)[:500])
    reported = usage.get("cost")
    cost = (
        float(reported)
        if isinstance(reported, (int, float))
        else (tokens_in * judge.price_in + tokens_out * judge.price_out) / 1_000_000
    )
    return Verdict(
        answers,
        response.seconds,
        response.attempts,
        response.started_at,
        tokens_in,
        tokens_out,
        cost,
        str(response.body.get("model", "")),
        reason,
    )


def parse_system_one(
    raw: dict[str, Any], questions: tuple[Question, ...]
) -> dict[str, Answer]:
    """Typed answers -> labels. A score's label is its most probable level (the level
    TypeSafe's `confidence` is measured around); a noul is "yes" from 0.5 up, with the
    confidence TypeSafe recommends for it, |2p - 1| (docs.typesafe.ai/confidence)."""
    answers = {}
    for question in questions:
        item = raw.get(question.name)
        if not isinstance(item, dict):
            answers[question.name] = Answer(None)
            continue
        if question.type == "noul":
            if not isinstance(item.get("noul"), (int, float)):
                answers[question.name] = Answer(None)
                continue
            p = float(item["noul"])
            answers[question.name] = Answer(
                "yes" if p >= 0.5 else "no", abs(2 * p - 1), {"yes": p, "no": 1 - p}
            )
            continue
        probabilities = {
            str(k): float(v) for k, v in item.get("probabilities", {}).items()
        }
        if question.type == "score":
            label = (
                max(probabilities, key=lambda level: probabilities[level])
                if probabilities
                else None
            )
        else:
            label = str(item.get("choice"))
        confidence = item.get("confidence")
        valid = label in question.labels()
        answers[question.name] = Answer(
            label if valid else None,
            float(confidence) if confidence is not None else None,
            probabilities or None,
        )
    return answers


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_chat(
    content: str, questions: tuple[Question, ...]
) -> tuple[dict[str, Answer], str | None]:
    """The JSON object in an LLM's reply -> labels; anything off-schema is invalid (None).

    A reply may answer a question with a bare value ("2", "yes") or with calibrated
    probabilities; the object form is read with parse_system_one's formulas (one
    parser, one set of formulas), so a chat judge's confidence means the same thing
    as a decision model's in the cascade. Nothing is repaired or re-asked: an
    invalid answer counts as a disagreement.
    """
    match = _JSON_OBJECT.search(content)
    data: Any = None
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        return {q.name: Answer(None) for q in questions}, None
    answers = {}
    for question in questions:
        value = data.get(question.name)
        if isinstance(value, dict):
            answers[question.name] = _object_answer(value, question)
            continue
        label: str | None
        if question.type == "noul":
            text = str(value).strip().lower()
            label = {"yes": "yes", "true": "yes", "no": "no", "false": "no"}.get(text)
        elif question.type == "score":
            text = str(value).strip()
            label = text if text in question.labels() else None
        else:
            text = str(value).strip()
            lookup = {key.lower(): key for key in question.labels()}
            label = lookup.get(text.lower())
        answers[question.name] = Answer(label)
    reason = data.get("reason")
    return answers, str(reason) if reason is not None else None


def _object_answer(item: dict[str, Any], question: Question) -> Answer:
    """One question's object in a chat reply, with parse_system_one's formulas.

    The probabilities are either under a "probabilities" key or the object's own
    label-valued entries ("yes": 0.99). The label is their maximum; the confidence
    is the reply's own when it carries one, else what the probabilities imply
    (noul: |2p - 1| around yes, as docs.typesafe.ai/confidence prescribes; score
    and choice: the top probability).
    """
    raw = item.get("probabilities")
    if not isinstance(raw, dict):
        raw = {
            key: value
            for key, value in item.items()
            if isinstance(value, (int, float)) and str(key) in question.labels()
        }
    probabilities = {str(key): float(value) for key, value in raw.items()}
    confidence = (
        float(item["confidence"])
        if isinstance(item.get("confidence"), (int, float))
        else None
    )
    if question.type == "noul":
        p = probabilities.get("yes")
        if p is None and isinstance(item.get("noul"), (int, float)):
            p = float(item["noul"])
        if p is None:
            return Answer(None, confidence)
        return Answer(
            "yes" if p >= 0.5 else "no",
            confidence if confidence is not None else abs(2 * p - 1),
            {"yes": p, "no": 1 - p},
        )
    label: str | None = None
    if probabilities:
        label = max(probabilities, key=lambda level: probabilities[level])
    elif question.type == "choice" and "choice" in item:
        label = str(item["choice"])
    if label not in question.labels():
        return Answer(None, confidence)
    return Answer(
        label,
        confidence if confidence is not None else probabilities.get(label),
        probabilities or None,
    )
