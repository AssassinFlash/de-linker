from __future__ import annotations

from prod_smoke import PROBES, is_production, main


def test_production_host_check() -> None:
    assert is_production("https://de-linker.com")
    assert is_production("https://DE-LINKER.com.")
    assert is_production("https://www.de-linker.com/path")
    assert not is_production("http://127.0.0.1:9187")


def test_smoke_is_at_most_five_turns() -> None:
    assert 1 <= len(PROBES) <= 5


def test_production_is_refused_without_confirmation() -> None:
    assert main(["--site", "https://de-linker.com"]) == 2
