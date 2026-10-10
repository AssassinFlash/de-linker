"""Official aerial imagery (DOP) of each federal state, for the roof step's map.

`data/imagery.json` names each state's open WMS, its layer and the credit and
licence the state asks for; the map requests 256 px tiles in EPSG:3857 and
shows the credit.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from .models import Imagery

DATA = Path(__file__).resolve().parents[2] / "data" / "imagery.json"


@cache
def _states() -> dict[str, Any]:
    states: dict[str, Any] = json.loads(DATA.read_text())["states"]
    return states


def for_state(state: str) -> Imagery | None:
    entry = _states().get(state)
    if entry is None:
        return None
    tile = (
        f"{entry['wms']}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={entry['layer']}"
        "&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png"
    )
    return Imagery(
        tiles=[tile],
        credit=entry["credit"],
        licence=entry["licence"],
        licence_url=entry["licence_url"],
    )
