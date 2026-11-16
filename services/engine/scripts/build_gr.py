"""Merge the Greek postcode set into the European table.

GeoNames' postal-code export has no row for Greece (checked 2026-11-15: its
country list contains `GR` in no archive), so Greece had no postcode at all
while every other European country the site sells into did. The gap is not
accepted: a Greek visitor is a customer, and the site's own country list offers
Greece.

Source: https://github.com/MentatInnovations/grpostcodes (Apache-2.0), whose
data file maps a postcode to a territory and to the centre of that territory.
It holds 1,250 codes rather than the country's full ~12,000, but every
postcode prefix from 10 to 90 has at least one row, so a visitor is always
placed in the right territory. That is the fact the report needs; the gap is
recorded here rather than hidden.

    uv run python scripts/build_gr.py <postcode_lat_long_output_file.csv>
"""

from __future__ import annotations

import argparse
import csv
import gzip
from collections.abc import Iterator
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "plz_eu.csv.gz"

# Greece has one timezone; the islands west of the mainland do not change it.
# Athens' IANA name is the one the rest of the engine already accepts.
GREECE_TZ = "Europe/Athens"
WRITE_HEADER = [
    "country",
    "postcode",
    "lat",
    "lon",
    "timezone",
    "region",
    "region_code",
    "place",
]


def greek_rows(source: Path) -> Iterator[list[str]]:
    with source.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            postcode = (row.get("tk") or "").strip()
            latitude, longitude = (
                (row.get("lat") or "").strip(),
                (row.get("lon") or "").strip(),
            )
            if not (postcode.isdigit() and len(postcode) == 5):
                continue
            try:
                float(latitude), float(longitude)
            except ValueError:
                continue
            yield [
                "GR",
                postcode,
                f"{float(latitude):.4f}",
                f"{float(longitude):.4f}",
                GREECE_TZ,
                # The dataset names the territory, not an administrative
                # region; the territory is what a Greek address prints.
                (row.get("territory") or "").strip(),
                "",
                (row.get("territory") or "").strip(),
            ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("greece", type=Path, help="postcode_lat_long_output_file.csv")
    args = parser.parse_args()

    existing: list[list[str]] = []
    with gzip.open(OUT, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != WRITE_HEADER:
            raise SystemExit(f"unexpected table header: {header}")
        existing = [row for row in reader if row[0] != "GR"]

    merged = existing + list(greek_rows(args.greece))
    merged.sort(key=lambda row: (row[0], row[1]))

    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(WRITE_HEADER)
        writer.writerows(merged)

    greece = sum(1 for row in merged if row[0] == "GR")
    countries = len({row[0] for row in merged})
    print(
        f"{len(merged)} postcodes across {countries} countries ({greece} Greek) -> {OUT}"
    )


if __name__ == "__main__":
    main()
