"""The conversation summary an inquiry carries (#244, docs/specs/13-genie.md).

When a customer who talked with Genie sends an inquiry, the inquiry can carry a
summary of that conversation, and the request form is prefilled with the
quantities, project conditions and note the customer gave in it (acceptance A7).
deepseek-flash writes the summary, on the official DeepSeek API only (AGENTS.md
§5), from the conversation text and the names of the products its cards showed;
nothing about the customer's identity is sent (the request schema has no field
for it).

Its answer is checked before anything uses it:

- the shape: one JSON object with bounded fields (MAX_*), or `unreadable`;
- no price, cost or currency anywhere (`price`): prices come only from the
  account-aware price facts (#242), never from a summary;
- every figure in the text was said in the conversation or is in a product name
  (`figure`);
- each quantity names a product of the conversation and a number the customer
  stated; a quantity that does not is dropped and named in `dropped`.

A refused or failed summary raises `SummaryError` with the reason. The caller
(WordPress, Linker\\Tools\\Genie\\InquirySummary) then assembles its own summary by
rule and records why; an inquiry is never held up by this call.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import httpx
from pydantic import Field, ValidationError

from linker_genie.agent import deepseek_access, model_name
from linker_genie.provider_budget import Transport
from linker_genie.schema import Locale, Strict, TurnMessage

PROMPT = Path(__file__).resolve().parents[2] / "prompts" / "summary.md"

# The bounds of an answer. Measured 2026-10-18 on twelve EN/DE conversations
# (eval/summary/, docs/acceptance/2026-10-18/244/summary-eval.md): the longest
# summary 283 characters, at most five conditions of at most 40 characters, the
# longest note 77 characters. Each bound is about three times the measured
# longest, so a valid answer is never cut, and a runaway one is refused.
MAX_SUMMARY = 800
MAX_CONDITIONS = 6
MAX_CONDITION = 120
MAX_NOTE = 500
# One line per product of the conversation, which shows at most six cards an answer
# (route.SEARCH_LIMIT); twelve covers two answers' worth.
MAX_QUANTITIES = 12
# The largest quantity a request field takes: Woo's own quantity input has no upper
# bound, so this only keeps a runaway number out of the prefill.
MAX_QUANTITY = 9999
# The conversation the summary may read: the thread WordPress keeps
# (Linker\Tools\Genie\Thread::LIMIT, 60) plus its last answer.
MAX_MESSAGES = 61
# The products the conversation's cards showed: at most six a card block
# (route.SEARCH_LIMIT) over the answers of a kept thread; forty is far above any
# conversation in the live turn log and only bounds the request.
MAX_PRODUCTS = 40
# The completion budget: measured completions (reasoning included) stayed under 550
# tokens on the eval set; 2000 leaves room without letting a runaway answer run on.
MAX_TOKENS = 2000
# One attempt, eight seconds: measured latencies with thinking on were 0.9-2.7 s on
# the eval set. WordPress waits for this answer while it renders the request page
# (its own timeout is ten seconds), so a slow call falls back to the rule-based
# summary instead of being retried.
TIMEOUT_SECONDS = 8.0

_LANGUAGE = {"en": "English", "de": "German (formal, Sie)"}

# A price: a currency sign or name, or the German ",-" after an amount.
_PRICE = re.compile(
    r"[€$£]|\b(?:eur|usd|gbp|chf|euros?|dollars?)\b|\d\s*,-", re.IGNORECASE
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# Number words a customer writes a quantity with (EN/DE, one to twelve). "a"/"an"
# are left out: they are in nearly every sentence and would vouch for any "1".
_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "dozen": 12,
    "ein": 1, "eine": 1, "einen": 1, "einem": 1, "einer": 1, "eins": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7,
    "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
}  # fmt: skip
_WORD = re.compile(r"[^\W\d_]+")


class SummaryProduct(Strict):
    id: int = Field(ge=1)
    name: str = Field(max_length=300)


class SummaryRequest(Strict):
    """What the summary may read: the conversation and its products, nothing else."""

    locale: Locale = "en"
    messages: list[TurnMessage] = Field(max_length=MAX_MESSAGES)
    products: list[SummaryProduct] = Field(
        default_factory=list, max_length=MAX_PRODUCTS
    )


class Quantity(Strict):
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=MAX_QUANTITY)


class Answer(Strict):
    """The model's answer, as the prompt asks for it."""

    summary: str = Field(max_length=MAX_SUMMARY)
    quantities: list[Quantity] = Field(max_length=MAX_QUANTITIES)
    conditions: list[Annotated[str, Field(max_length=MAX_CONDITION)]] = Field(
        max_length=MAX_CONDITIONS
    )
    note: str = Field(max_length=MAX_NOTE)


class Summary(Answer):
    """A checked answer, with the quantities that did not pass."""

    dropped: list[str] = Field(default_factory=list)


class SummaryError(Exception):
    """The summary was refused or could not be made; `reason` says why."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ModelUnavailable(Exception):
    """The model call failed; the message is the cause."""


Complete = Callable[[str, str], str]


def summarise(request: SummaryRequest, complete: Complete) -> Summary:
    """The checked summary of the conversation, or SummaryError with the reason."""
    said = [
        m.content for m in request.messages if m.role == "user" and m.content.strip()
    ]
    if not said:
        raise SummaryError("empty")
    products = "\n".join(f"{p.id}: {p.name}" for p in request.products) or "(none)"
    chat = "\n".join(f"{m.role}: {m.content}" for m in request.messages)
    user = f"LANGUAGE: {_LANGUAGE[request.locale]}\nPRODUCTS:\n{products}\nCONVERSATION:\n{chat}"
    try:
        raw = complete(PROMPT.read_text(encoding="utf-8"), user)
    except ModelUnavailable as error:
        raise SummaryError(f"model: {error}") from error
    try:
        answer = Answer.model_validate(json.loads(raw))
    except (ValueError, ValidationError) as error:
        raise SummaryError("unreadable") from error
    if not answer.summary.strip():
        raise SummaryError("unreadable")
    texts = [answer.summary, *answer.conditions, answer.note]
    if any(_PRICE.search(text) for text in texts):
        raise SummaryError("price")
    known = _figures(
        " ".join(
            [
                *(m.content for m in request.messages),
                *(p.name for p in request.products),
            ]
        ),
        words=True,
    )
    # The summary's own figures are its digits: its words ("eine Lieferung") are
    # articles as often as numbers, so only the conversation's words vouch.
    if any(not _figures(text, words=False) <= known for text in texts):
        raise SummaryError("figure")
    stated = _figures(" ".join(said), words=True)
    offered = {p.id for p in request.products}
    kept: list[Quantity] = []
    dropped: list[str] = []
    for line in answer.quantities:
        if line.product_id not in offered:
            dropped.append(f"product {line.product_id}")
        elif str(line.quantity) not in stated:
            dropped.append(f"quantity {line.quantity}")
        else:
            kept.append(line)
    return Summary(
        summary=answer.summary.strip(),
        quantities=kept,
        conditions=[c.strip() for c in answer.conditions if c.strip()],
        note=answer.note.strip(),
        dropped=dropped,
    )


def _figures(text: str, words: bool) -> set[str]:
    """The numbers a text states: each written figure with and without its
    separators and its parts ("9.500" → 9500, 9, 500), and with `words` its number
    words as digits ("drei" → 3)."""
    found: set[str] = set()
    for figure in _NUMBER.findall(text):
        found.add(re.sub(r"[.,]", "", figure))
        found.update(re.split(r"[.,]", figure))
    for word in _WORD.findall(text.lower()) if words else []:
        if word in _WORDS:
            found.add(str(_WORDS[word]))
    return {f.lstrip("0") or "0" for f in found}


def deepseek(transport: httpx.BaseTransport | None = None) -> Complete:
    """deepseek-flash on the official DeepSeek API, JSON output, one attempt."""
    access = deepseek_access()
    base, key = access.base_url, access.key

    def complete(system: str, user: str) -> str:
        try:
            with httpx.Client(
                transport=Transport("deepseek", transport), timeout=TIMEOUT_SECONDS
            ) as client:
                response = client.post(
                    base.rstrip("/") + "/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model_name(),
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": MAX_TOKENS,
                    },
                )
        except httpx.TimeoutException as error:
            raise ModelUnavailable("timeout") from error
        except httpx.HTTPError as error:
            raise ModelUnavailable(type(error).__name__) from error
        if response.status_code != 200:
            raise ModelUnavailable(f"HTTP {response.status_code}")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise ModelUnavailable("no content") from error
        if not isinstance(content, str):
            raise ModelUnavailable("no content")
        return content

    return complete
