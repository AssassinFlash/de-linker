"""Official aerial imagery of each European region or country, for the roof map.

`data/imagery.json` names each federal state's or country's open orthophoto WMS
or tile template alongside the European Union Copernicus VHR mosaic viewing
service for EEA and United Kingdom territories that publish no separate open
national WMS. Countries where neither service returns imagery answer ``None`` so
the map displays the building footprint and hand-drawn fallback honestly.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from .models import Imagery

DATA = Path(__file__).resolve().parents[2] / "data" / "imagery.json"


@cache
def _catalogue() -> dict[str, Any]:
    catalogue: dict[str, Any] = json.loads(DATA.read_text(encoding="utf-8"))
    return catalogue


def _build(entry: dict[str, Any]) -> Imagery:
    if "template" in entry:
        tile = str(entry["template"])
    else:
        tile = (
            f"{entry['wms']}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={entry['layer']}"
            "&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png"
        )
    return Imagery(
        tiles=[tile],
        credit=str(entry["credit"]),
        licence=str(entry["licence"]),
        licence_url=str(entry["licence_url"]),
    )


def for_state(state: str) -> Imagery | None:
    catalogue = _catalogue()
    states: dict[str, Any] = catalogue["states"]
    entry = states.get(state)
    if entry is not None:
        return _build(entry)
    copernicus: dict[str, Any] | None = catalogue.get("copernicus_vhr")
    if copernicus is not None and state in copernicus.get("countries", ()):
        return _build(copernicus)
    return None


def for_country(country: str) -> Imagery | None:
    """The national or Copernicus VHR mosaic of a country, where verified."""
    return for_state(country)
