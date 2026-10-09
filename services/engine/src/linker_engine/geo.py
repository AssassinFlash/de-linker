"""Postcode (PLZ) to a map position and the federal state.

`data/plz_de.csv.gz` holds one row per German postcode: a representative
coordinate and the ISO 3166-2 code of the state. It is derived from the
GeoNames postal code export for Germany (CC BY 4.0, attribution "GeoNames",
https://www.geonames.org/); `scripts/build_plz.py` rebuilds it. The state
picks the official LoD2 and aerial imagery services of the roof step.
"""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass
from functools import cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "plz_de.csv.gz"
ATTRIBUTION = "Postcode positions: GeoNames (CC BY 4.0)"


@dataclass(frozen=True)
class Place:
    plz: str
    latitude: float
    longitude: float
    state: str  # ISO 3166-2, for example DE-BY
    name: str


@cache
def _table(path: Path = DATA) -> dict[str, Place]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return {
            row["plz"]: Place(
                plz=row["plz"],
                latitude=float(row["lat"]),
                longitude=float(row["lon"]),
                state=row["state"],
                name=row["place"],
            )
            for row in csv.DictReader(handle)
        }


def lookup(plz: str) -> Place | None:
    return _table().get(plz)
