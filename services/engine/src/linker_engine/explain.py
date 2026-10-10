"""The value a rule read, in words, for the screen and the report alike."""

from __future__ import annotations

from .texts import Locale, fmt, has, t, tn

UNKNOWN = "value.unknown"


def value_text(
    rule_id: str, value: object, limit: object, locale: Locale, **context: object
) -> str:
    """For example "20 kW for a 10 kWp array" or "3-phase, as selected"."""
    if value is None:
        return t(UNKNOWN, locale)
    if rule_id == "application":
        key = f"value.application.{value}"
        shown = t(key, locale) if has(key) else str(value)
        return t(
            "value.application_match" if value == limit else "value.application",
            locale,
            value=shown,
            limit=t(f"value.application.{limit}", locale),
        )
    if rule_id == "phase":
        return t(
            "value.phase_match" if value == limit else "value.phase",
            locale,
            value=value,
            limit=limit,
        )
    if rule_id == "dc_ac_ratio" and isinstance(value, int | float):
        # A ratio reads as one: 1.00 rather than 1.
        return t(
            "value.dc_ac_ratio",
            locale,
            value=fmt(value, locale, 2),
            limit=fmt(limit, locale, 2),
        )
    if rule_id == "backup":
        if value == "accessory":
            return t("value.backup.accessory", locale)
        return t("value.backup.native", locale, value=value)
    if rule_id in (
        "string_count",
        "string_voltage",
        "string_current",
        "engineering_data",
    ):
        return t("value.modules", locale, value=value)
    if rule_id == "battery_release" and isinstance(value, int):
        return tn("value.batteries", value, locale, value=value)
    key = f"value.{rule_id}"
    if has(key):
        return t(
            key,
            locale,
            value=value,
            limit=limit if limit is not None else "",
            **context,
        )
    return fmt(value, locale)
