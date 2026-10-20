"""The class of a failure, set where it is caught (#410).

`cycle` used to read the class back out of the sentence. A change to the
wording then shipped a normal recommendation. The class now travels with
the failure: on the exception (`failure_kind`, or `AbilityError.fatal`)
and on the note the catch site puts in `call_failures`.

Two library sentences stay, because pydantic-ai uses one exception class
for both. `OpenAIChatModel._process_response` raises
`UnexpectedModelBehavior` for a body that is not a chat completion
(`Invalid response from … chat completions endpoint`), which is the empty
stream. `tool_manager._check_max_retries` raises the same class for the
tool budget (`exceeded max retries count of`). The budget is not a fatal
class; `cycle` treats that sentence as `exhausted`. A chat 5xx or 429 is
`ModelHTTPError.status_code`, not the message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from linker_genie.abilities import AbilityError
from linker_genie.embedding import sentence_is_encoder_failure

# Passed by cycle.fatal_class (#410) and read by template.fallback. `exhausted`
# (#366) is separate: the tool never returned, so that path shows no cards.
FailureClass = Literal["model", "retrieval", "ability"]


@dataclass(frozen=True)
class RecordedFailure:
    """One failure the turn log can show, with the class known at the catch."""

    text: str
    kind: FailureClass | None = None

    def dump(self) -> dict[str, str]:
        """The JSON object `prepared.log["call_failures"]` stores."""
        payload = {"text": self.text}
        if self.kind is not None:
            payload["kind"] = self.kind
        return payload


def note(error: BaseException, *, prefix: str = "") -> RecordedFailure:
    """The note a catch site records. `prefix` is the tool name."""
    text = f"{prefix}: {error}" if prefix else str(error)
    return RecordedFailure(text, kind_of(error))


def _row_text(entry: object) -> str | None:
    """The text of a stored row (`{text, kind?}` or a string), else None."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        text = entry.get("text")
        if isinstance(text, str):
            return text
    return None


def is_row(entry: object) -> bool:
    """True when `entry` is a stored `call_failures` row: a string or `{text}`."""
    return _row_text(entry) is not None


def from_log(entry: object) -> RecordedFailure:
    """A log entry: a note this module wrote, or a plain string from an older row.

    A string has no class. The words are not read again (#410).
    """
    if isinstance(entry, RecordedFailure):
        return entry
    text = _row_text(entry)
    if text is None:
        return RecordedFailure(str(entry))
    if isinstance(entry, dict):
        return RecordedFailure(text, _as_kind(entry.get("kind")))
    return RecordedFailure(text)


def failure_text(entry: object) -> str:
    """The sentence of a log entry, string or note."""
    if isinstance(entry, RecordedFailure):
        return entry.text
    text = _row_text(entry)
    return text if text is not None else ""


def kind_of(error: BaseException) -> FailureClass | None:
    """The class `error` already carries, or None when it is not a failed turn.

    An `EmbeddingError` or `KnowledgeUnavailable` is retrieval even when its
    message is not one of the older HTTP sentences (`unexpected response`,
    `returned N embeddings for M texts`). An ability 5xx, a timeout and the
    retries giving up are `AbilityError.fatal`. A 4xx is not. A page outage
    is not: the answer goes on without the page.
    """
    if isinstance(error, AbilityError):
        return "ability" if error.fatal else None
    marked = getattr(error, "failure_kind", None)
    if marked == "retrieval":
        return "retrieval"
    library = _library_model_kind(error)
    if library is not None:
        return library
    # The type was dropped and only the sentence remains (a probe that
    # raises RuntimeError of the message, or a wrapper that did). The
    # fragments live next to the raises, not here.
    text = str(error)
    if sentence_is_encoder_failure(text) or _is_index_failure(text):
        return "retrieval"
    return None


def _as_kind(value: object) -> FailureClass | None:
    if value == "model" or value == "retrieval" or value == "ability":
        return value
    return None


def _library_model_kind(error: BaseException) -> FailureClass | None:
    from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

    if isinstance(error, ModelHTTPError):
        if error.status_code == 429 or 500 <= error.status_code <= 599:
            return "model"
        return None
    if not isinstance(error, UnexpectedModelBehavior):
        return None
    message = str(error)
    # tool_manager._check_max_retries. The tool budget, not a model outage.
    if "exceeded max retries count of" in message:
        return None
    # OpenAIChatModel._process_response, including an empty stream.
    if (
        message.startswith("Invalid response from ")
        and "chat completions endpoint" in message
    ):
        return "model"
    return None


def _is_index_failure(text: str) -> bool:
    from linker_genie.knowledge import is_index_failure

    return is_index_failure(text)
