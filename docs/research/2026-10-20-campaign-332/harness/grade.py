"""Grade one recorded failure case. The rules are the campaign's checks.

A case passes only when the failure is explicit, a failed turn did not
state a measurement, and a retry — when one was run — succeeded. UI
blankness is graded from the HTTP body the shell would parse; a browser
note can override it.

The turn log's provider and model are not graded. app.py writes them from
provider_name() and model_name() (agent.py: CHAT_PROVIDER is the constant
"deepseek"; model_name() is GENIE_MODEL or "deepseek-flash"). Those columns
are the configured names, not the model that produced the tokens, so a
check against them cannot show a silent switch.
"""

from __future__ import annotations

import re
from typing import Any

# Customer-visible failure language already shipped (template.DEGRADED,
# App.tsx / Hero.tsx, Attachments throttled copy).
EXPLICIT_BITS = (
    "could not answer",
    "could not",
    "try again",
    "nicht beantworten",
    "versuchen sie",
    "did not answer",
    "genie did not",
    "hourly limit",
    "throttled",
    "not configured",
)
# A measurement the customer could take as a product fact. Model codes
# such as H2-10K-T2 do not match: the unit is required.
MEASUREMENT = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:kwh|kw|w|v|a|€|eur|mm)\b",
    re.IGNORECASE,
)


def _text(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("answer_text") or ""),
        str(row.get("error_code") or ""),
        str(row.get("error_message") or ""),
        str(row.get("ui_text") or ""),
    ]
    return "\n".join(parts).lower()


def _has_failure_sentence(row: dict[str, Any]) -> bool:
    return any(bit in _text(row) for bit in EXPLICIT_BITS)


def customer_visible_outage(row: dict[str, Any]) -> bool:
    """True when the customer can see that the turn failed.

    A 200 whose SSE has no `done` is the shell's error path: parseStream
    throws and the dock shows "Genie did not answer. Please try again."
    """
    http = row.get("http")
    if isinstance(http, int) and http >= 400:
        return True
    if row.get("transport_error"):
        return True
    if http == 200 and row.get("done") is False and row.get("stream_prefix"):
        return True
    return _has_failure_sentence(row)


def fabricated(row: dict[str, Any]) -> bool:
    """A measurement in an answer the customer can read on a failed turn.

    A stream that never reaches `done` is not rendered: the shell throws,
    and a reload ignores that stream. A healthy burst may cite a real
    catalogue rating; that is not a failed value written as fact.
    """
    if row.get("allow_measurements") is True:
        return False
    if row.get("done") is not True:
        return False
    return MEASUREMENT.search(str(row.get("answer_text") or "")) is not None


def blank(row: dict[str, Any]) -> bool:
    """A finished success with nothing to read and no error."""
    http = row.get("http")
    if http not in (None, 200):
        return False
    if row.get("transport_error"):
        return False
    if str(row.get("answer_text") or "").strip():
        return False
    if row.get("ui_text"):
        return False
    blocks = row.get("blocks")
    if isinstance(blocks, list) and blocks:
        return False
    return True


def healthy(row: dict[str, Any]) -> bool:
    """A normal turn: 200, a finished stream, and something to read."""
    return (
        row.get("http") == 200
        and row.get("done") is True
        and bool(str(row.get("answer_text") or "").strip())
        and not row.get("transport_error")
    )


def grade(row: dict[str, Any]) -> dict[str, Any]:
    """Return the row plus verdict and the checks that failed."""
    reasons: list[str] = []
    kind = str(row.get("kind") or "fault")
    if kind == "control":
        if not healthy(row):
            reasons.append("healthy turn did not answer")
    elif kind == "burst":
        children = row.get("children")
        if not isinstance(children, list) or not children:
            reasons.append("burst recorded no turns")
        else:
            for child in children:
                if not isinstance(child, dict):
                    reasons.append("burst child is not a record")
                    continue
                if healthy(child) or customer_visible_outage(child):
                    if not healthy(child) and fabricated(child):
                        reasons.append(
                            "burst turn states a measurement after a failure"
                        )
                    continue
                reasons.append(
                    f"burst turn {child.get('id')} is neither a success nor an explicit failure"
                )
    else:
        channel = str(row.get("explicit_channel") or "customer")
        if channel == "meta":
            meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
            if not (isinstance(meta, dict) and meta.get("jev_error")):
                reasons.append("jev failure is not in SSE meta")
        elif not customer_visible_outage(row):
            reasons.append("failure is not visible to the customer")
        if kind != "fault":
            reasons.append(f"unknown kind {kind}")
        if fabricated(row):
            reasons.append("answer states a measurement on a failed turn")
        if blank(row) and not customer_visible_outage(row):
            reasons.append("success response has no answer and no error")
        if row.get("partial_shown") is True:
            reasons.append("a cut stream was shown as an answer")
        if row.get("reload_hides_error") is True:
            reasons.append("reload shows the question with no error and no answer")
        retry = row.get("retry")
        if isinstance(retry, dict) and retry.get("ok") is not True:
            reasons.append("retry after the fault was cleared did not succeed")
    verdict = "defect" if reasons else "pass"
    graded = dict(row)
    graded["verdict"] = verdict
    graded["reasons"] = reasons
    return graded
