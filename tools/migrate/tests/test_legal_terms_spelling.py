"""The reviewed Terms correction changes only its two German sentences."""

import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "legal-terms-spelling.py"
spec = importlib.util.spec_from_file_location("legal_terms_spelling", path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

EN = "<p>For B2B sales, risk passes to the buyer.</p>"
DE = (
    '<section id="section-5"><p>Bei B2Bäufen geht die Gefahr auf den Käufer über, '
    "wenn die Ware dem Frachtführer übergeben wird.</p></section>"
    '<section id="section-7"><p>Es gelten die gesetzlichen B2Bährleistungsrechte. '
    "Produktgarantien bleiben unverändert.</p></section>"
)
EXPECTED = DE.replace("B2Bäufen", "B2B-Käufen").replace(
    "B2Bährleistungsrechte", "B2B-Gewährleistungsrechte"
)


def test_pair_changes_only_the_reviewed_german_text_and_repeats_safely() -> None:
    planned = module.plan_pair(EN, DE)
    assert planned == (EN, EXPECTED)
    assert module.plan_pair(*planned) == planned


@pytest.mark.parametrize(
    "drifted",
    [
        DE.replace("B2Bäufen", "B2B-Käufen"),
        DE.replace("B2Bäufen", "anderen Käufen"),
        DE + DE,
    ],
)
def test_refuses_partial_missing_or_duplicate_source(drifted: str) -> None:
    with pytest.raises(ValueError):
        module.plan_pair(EN, drifted)
