"""Plan narrow corrections to existing Utility and Services controls.

This module does not write WordPress. Use the existing reviewed_page_pair
transport with a verified recovery baseline, a current scoped pair increment,
reviewed current-state digest, and exact post-write readback.
"""

from __future__ import annotations

import re


def _utility(content: str) -> tuple[str, str]:
    if len(re.findall(r'<section\b[^>]*\bid="workflow"', content)) != 1:
        raise ValueError("Expected one existing workflow section")
    old, new = 'href="#exec-deck-nav"', 'href="#workflow"'
    if content.count(old) == 1 and content.count(new) == 0:
        return content.replace(old, new, 1), "old"
    if content.count(old) == 0 and content.count(new) == 1:
        return content, "final"
    raise ValueError("Workflow link changed or is ambiguous; nothing planned")


def _services(content: str) -> tuple[str, str]:
    states: list[str] = []
    for tabs in ("stageTabs", "roleTabs"):
        old = (
            "if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {\n"
            "        event.preventDefault();\n"
            "        const next = (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
        new = (
            "if (['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) {\n"
            "        event.preventDefault();\n"
            "        const next = event.key === 'Home' ? 0\n"
            f"          : event.key === 'End' ? {tabs}.length - 1\n"
            "          : (i + (event.key === 'ArrowRight' ? 1 : -1) "
            f"+ {tabs}.length) % {tabs}.length;"
        )
        if content.count(old) == 1 and content.count(new) == 0:
            states.append("old")
            content = content.replace(old, new, 1)
        elif content.count(old) == 0 and content.count(new) == 1:
            states.append("final")
        else:
            raise ValueError("Service key handler changed; nothing planned")
    if states[0] != states[1]:
        raise ValueError("Partially changed service handlers; inspect before retrying")
    return content, states[0]


def plan_pair(family: str, english: str, german: str) -> tuple[str, str]:
    """Accept a complete old or final pair; preserve all other source bytes."""
    if family not in {"utility", "services"}:
        raise ValueError("Only Utility and Services are eligible")
    root = "tv-utility-page-v1" if family == "utility" else "service-redesign"
    transform = _utility if family == "utility" else _services
    planned: list[str] = []
    states: list[str] = []
    for content in (english, german):
        if len(re.findall(r'\bid="' + root + '"', content)) != 1:
            raise ValueError("Expected one existing marketing root")
        after, state = transform(content)
        planned.append(after)
        states.append(state)
    if states[0] != states[1]:
        raise ValueError("Partially changed language pair; inspect before retrying")
    return planned[0], planned[1]
