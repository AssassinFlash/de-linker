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
        """The region as ISO 3166-2, which is what the imagery services key on.

        GeoNames writes Germany's states as `BY`, and `data/lod2-sources.json`
        keys the official outline services as `DE-BY`. The postal table used to
        store the assembled code; keeping the two apart lets the same row serve
        the report (which prints `Bavaria`) and the roof step (which needs
        `DE-BY`).
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

    Without a country the postcode is matched across the table. A postcode
    several countries share resolves to the site's home market, Germany, and
    only to Germany — measured 2026-11-15: 4,754 of 10,815 German postcodes are
    also written by another country, so refusing the ambiguous ones would have
    refused 44% of the home market's own customers. A visitor elsewhere names
    their country, which the form already collects.

    A fuller postcode than the table lists (Britain's `M1 1AE` against the
    listed `M1`) resolves to its district inside the named country.
    """
    wanted = normalise(postcode)
    if not wanted:
        return None
    if country is not None:
        exact = _by_country().get(country.upper(), {}).get(wanted)
        return exact if exact is not None else prefix_lookup(postcode, country)
    matches = _by_postcode().get(wanted, ())
    if not matches:
        # A postcode the table lists only as a district still has to resolve:
        # `M1 1AE` asks for [`M1`], and no country was given.
        for candidate in ("GB", "IE", "NL"):
            hit = prefix_lookup(postcode, candidate)
            if hit is not None:
                return hit
        return None
    home = [place for place in matches if place.country == "DE"]
    return home[0] if home else (matches[0] if len(matches) == 1 else None)


def lookup_in(postcode: str, country: str) -> Place | None:
    """The place inside one country, which is what a form with a country uses."""
    return _by_country().get(country.upper(), {}).get(normalise(postcode))


def countries_of(postcode: str) -> frozenset[str]:
    """Every country that writes this postcode this way.

    The lookup needs it to tell "nowhere" from "several places": only the
    second is worth asking the visitor a follow-up question for.
    """
    return frozenset(
        place.country for place in _by_postcode().get(normalise(postcode), ())
    )


def countries() -> frozenset[str]:
    return frozenset(_by_country())
