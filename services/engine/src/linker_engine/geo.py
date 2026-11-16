"""Postcode to a map position, a country, a region and an IANA timezone.

`data/plz_eu.csv.gz` holds one row per postcode across 49 European countries.
It is derived from the GeoNames postal code export for every country and the
GeoNames city list for timezones (CC BY 4.0, attribution "GeoNames",
https://www.geonames.org/); `scripts/build_plz.py` rebuilds it.

The table used to hold German postcodes only, and the lookup accepted a
five-digit number — so a visitor in the Netherlands had nothing to enter and
one in the United Kingdom could not be answered at all (measured 2026-11-15).
Postcode shapes differ per country: `10115` in Germany, `75001` in France,
`M1 1AE` in Britain, `3750-000` in Portugal, `59-700` in Poland. The table
therefore keys on the country and the postcode as the country writes it, and
the lookup normalises both.
"""

from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "plz_eu.csv.gz"
ATTRIBUTION = "Postcode positions and timezones: GeoNames (CC BY 4.0)"


@dataclass(frozen=True)
class Place:
    country: str  # ISO 3166-1 alpha-2
    postcode: str  # as the country writes it, upper-cased
    latitude: float
    longitude: float
    timezone: str  # IANA name
    region: str  # the country's own first-level division
    region_code: str  # GeoNames' short code for it, may be empty
    name: str

    @property
    def iso_region(self) -> str:
        """The region in the form this site's services key on.

        `data/lod2-sources.json` and `data/imagery.json` are keyed by ISO
        3166-2 (`DE-BY`), so a German place assembles `DE-` and its state code.
        GeoNames writes every other country's first-level division in its own
        scheme — Austria `09`, France `84`, Britain `SCT` — which is not ISO
        and has no service here; those keep GeoNames' code unchanged so a
        reader can see what it is rather than a code that looks like ISO.
        """
        if self.country == "DE" and self.region_code:
            return f"DE-{self.region_code}"
        return self.region_code or self.region


@cache
def _table(path: Path = DATA) -> dict[tuple[str, str], Place]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return {
            (row["country"], row["postcode"]): Place(
                country=row["country"],
                postcode=row["postcode"],
                latitude=float(row["lat"]),
                longitude=float(row["lon"]),
                timezone=row["timezone"],
                region=row["region"],
                region_code=row["region_code"],
                name=row["place"],
            )
            for row in csv.DictReader(handle)
        }


@cache
def _by_country() -> dict[str, dict[str, Place]]:
    grouped: dict[str, dict[str, Place]] = {}
    for (country, postcode), place in _table().items():
        grouped.setdefault(country, {})[postcode] = place
    return grouped


@cache
def _by_postcode() -> dict[str, tuple[Place, ...]]:
    """Every country that writes this postcode this way, for a country-less ask."""
    grouped: dict[str, list[Place]] = {}
    for place in _table().values():
        grouped.setdefault(place.postcode, []).append(place)
    return {postcode: tuple(places) for postcode, places in grouped.items()}


def normalise(postcode: str) -> str:
    """One spelling per postcode, so `M1 1AE` and `m11ae` are the same place."""
    return re.sub(r"\s+", " ", postcode.strip()).upper()


def _compact(postcode: str) -> str:
    return re.sub(r"\s+", "", postcode).upper()


# Countries whose residents write a country prefix in front of their own
# postcode. Measured 2026-11-16 against `data/plz_eu.csv.gz`: the table stores
# Luxembourg `L-1111`, Latvia `LV-1001`, Moldova `MD-2000` and Andorra `AD100`,
# and Lithuania's rows omit the `LT-` its residents type. The prefix is not
# part of the postcode, so `L-1111`, `LU-1111` and `1111` name one place.
_PREFIXES = {"LU": "L", "LV": "LV", "MD": "MD", "AD": "AD", "LT": "LT"}


def _compact_key(postcode: str, country: str) -> str:
    """The postcode without separators or its own country prefix.

    Czechia, Sweden and Slovakia write one space inside the code (`110 00`,
    `100 04`, `010 01`); a visitor writing `11000` names the same street. Only
    the separators and the country's own prefix are dropped — nothing else,
    because two different codes must stay different.
    """
    letters = "".join(ch for ch in postcode.upper() if ch.isalnum())
    prefix = _PREFIXES.get(country.upper(), "")
    if prefix and letters.startswith(prefix):
        rest = letters[len(prefix) :]
        if rest and any(ch.isdigit() for ch in rest):
            return rest
    return letters


@cache
def _by_compact() -> dict[str, dict[str, Place | None]]:
    """Country → compact key → the place it names, or None when ambiguous.

    Two recorded codes can compact to one key inside the same country; that
    key answers nothing rather than guessing which street was meant.
    """
    grouped: dict[str, dict[str, Place | None]] = {}
    for place in _table().values():
        bucket = grouped.setdefault(place.country, {})
        key = _compact_key(place.postcode, place.country)
        bucket[key] = place if key not in bucket else None
    return grouped


def prefix_lookup(postcode: str, country: str) -> Place | None:
    """The district a fuller postcode belongs to.

    GeoNames lists British, Irish and Dutch postcodes by district (`AB10`,
    `D01`, `9401`), not by the full address code a visitor knows (`AB10 1AA`).
    The postcode a form asks for is the full one, so an exact match alone would
    refuse every British visitor — measured 2026-11-15: `M1 1AE` and `m11ae`
    both answered "not found" while `M9` resolved.

    A district is the inward code's letters plus the digits before the space,
    so the space is the boundary that decides it: `M1 1AE` is district `M1`
    and `M11 1AA` is district `M11`. Compacting the input first loses that and
    makes both look like `M1...`.
    """
    cleaned = re.sub(r"\s+", " ", postcode.strip()).upper()
    table = _by_country().get(country.upper(), {})
    candidates: list[str] = []
    if " " in cleaned:
        # Everything before the space when the country writes one there.
        candidates.append(cleaned.split(" ", 1)[0])
    else:
        # A visitor who types `M11AE` wrote the same postcode without its
        # space. The British and Irish inward boundary is the first digit after
        # the letters, so `M11AE` → `M1` and `AB101AA` → `AB10`; trying the
        # letter run plus each following digit finds the district either way.
        letters = 0
        while letters < len(cleaned) and cleaned[letters].isalpha():
            letters += 1
        if letters:
            candidates += [
                cleaned[: letters + extra]
                for extra in range(1, len(cleaned) - letters + 1)
            ]
    compact = _compact(postcode)
    candidates += [compact[:length] for length in range(len(compact), 1, -1)]
    for candidate in candidates:
        hit = table.get(candidate)
        if hit is not None:
            return hit
    return None


def lookup(postcode: str, country: str | None = None) -> Place | None:
    """The place a postcode names, within the country when one is given.

    Without a country the postcode is matched across the table. Only an
    unambiguous answer is returned: a postcode several countries write the
    same way has no single place, and guessing one would put the project in
    the wrong country. Measured 2026-11-15: 4,754 of 10,815 German postcodes
    are also written elsewhere, so the form collects the country and passes
    it; `countries_of` is what tells the screen to ask.

    A fuller postcode than the table lists (Britain's `M1 1AE` against the
    listed `M1`) resolves to its district inside the named country.
    """
    wanted = normalise(postcode)
    if not wanted:
        return None
    if country is not None:
        exact = _by_country().get(country.upper(), {}).get(wanted)
        if exact is not None:
            return exact
        compact = (
            _by_compact().get(country.upper(), {}).get(_compact_key(postcode, country))
        )
        return compact if compact is not None else prefix_lookup(postcode, country)
    matches = _by_postcode().get(wanted, ())
    if not matches:
        # A postcode the table lists only as a district still has to resolve:
        # `M1 1AE` asks for [`M1`], and no country was given.
        found = {
            hit.country: hit
            for hit in (prefix_lookup(postcode, candidate) for candidate in countries())
            if hit is not None
        }
        if len(found) == 1:
            return found.popitem()[1]
        # The same fallback for a code written with other separators: `11000`
        # for Czechia's `110 00`, `1111` for Luxembourg's `L-1111`.
        keyed = {
            place.country: place
            for candidate in countries()
            if (
                place := _by_compact()
                .get(candidate, {})
                .get(_compact_key(postcode, candidate))
            )
            is not None
        }
        return keyed.popitem()[1] if len(keyed) == 1 else None
    countries_found = {place.country for place in matches}
    return matches[0] if len(countries_found) == 1 else None


def lookup_in(postcode: str, country: str) -> Place | None:
    """The place inside one country, which is what a form with a country uses.

    It resolves exactly like `lookup` does for a named country, so a code the
    visitor wrote with other separators or with its own country prefix
    (`11000` for `110 00`, `L-1111` for `1111`) still finds the same place.
    """
    return lookup(postcode, country)


def countries_of(postcode: str) -> frozenset[str]:
    """Every country that writes this postcode this way.

    The lookup needs it to tell "nowhere" from "several places": only the
    second is worth asking the visitor a follow-up question for. A code written
    with other separators counts too — `11000` is Czechia's `110 00` as well as
    Serbia's `11000`, and answering "nowhere" would be wrong for both.
    """
    wanted = normalise(postcode)
    found = {place.country for place in _by_postcode().get(wanted, ())}
    for country in _by_compact():
        if _by_compact()[country].get(_compact_key(postcode, country)) is not None:
            found.add(country)
    return frozenset(found)


def countries() -> frozenset[str]:
    return frozenset(_by_country())
