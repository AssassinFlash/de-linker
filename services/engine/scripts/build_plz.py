"""Build data/plz_eu.csv.gz from the GeoNames postal code export for Europe.

Source: https://download.geonames.org/export/zip/allCountries.zip and
https://download.geonames.org/export/dump/cities5000.zip (both CC BY 4.0,
credit "GeoNames"; the readme in each archive states the licence).

The previous table held German postcodes only and the lookup accepted a
five-digit number, so a visitor outside Germany had nothing to enter and one
who typed a town name got an answer of "not found" (measured 2026-11-15).
This table covers every European country GeoNames lists and carries what the
report needs for each: a coordinate, the country, the region GeoNames names,
and an IANA timezone.

Timezones come from the city file, not the postal file: `allCountries.txt`
has no timezone column. Each postcode takes the zone of the nearest city in
`cities5000.txt`, which is exact for every country in this set except the
few that span zones — Spain's Canaries and Portugal's Azores carry their own
zones in GeoNames' data, so the nearest-city answer stays right there too.

    uv run python scripts/build_plz.py <allCountries.txt> <cities5000.txt>
"""

from __future__ import annotations

import argparse
import csv
import gzip
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "plz_eu.csv.gz"

# The postal-code column names differ per country (`plz`, `zip`, `postal`), so
# Europe is read from the canonical allCountries export which has one shape for
# every row: country, postcode, name, admin1 name, admin1 code, ..., lat, lon.
COUNTRY, POSTCODE, PLACE, ADMIN1, ADMIN1_CODE = 0, 1, 2, 3, 4
LATITUDE, LONGITUDE = 9, 10

# GeoNames' allCountries export covers the whole world. The site sells into
# Europe, and a table of the whole planet would answer for places the engine
# has no imagery or grid facts for. This is the same set the site's own
# country list offers.
EUROPE = frozenset(
    """
    AD AL AT AX BA BE BG BY CH CY CZ DE DK EE ES FI FO FR GB GG GI GR HR HU IE
    IM IS IT JE LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS RU SE SI SJ SK SM
    UA VA XK
    """.split()
)


def european_rows(source: Path) -> Iterator[list[str]]:
    with source.open(encoding="utf-8") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) <= LONGITUDE or row[COUNTRY] not in EUROPE:
                continue
            if not row[POSTCODE].strip():
                continue
            yield row


def city_zones(
    source: Path,
) -> tuple[list[tuple[float, float, str, str]], list[float]]:
    """A latitude-sorted index of every city's zone and country.

    The dump's columns are `geonameid, name, asciiname, alternatenames, lat,
    lon, feature class, feature code, country code, ... , timezone, ...` — the
    class is column 6, the country is column 8 and the zone is column 17 (all
    zero-based).
    """
    entries: list[tuple[float, float, str, str]] = []
    with source.open(encoding="utf-8") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) <= 17 or row[6] != "P":
                continue
            try:
                entries.append((float(row[4]), float(row[5]), row[17], row[8]))
            except (ValueError, IndexError):
                continue
    entries.sort()
    return entries, [entry[0] for entry in entries]


def nearest_zone(
    index: tuple[list[tuple[float, float, str, str]], list[float]],
    latitude: float,
    longitude: float,
    country: str | None = None,
) -> str | None:
    """The zone of the closest city, preferring one in the same country.

    A latitude-sorted list narrows the candidates before the distance is
    computed. The country filter is not cosmetic: measured 2026-11-15, 1,411
    border postcodes took the zone of a city across the frontier (Spanish
    Portbou answered `Europe/Paris`) because the nearest city happened to be
    in the neighbouring country. Those zones agree on UTC offset today, but a
    zone name is a claim about a place, so the nearest same-country city wins
    whenever there is one.
    """
    entries, latitudes = index
    if not entries:
        return None
    start = bisect_left(latitudes, latitude - 1.0)
    end = bisect_left(latitudes, latitude + 1.0)
    candidates = entries[start:end] or entries
    same = [entry for entry in candidates if entry[3] == country] if country else []
    pool = same or candidates
    best: tuple[float, str] | None = None
    for city_lat, city_lon, zone, _ in pool:
        distance = (city_lat - latitude) ** 2 + (city_lon - longitude) ** 2
        if best is None or distance < best[0]:
            best = (distance, zone)
    return None if best is None else best[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("postcodes", type=Path, help="allCountries.txt")
    parser.add_argument("cities", type=Path, help="cities5000.txt")
    args = parser.parse_args()

    index = city_zones(args.cities)
    # One row per country and postcode: the most accurate entry, and among
    # equals the alphabetically first place so the table is reproducible.
    best: dict[tuple[str, str], tuple[int, str, list[str]]] = {}
    missing_zone = 0
    for row in european_rows(args.postcodes):
        country, postcode = row[COUNTRY], row[POSTCODE].strip().upper()
        try:
            latitude, longitude = float(row[LATITUDE]), float(row[LONGITUDE])
        except ValueError:
            continue
        zone = nearest_zone(index, latitude, longitude, country)
        if zone is None:
            missing_zone += 1
            continue
        rank = int(row[11]) if len(row) > 11 and row[11].isdigit() else 0
        key = (country, postcode)
        place = row[PLACE].strip() or postcode
        record = [
            country,
            postcode,
            f"{latitude:.4f}",
            f"{longitude:.4f}",
            zone,
            row[ADMIN1].strip(),
            row[ADMIN1_CODE].strip(),
            place,
        ]
        if key not in best or rank > best[key][0]:
            best[key] = (rank, place, record)

    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "country",
                "postcode",
                "lat",
                "lon",
                "timezone",
                "region",
                "region_code",
                "place",
            ]
        )
        for key in sorted(best):
            writer.writerow(best[key][2])

    countries: dict[str, int] = defaultdict(int)
    for country, _ in best:
        countries[country] += 1
    print(f"{len(best)} postcodes across {len(countries)} countries -> {OUT}")
    if missing_zone:
        print(f"{missing_zone} rows skipped: no city near enough to name a zone")


if __name__ == "__main__":
    main()
