"""#339 names the German card-permalink case (#413).

The link itself is decided in linker-i18n (Store API `permalink`) and checked
by GenieCardLinksTest plus the card test. This test only keeps the case on
the fixture list.
"""

import json
from pathlib import Path

_MANIFEST = json.loads(
    (Path(__file__).parent / "fixtures" / "339" / "manifest.json").read_text(
        encoding="utf-8"
    )
)


def test_339_names_the_card_permalink_case() -> None:
    case = next(
        item for item in _MANIFEST["cases"] if item["id"] == "s1-card-permalink-locale"
    )
    assert case["issue"] == 413
    assert case["locales"] == ["de", "en"]
    assert case["accounts"] == ["approved", "pending", "restricted", "guest"]
    assert case["products"] == [4107, 1957]
