"""Build data/plz_de.csv.gz from the GeoNames postal code export for Germany.

Source: https://download.geonames.org/export/zip/DE.zip (CC BY 4.0, credit
"GeoNames"; the readme in the archive states the licence). GeoNames lists a
postcode once per place; the table keeps one row per postcode, the one with
the best stated accuracy, and the federal state as ISO 3166-2.

    uv run python scripts/build_plz.py <path to DE.txt>
"""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

# GeoNames writes the state either as its ISO letters or as its own numeric code.
STATES = {
    "BW": "DE-BW",
    "01": "DE-BW",
    "BY": "DE-BY",
    "02": "DE-BY",
    "HB": "DE-HB",
    "03": "DE-HB",
    "HH": "DE-HH",
    "04": "DE-HH",
    "HE": "DE-HE",
    "05": "DE-HE",
    "NI": "DE-NI",
    "06": "DE-NI",
    "NW": "DE-NW",
    "07": "DE-NW",
    "RP": "DE-RP",
    "08": "DE-RP",
    "SL": "DE-SL",
    "09": "DE-SL",
    "SH": "DE-SH",
    "10": "DE-SH",
    "BB": "DE-BB",
    "11": "DE-BB",
    "MV": "DE-MV",
    "12": "DE-MV",
    "SN": "DE-SN",
    "13": "DE-SN",
    "ST": "DE-ST",
    "14": "DE-ST",
    "TH": "DE-TH",
    "15": "DE-TH",
    "BE": "DE-BE",
    "16": "DE-BE",
}
OUT = Path(__file__).resolve().parents[1] / "data" / "plz_de.csv.gz"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="DE.txt from the GeoNames archive")
    args = parser.parse_args()
    best: dict[str, tuple[int, list[str]]] = {}
    with args.source.open(encoding="utf-8") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            plz, place, code, lat, lon, accuracy = (
                row[1],
                row[2],
                row[4],
                row[9],
                row[10],
                row[11],
            )
            if not code:
                continue  # one row without any state in the 2026-10-09 export
            if code not in STATES:
                raise SystemExit(f"unknown state code {code!r} for {plz}")
            rank = int(accuracy) if accuracy.isdigit() else 0
            if plz not in best or rank > best[plz][0]:
                best[plz] = (rank, [plz, lat, lon, STATES[code], place])
    with gzip.open(OUT, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["plz", "lat", "lon", "state", "place"])
        for plz in sorted(best):
            writer.writerow(best[plz][1])
    print(f"{len(best)} postcodes -> {OUT}")


if __name__ == "__main__":
    main()
