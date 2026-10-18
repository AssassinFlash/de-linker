"""deepseek-flash reads an image: one call per image, JSON back (#236).

The only model that sees a customer's file is deepseek-flash on the official DeepSeek
API (AGENTS.md §5, the Genie channel); the image goes as an OpenAI-compatible
`image_url` block with a base64 data URL, and `response_format: json_object` makes the
answer a JSON object without code fences (docs/research/2026-10-17-deepseek-flash-
vision/ §3.1, §6: probe P1, HTTP 200 in 2.3 s, brand, model and nine ratings read
exactly). The call is its own, before the turn's agent runs (ticket #236: "单独调用一次
deepseek-flash 抽取"); the agent only reads the text this returns.

Every failure is explicit: a 4xx is raised at once with the API's own message (a 400
is how the API refuses a file it cannot take, research §6.5), a 5xx, a 429 or a broken
connection is tried once more and then raised. Nothing falls back to another model.
The key, the address and the model name are the chat model's (agent.py, handed in by
app.py), never written anywhere.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

# One image read: probe P1 took 2.3 s at 611 tokens in and 414 out (research §3.4);
# a document page writes more text. Thirty seconds holds a slow answer and still leaves
# the turn time for its agent inside the shell's 60 s proxy timeout (Proxy.php).
TIMEOUT_SECONDS = 30.0
# A failed connection, a 429 or a 5xx is tried once more after a short pause (the
# ability client's first back-off step, abilities.py).
ATTEMPTS = 2
PAUSE_SECONDS = 0.25


@dataclass(frozen=True)
class Instruction:
    """What deepseek-flash is asked about one image, and how it answers.

    `json`: a JSON object (`response_format: json_object`); otherwise plain text,
    returned as `{"text": …, "truncated": bool}`, so an answer cut at `max_tokens`
    is still the text read so far (a cut JSON object is no answer at all).
    """

    text: str
    json: bool = True
    max_tokens: int | None = None


# Reads one JPEG with one instruction; returns the answer as an object.
See = Callable[[bytes, Instruction], dict[str, Any]]


class VisionError(RuntimeError):
    """deepseek-flash did not read the image; the message says why."""


class Vision:
    """The official API's chat completions, for one image at a time."""

    def __init__(
        self,
        key: str,
        base_url: str,
        model: str,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._key = key
        self._model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._client = httpx.Client(timeout=TIMEOUT_SECONDS, transport=transport)
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def __call__(self, jpeg: bytes, instruction: Instruction) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction.text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64,"
                                + base64.b64encode(jpeg).decode("ascii")
                            },
                        },
                    ],
                }
            ],
            # Transcription needs no reasoning: on the 11 photos of eval/attachments a
            # read took 2.9–31.4 s with thinking on (the default) and 0.9–4.0 s with
            # it off, the models read the same or left null (never another model);
            # one photo timed out twice with it on (docs/acceptance/2026-10-18/236/
            # thinking.md). The switch is the official API's (research S16,
            # "thinking"); the turn's agent keeps thinking on (agent.py).
            "thinking": {"type": "disabled"},
        }
        if instruction.json:
            payload["response_format"] = {"type": "json_object"}
        if instruction.max_tokens:
            payload["max_tokens"] = instruction.max_tokens
        body = self._post(payload)
        try:
            choice = body["choices"][0]
            content = choice["message"]["content"]
            if not instruction.json:
                if not isinstance(content, str):
                    raise TypeError("no text")
                return {
                    "text": content,
                    "truncated": choice.get("finish_reason") == "length",
                }
            answer = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            log.error("genie vision: unreadable answer from deepseek-flash: %s", error)
            raise VisionError(f"unreadable answer: {error}") from error
        if not isinstance(answer, dict):
            log.error(
                "genie vision: deepseek-flash answered %s, not an object",
                type(answer).__name__,
            )
            raise VisionError("the answer is not a JSON object")
        return answer

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._key}"}
        last = ""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = self._client.post(self._url, json=payload, headers=headers)
            except httpx.TransportError as error:
                last = f"connection: {error}"
            else:
                if response.status_code < 400:
                    data = response.json()
                    if isinstance(data, dict):
                        return data
                    last = "the response is not a JSON object"
                    break
                last = f"HTTP {response.status_code}: {_message(response)}"
                if response.status_code != 429 and response.status_code < 500:
                    # The API refused the request (a 400 for a file it cannot take):
                    # trying again sends the same refusal.
                    log.error(
                        "genie vision: deepseek-flash refused the image: %s", last
                    )
                    raise VisionError(last)
            if attempt < ATTEMPTS:
                log.warning(
                    "genie vision: attempt %d failed, retrying: %s", attempt, last
                )
                self._sleep(PAUSE_SECONDS)
        log.error("genie vision: deepseek-flash did not read the image: %s", last)
        raise VisionError(last)


def _message(response: httpx.Response) -> str:
    """The API's own error message, without anything the request carried."""
    try:
        data = response.json()
    except ValueError:
        return response.text[:300]
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return str(error["message"])[:300]
    return str(data)[:300]
