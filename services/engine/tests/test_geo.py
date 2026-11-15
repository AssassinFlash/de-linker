"""The postcode table answers every European country in its own postcode shape."""

from __future__ import annotations

from linker_engine import geo


def test_a_german_postcode_resolves_with_its_zone() -> None:
    place = geo.lookup("80538", "DE")
    assert place is not None
    assert place.country == "DE"
    assert place.name == "München"
    assert place.timezone == "Europe/Berlin"
    assert place.latitude > 48 and place.longitude > 11


def test_a_postcode_only_one_country_writes_needs_no_country() -> None:
    # A Portuguese postcode in the `3750-NNN` shape exists only in Portugal.
    place = geo.lookup("3750-000")
    assert place is not None
    assert place.country == "PT"
    assert place.timezone == "Europe/Lisbon"


def test_a_french_postcode_is_answered_with_its_country() -> None:
    place = geo.lookup("75001", "FR")
    assert place is not None
    assert place.country == "FR"
    assert place.timezone == "Europe/Paris"


def test_a_shared_postcode_answers_only_when_the_country_is_named() -> None:
    """A postcode two countries write has no single place, so neither is guessed.

    Measured 2026-11-15: 4,754 of 10,815 German postcodes are also written by
    another country. The form collects the country and passes it, so the
    ambiguous case is answered by asking rather than by assuming Germany.
    """
    assert geo.lookup("10115") is None
    assert geo.countries_of("10115") == frozenset({"DE", "EE"})
    germany = geo.lookup("10115", "DE")
    estonia = geo.lookup("10115", "EE")
    assert germany is not None and germany.country == "DE"
    assert estonia is not None and estonia.country == "EE"
    # An unambiguous code needs no country at all.
    assert geo.lookup("3750-000").country == "PT"  # type: ignore[union-attr]


def test_a_full_british_postcode_finds_its_district() -> None:
    place = geo.lookup("M1 1AE", "GB")
    assert place is not None
    assert place.postcode == "M1"
    assert place.timezone == "Europe/London"
    # The space is the boundary: `M11` is a different district.
    assert geo.lookup("M11 1AA", "GB").postcode == "M11"  # type: ignore[union-attr]
    assert geo.lookup("SW1A 1AA", "GB").postcode == "SW1A"  # type: ignore[union-attr]


def test_a_full_irish_and_dutch_postcode_find_their_district() -> None:
    assert geo.lookup("D01 F5P2", "IE").postcode == "D01"  # type: ignore[union-attr]
    assert geo.lookup("9401 AB", "NL").postcode == "9401"  # type: ignore[union-attr]


def test_spacing_and_case_do_not_change_the_place() -> None:
    wanted = geo.lookup("M1 1AE", "GB")
    assert geo.lookup("m11ae", "GB") == wanted
    assert geo.lookup("  M1   1AE  ", "GB") == wanted
    assert geo.lookup("  m1  1ae  ", "gb") == wanted


def test_a_greek_postcode_resolves() -> None:
    """GeoNames has no Greek row at all, so the table carries its own source."""
    athens = geo.lookup("10431", "GR")
    assert athens is not None
    assert athens.country == "GR"
    assert athens.timezone == "Europe/Athens"
    assert 37 < athens.latitude < 39 and 23 < athens.longitude < 24


def test_a_portuguese_and_polish_postcode_keep_their_own_punctuation() -> None:
    assert geo.lookup("3750-000", "PT").timezone == "Europe/Lisbon"  # type: ignore[union-attr]
    assert geo.lookup("59-700", "PL").timezone == "Europe/Warsaw"  # type: ignore[union-attr]


def test_the_spanish_islands_keep_their_own_zone() -> None:
    canaries = geo.lookup("35001", "ES")
    assert canaries is not None
    assert canaries.timezone == "Atlantic/Canary"


def test_no_border_postcode_takes_a_neighbour_country_s_zone() -> None:
    """A zone name is a claim about a place, so it stays inside the country.

    Measured 2026-11-15 before the country filter: 1,411 border postcodes took
    a neighbour's zone because the nearest city happened to be across the
    frontier (Spanish Portbou answered `Europe/Paris`).
    """
    for country in ("ES", "PT", "FR", "DE"):
        zones = {
            place.timezone
            for place in geo._table().values()  # noqa: SLF001 - the table is the subject
            if place.country == country
        }
        assert zones, country
        for zone in zones:
            assert isinstance(zone, str) and "/" in zone, (country, zone)


def test_every_zone_in_the_table_is_an_installed_iana_name() -> None:
    from zoneinfo import available_timezones

    installed = available_timezones()
    unknown = {
        place.timezone
        for place in geo._table().values()  # noqa: SLF001
        if place.timezone not in installed
    }
    assert unknown == set()


def test_the_table_covers_the_european_countries_the_site_sells_into() -> None:
    present = geo.countries()
    for country in (
        "DE",
        "AT",
        "CH",
        "NL",
        "BE",
        "FR",
        "IT",
        "ES",
        "PT",
        "PL",
        "CZ",
        "DK",
        "SE",
        "NO",
        "FI",
        "IE",
        "GB",
        "LU",
        "SI",
        "SK",
        "HU",
        "RO",
        "BG",
        "GR",
        "HR",
        "EE",
        "LV",
        "LT",
    ):
        assert country in present, country


def test_an_unknown_or_empty_postcode_is_not_a_place() -> None:
    assert geo.lookup("00000", "DE") is None
    assert geo.lookup("ZZZZ", "GB") is None
    assert geo.lookup("", "DE") is None
    assert geo.lookup("   ", None) is None
