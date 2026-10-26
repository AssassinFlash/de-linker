"""Present the retained capacity assumption; never resolve or recalculate it."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from linker_engine.models import ReportRow, ReportSection

from .canonical import Object
from .capacity_window import REFERENCE_CAPACITY
from .report_copy import text


def capacity_section(
    parameters: Object,
    locale: str,
    number: Callable[[Any, str, str], str],
    *,
    identity: str,
    unit_names: str = "",
) -> ReportSection | None:
    facts = cast(Object, parameters.get("source_facts", {}))
    reference = facts.get("capacity_window_assumption")
    if not isinstance(reference, dict) or reference.get("basis") != REFERENCE_CAPACITY:
        return None
    rows = [
        ReportRow(
            label=text("capacity_reference_published", locale),
            value=number(reference["published_usable_energy_kwh"], locale, "kWh"),
        ),
        ReportRow(
            label=text("plant_unit_window", locale),
            value=number(reference["window_kwh"], locale, "kWh"),
        ),
    ]
    paragraphs = [text("capacity_reference_scope", locale)]
    qualifier = reference.get("manufacturer_qualifier")
    if isinstance(qualifier, dict):
        original = qualifier.get("source_text")
        if isinstance(original, dict) and isinstance(original.get(locale), str):
            paragraphs.append(cast(str, original[locale]))
    fact = facts.get(str(reference["reference_fact_id"]))
    source = fact.get("source") if isinstance(fact, dict) else None
    if isinstance(source, dict):
        rows.append(
            ReportRow(
                label=f"{text('source', locale)} · {text('page', locale)} {source['page']}",
                value=str(source["url"]),
                href=str(source["url"]),
            )
        )
    return ReportSection(
        id=identity,
        title=(unit_names + " · " if unit_names else "")
        + text("capacity_reference_title", locale),
        paragraphs=paragraphs,
        rows=rows,
    )
