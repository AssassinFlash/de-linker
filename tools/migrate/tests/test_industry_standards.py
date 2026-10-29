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
        '<style data-site-css="service-redesign.css">.x{color:red}\n'
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
    assert 'aria-label="Services for trade customers"' in english
    assert 'aria-label="Leistungen für Fachpartner"' in german


def test_the_previous_english_accessible_name_is_upgraded_without_a_second_row() -> (
    None
):
    current = page().replace(
        standards.SERVICE_LEDGER_INSERTION_POINT,
        standards.PREVIOUS_EN_MARKUP + "\n" + standards.SERVICE_LEDGER_INSERTION_POINT,
        1,
    )
    upgraded = standards.plan_page(current, "en")
    assert upgraded == current.replace(
        standards.PREVIOUS_EN_MARKUP, standards.EN_MARKUP, 1
    )
    assert upgraded.count('class="lk-trade-standards"') == 1
    assert standards.plan_page(upgraded, "en") == upgraded


def test_planning_is_idempotent_and_preserves_unrelated_bytes() -> None:
    original = page()
    planned = standards.plan_page(original, "en")
    assert standards.plan_page(planned, "en") == planned
    assert (
        original.replace(
            standards.SERVICE_LEDGER_INSERTION_POINT,
            standards.EN_MARKUP + "\n" + standards.SERVICE_LEDGER_INSERTION_POINT,
            1,
        )
        == planned
    )
    assert planned.count(standards.EN_MARKUP) == 1
    assert (
        planned.split(standards.EN_MARKUP, 1)[0]
        == original.split(standards.SERVICE_LEDGER_INSERTION_POINT, 1)[0]
    )
    assert "#service-redesign .lk-trade-standards" not in planned


def test_the_row_style_lives_in_the_existing_windpress_source() -> None:
    stylesheet = (
        Path(__file__).parents[3]
        / "plugins/linker-commerce/content/windpress/service-intro.css"
    ).read_text()
    assert "#service-redesign .lk-trade-standards" in stylesheet


def test_a_drifted_or_wrong_page_is_refused() -> None:
    with pytest.raises(ValueError, match="EN or DE"):
        standards.plan_page(page('id="another-page"'), "en")
    drifted = page().replace(
        standards.SERVICE_LEDGER_INSERTION_POINT, "<div>changed</div>", 1
    )
    with pytest.raises(ValueError, match="not unique"):
        standards.plan_page(drifted, "en")


def test_reviewed_row_has_no_invented_trade_numbers_or_incoterms() -> None:
    english, german = standards.plan_pair(page(), page())
    for source in (english, german):
        assert not any(value in source for value in standards.FORBIDDEN)


def test_the_trade_library_has_no_online_warranty_or_incoterm_claim() -> None:
    trade_library = (
        Path(__file__).parents[3] / "plugins/linker-commerce/data/faq-trade.json"
    ).read_text()
    for stale_claim in (
        "Open Warranty & Replacements",
        "signed-in account",
        "angemeldete Konto",
        "Incoterms",
        "EXW",
        "DAP",
    ):
        assert stale_claim not in trade_library


def test_page_snapshot_retention_keeps_the_latest_three_verified_files(
    tmp_path: Path,
) -> None:
    for stamp in ("01", "02", "03", "04"):
        (tmp_path / f"industry-standards-before-{stamp}.json").write_text(
            '{"readback_verified": true}'
        )
    removed = standards.prune_page_backups(tmp_path)
    assert removed == [str(tmp_path / "industry-standards-before-01.json")]
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "industry-standards-before-02.json",
        "industry-standards-before-03.json",
        "industry-standards-before-04.json",
    ]
