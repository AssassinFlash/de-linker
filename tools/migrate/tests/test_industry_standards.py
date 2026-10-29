"""The reviewed trade-standard row is complete, bilingual and idempotent."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "industry_standards", Path(__file__).parents[1] / "industry-standards.py"
)
assert spec and spec.loader
standards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(standards)


def page(root: str = 'id="service-redesign"') -> str:
    return (
        "<style data-site-css=\"service-redesign.css\">.x{color:red}\n"
        "@media (max-width: 1100px) { .x{color:blue} }</style>\n"
        f'<div {root}><section id="deliverables"><div class="lk-container">'
        '<div class="service-intro">Keep this copy.</div>\n'
        '<div class="service-ledger">Keep this ledger.</div>'
        "</div></section></div>"
    )


def test_the_row_adds_the_exact_english_and_german_facts() -> None:
    english, german = standards.plan_pair(page(), page())
    for value in (
        "Orders ship from our warehouse.",
        "freight is quoted separately for the destination.",
        "We provide product training for installers.",
        "Our team handles after-sales support.",
        "Warranty terms follow the order.",
        "We work with distributors and resellers.",
    ):
        assert value in english
    for value in (
        "Bestellungen versenden wir ab Lager.",
        "Fracht gesondert nach Zielort",
        "Für Installateure bieten wir Produktschulungen an.",
        "Unser Team übernimmt den Kundendienst.",
        "Garantiebedingungen richten sich nach der Bestellung.",
        "Wir arbeiten mit Distributoren und Wiederverkäufern zusammen.",
    ):
        assert value in german


def test_planning_is_idempotent_and_preserves_unrelated_bytes() -> None:
    original = page()
    planned = standards.plan_page(original, "en")
    assert standards.plan_page(planned, "en") == planned
    assert original.replace(
        standards.CSS_ANCHOR, standards.CSS + "\n" + standards.CSS_ANCHOR, 1
    ).replace(
        standards.LEDGER_ANCHOR,
        standards.EN_MARKUP + "\n" + standards.LEDGER_ANCHOR,
        1,
    ) == planned
    assert planned.count(standards.CSS) == 1
    assert planned.count(standards.EN_MARKUP) == 1


def test_a_partial_increment_is_refused() -> None:
    partial = page().replace(
        standards.LEDGER_ANCHOR,
        standards.EN_MARKUP + "\n" + standards.LEDGER_ANCHOR,
        1,
    )
    with pytest.raises(ValueError, match="partially"):
        standards.plan_page(partial, "en")


def test_a_drifted_or_wrong_page_is_refused() -> None:
    with pytest.raises(ValueError, match="EN or DE"):
        standards.plan_page(page('id="another-page"'), "en")
    drifted = page().replace(standards.LEDGER_ANCHOR, "<div>changed</div>", 1)
    with pytest.raises(ValueError, match="not unique"):
        standards.plan_page(drifted, "en")


def test_reviewed_row_has_no_invented_trade_numbers_or_incoterms() -> None:
    english, german = standards.plan_pair(page(), page())
    for source in (english, german):
        assert not any(value in source for value in standards.FORBIDDEN)
