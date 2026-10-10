"""The judges: System One decision models and chat LLMs, behind one call.

A System One judge (TypeSafe's Jev through aihubmix, or an open decision model served
by llama.cpp's /v1/systemone) returns typed answers with probabilities. A chat judge
(an LLM through aihubmix, or an open LLM served by llama.cpp) gets the same questions in
a prompt and replies in JSON. Either way one call evaluates one item.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from .http import HttpError, aihubmix_credentials, post_json
from .rubric import Question, chat_messages

Kind = Literal["system_one", "chat"]
AIHUBMIX = "aihubmix"


@dataclass(frozen=True)
class Judge:
    name: str
    kind: Kind
    model: str
    endpoint: str
    """`AIHUBMIX`, or the base URL of a local llama.cpp server."""
    price_in: float = 0.0
    """USD per million input tokens (aihubmix billing config, data/prices.json)."""
    price_out: float = 0.0
    temperature: float | None = None
    json_mode: bool = False
    extra: dict[str, Any] = field(default_factory=dict)
    weights: str = "closed"
    """"closed", or the open checkpoint and its quantization."""

    @property
    def local(self) -> bool:
        return self.endpoint != AIHUBMIX


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
            response = post_json(base + "/v1/chat/completions", body, key)
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
    cost = (tokens_in * judge.price_in + tokens_out * judge.price_out) / 1_000_000
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

    Nothing is repaired or re-asked: an invalid answer counts as a disagreement.
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
