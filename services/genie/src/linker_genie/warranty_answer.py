"""Customer answers assembled from a verified manufacturer's policy passage.

The model selects a topic and the already-tagged answer; it does not paraphrase
coverage, dates, exclusions or the warranty start. Numeric placeholders remain
ordinary document figures and pass through the normal grounding and seal.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from linker_genie.warranty_scope import exclusion_category


def answers(hit: dict[str, Any], notes: Sequence[Any]) -> dict[str, str]:
    """Render only from the validated, tagged policy row and its source notes."""
    chunk = hit.get("chunk_id")
    text = hit.get("text")
    if not isinstance(chunk, str) or not isinstance(text, str) or len(notes) < 6:
        return {}
    lang = notes[0].lang
    if lang not in {"en", "de"} or any(note.lang != lang for note in notes):
        return {}
    lines = text.splitlines()
    row = [
        line for line in lines if line.casefold().startswith("| warranty / garantie |")
    ]
    if len(row) != 1:
        return {}
    period = re.findall(r"\[n([1-9]\d*)=[^\[\]\n]+\]", row[0])
    if len(period) != 1:
        return {}

    def excerpt(note: Any) -> str | None:
        prefix = note.quote.split(":", 1)[0] + ": "
        suffix = f" (p. {note.page})"
        matches = [
            line[len(prefix) : -len(suffix)]
            for line in lines
            if line.startswith(prefix) and line.endswith(suffix)
        ]
        if len(matches) != 1:
            return None
        # A German source list uses an ordinal before the tagged duration;
        # it is a list marker, not a numeric policy value.
        source = re.sub(r"(?<!\w)\d{1,2}\.(?=\s+\[n[1-9]\d*=)", "", matches[0])
        # A policy exception refers to a compatibility list in a parenthesis.
        # Keep that instruction but leave the URL to the cited source document;
        # the answer schema does not permit free-standing URLs in prose.
        source = re.sub(r"\s+https?://[^)]*(?=\))", "", source, flags=re.I)
        source = re.sub(
            r"(\(siehe die Batterie-Kompatibilitätsliste)\s+unter\s+[^)]+(?=\))",
            r"\1",
            source,
            flags=re.I,
        )
        if re.search(r"https?://|www\.", source, re.I):
            return None
        return re.sub(
            r"\[n([1-9]\d*)=[^\[\]\n]+\]",
            lambda match: f"{{fact:{chunk}.n{match.group(1)}}}",
            source,
        ).strip()

    pieces = [excerpt(note) for note in notes]
    if any(piece is None for piece in pieces):
        return {}
    original = [piece for piece in pieces if piece is not None]
    labels = (
        {
            "period": "Limited warranty period",
            "production": "Production condition",
            "overview": "Purchaser condition",
            "start": "Warranty start",
            "effective": "Installation policy",
            "geography": "Purchase and installation condition",
            "coverage": "Coverage and exclusions",
            "reporting": "Reporting a defect",
            "battery_compatibility": "Battery compatibility condition",
            "modification": "Modification condition",
            "force_majeure": "Force majeure condition",
        }
        if lang == "en"
        else {
            "period": "Eingeschränkte Garantiedauer",
            "production": "Bedingung zum Herstellungsdatum",
            "overview": "Bedingung zum Käufer",
            "start": "Beginn der Garantie",
            "effective": "Bedingung zum Installationsdatum",
            "geography": "Bedingung zu Kauf und Installation",
            "coverage": "Deckung und Ausschlüsse",
            "reporting": "Meldung eines Mangels",
            "battery_compatibility": "Bedingung zur Batteriekompatibilität",
            "modification": "Bedingung zu Änderungen",
            "force_majeure": "Bedingung zu höherer Gewalt",
        }
    )

    def sentence(role: str, value: str) -> str:
        return f"{labels[role]}: {value}".rstrip() + (
            "" if value.endswith(".") else "."
        )

    period_answer = sentence("period", f"{{fact:{chunk}.n{period[0]}}}")
    rendered = {
        "period": period_answer + " " + sentence("production", original[0]),
        "production": sentence("production", original[0]),
        "overview": sentence("overview", original[1]),
        "start": sentence("start", original[2]),
        "effective": sentence("effective", original[3]),
        "geography": sentence("geography", original[4]),
        "coverage": sentence("coverage", original[5]),
    }
    for note, piece in zip(notes[6:], original[6:], strict=True):
        category = exclusion_category(note.quote)
        if category in labels:
            rendered[category] = sentence(category, piece)
    rendered["general"] = "\n".join(
        rendered[role]
        for role in (
            "period",
            "overview",
            "start",
            "effective",
            "geography",
            "coverage",
        )
    )
    return rendered
