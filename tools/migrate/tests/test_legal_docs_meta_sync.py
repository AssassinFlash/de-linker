"""The stale DOCS version lines re-date exactly, and drift is refused."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "sync", Path(__file__).parents[1] / "legal-docs-meta-sync.py"
)
assert spec and spec.loader
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

# Byte-for-byte as rendered on de-linker.com: the stale copy (Imprint and
# Privacy Policy, EN and DE, read 2026-10-29) and the re-dated copy the Terms
# of Sale and Refund and Returns pages already carry.
STALE_TERMS = (
    "en: ['Terms of Sale', 'Version 1.2 \u00b7 30 July 2026'], "
    "de: ['Verkaufsbedingungen', 'Version 1.2 \u00b7 Stand: 30. Juli 2026']"
)
STALE_RETURNS = (
    "en: ['Refund & Returns', 'Version 1.1 \u00b7 30 July 2026'], "
    "de: ['R\u00fcckgabe & Erstattung', 'Version 1.1 \u00b7 Stand: 30. Juli 2026']"
)
FRESH_TERMS = (
    "en: ['Terms of Sale', 'Version 1.2 \u00b7 27 October 2026'], "
    "de: ['Verkaufsbedingungen', 'Version 1.2 \u00b7 Stand: 27. Oktober 2026']"
)
FRESH_RETURNS = (
    "en: ['Refund & Returns', 'Version 1.1 \u00b7 27 October 2026'], "
    "de: ['R\u00fcckgabe & Erstattung', 'Version 1.1 \u00b7 Stand: 27. Oktober 2026']"
)

IMPRINT_LINE = "en: ['Imprint', 'Last updated 29 September 2026'], de: ['Impressum', 'Stand: 29. September 2026']"


def page(terms: str, returns: str) -> str:
    return (
        '<script id="tv-legal-js">/* docs */\n'
        "  var DOCS = [\n"
        f"    {{ doc: 'imprint', path: '/imprint/',\n      {IMPRINT_LINE} }},\n"
        f"    {{ doc: 'terms', path: '/terms-of-sale/',\n      {terms} }},\n"
        f"    {{ doc: 'returns', path: '/refund-returns/',\n      {returns} }}\n"
        "  ];\nvar re = /\\s+/g; \\u003c/svg>\n</script>"
    )


STALE_PAGE = page(STALE_TERMS, STALE_RETURNS)
FRESH_PAGE = page(FRESH_TERMS, FRESH_RETURNS)


def test_re_dates_the_stale_lines_and_touches_nothing_else() -> None:
    fixed = sync.plan_page(STALE_PAGE)
    assert fixed == FRESH_PAGE
    assert sync.plan_page(fixed) == fixed


def test_refuses_partial_mixed_or_unknown_lines() -> None:
    for content in (
        page(STALE_TERMS, FRESH_RETURNS),  # mixed: half re-dated already
        page(FRESH_TERMS, STALE_RETURNS),
        page(STALE_TERMS.replace("1.2", "1.3"), STALE_RETURNS),  # new version
        STALE_PAGE.replace(STALE_RETURNS, STALE_TERMS),  # duplicated line
    ):
        with pytest.raises(ValueError, match="drifted"):
            sync.plan_page(content)


def test_replacements_strings_match_the_live_documents() -> None:
    # The plan itself must spell exactly the stale and the re-dated pairs.
    assert [(old, new) for old, new in sync.REPLACEMENTS] == [
        (STALE_TERMS, FRESH_TERMS),
        (STALE_RETURNS, FRESH_RETURNS),
    ]
