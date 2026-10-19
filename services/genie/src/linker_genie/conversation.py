"""The customer's own words on a turn request.

`agent`, `understand` and `app` each used to scan `request.messages` for the
last user message. One helper keeps that scan, and the configurator prefill
reads every user message through the same list (#365).
"""

from __future__ import annotations

from linker_genie.schema import TurnRequest


def customer_messages(request: TurnRequest) -> list[str]:
    """User-message texts in conversation order. Assistant text is not included."""
    return [message.content for message in request.messages if message.role == "user"]


def last_customer_message(request: TurnRequest) -> str:
    """The user message this turn answers, or "" when the thread has none."""
    messages = customer_messages(request)
    return messages[-1] if messages else ""
