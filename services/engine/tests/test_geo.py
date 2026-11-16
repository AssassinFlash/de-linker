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

    Measured 2026-11-16: Poland writes `10-115` (Olsztyn), so the same digits
    without Poland's hyphen name a third country too. The ambiguity grows; the
    answer still asks instead of picking one.
    """
    assert geo.lookup("10115") is None
    assert {"DE", "EE"} <= geo.countries_of("10115")
    germany = geo.lookup("10115", "DE")
    estonia = geo.lookup("10115", "EE")
    poland = geo.lookup("10-115", "PL")
    assert germany is not None and germany.country == "DE"
    assert estonia is not None and estonia.country == "EE"
    assert poland is not None and poland.country == "PL"
    # An unambiguous code needs no country at all.
    assert geo.lookup("3750-000").country == "PT"  # type: ignore[union-attr]


def test_a_code_written_without_its_space_finds_the_same_place() -> None:
    """Czechia, Sweden and Slovakia write one space inside the postcode.

    Measured 2026-11-16 against the table: a resident typing `11000` or
    `11120` was answered "nowhere" while `110 00` resolved, because the table
    keeps the country's own spelling and the lookup only matched it exactly.
    """
    prague = geo.lookup("110 00", "CZ")
    assert prague is not None and prague.name == "Vinohrady"
    assert geo.lookup("11000", "CZ") == prague
    stockholm = geo.lookup("111 20", "SE")
    assert stockholm is not None and stockholm.timezone == "Europe/Stockholm"
    assert geo.lookup("11120", "SE") == stockholm
    zilina = geo.lookup("010 01", "SK")
    assert zilina is not None and zilina.timezone == "Europe/Bratislava"
    assert geo.lookup("01001", "SK") == zilina


def test_a_code_written_with_its_own_country_prefix_finds_the_same_place() -> None:
    """Luxembourg, Latvia, Moldova and Andorra publish their prefix in the code.

    Measured 2026-11-16: the table stores `L-1111`, `LV-1001`, `MD-2000` and
    `AD100`. Residents write the prefix, so both spellings must answer — and
    the reverse for Lithuania, whose rows carry no prefix but whose residents
    type `LT-`.
    """
    lux = geo.lookup("L-1111", "LU")
    assert lux is not None and lux.timezone == "Europe/Luxembourg"
    assert geo.lookup("1111", "LU") == lux
    riga = geo.lookup("LV-1001", "LV")
    assert riga is not None and riga.name == "Riga"
    assert geo.lookup("1001", "LV") == riga
    chisinau = geo.lookup("MD-2000", "MD")
    assert chisinau is not None and chisinau.name == "Chisinau"
    assert geo.lookup("2000", "MD") == chisinau
    assert geo.lookup("AD100", "AD") == geo.lookup("100", "AD")
    vilnius = geo.lookup("01001", "LT")
    assert vilnius is not None and vilnius.name == "Vilnius"
    assert geo.lookup("LT-01001", "LT") == vilnius
    # The country an unambiguous code names is answered without being asked.
    assert geo.lookup("L-1111").country == "LU"  # type: ignore[union-attr]


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


def test_location_labels_with_space_postcodes_resolve_again() -> None:
    for query, country, expected_code in (
        ("110 00 Vinohrady", "CZ", "110 00"),
        ("111 20 Stockholm", "SE", "111 20"),
        ("010 01 Žilina", "SK", "010 01"),
        ("M1 1AE Manchester", "GB", "M1"),
        ("59-700 Golnice", "PL", "59-700"),
    ):
        found = geo.lookup(query, country)
        assert found is not None, (query, country)
        assert found.country == country
        assert found.postcode == expected_code


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
