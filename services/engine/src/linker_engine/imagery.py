"""Official aerial imagery of each European region or country, for the roof map.

`data/imagery.json` names each federal state's or country's open orthophoto WMS
or tile template alongside the European Union Copernicus VHR mosaic viewing
service for EEA and United Kingdom territories that publish no separate open
national WMS. When ``LINKER_GOOGLE_MAP_TILES_KEY`` is configured, Google 2D
Satellite imagery replaces Italy's blank-tile PCN relay and serves European
countries without a verified open orthophoto service; if the key is unset or
session creation fails, each lookup falls back cleanly to the open service or
``None``.
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import cache
from pathlib import Path
from typing import Any

from . import geo
from .models import Imagery

DATA = Path(__file__).resolve().parents[2] / "data" / "imagery.json"

GOOGLE_CREATE_SESSION_URL = "https://tile.googleapis.com/v1/createSession"
GOOGLE_TILE_URL = "https://tile.googleapis.com/v1/2dtiles"
GOOGLE_REFERER = "https://de-linker.com/"
GOOGLE_TIMEOUT_SECONDS = 10
GOOGLE_DEFAULT_TTL_SECONDS = 86400.0
GOOGLE_REFRESH_MARGIN_SECONDS = 3600.0

_GOOGLE_LOCK = threading.Lock()
_GOOGLE_SESSIONS: dict[str, tuple[str, float]] = {}


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


def _create_google_session(api_key: str) -> tuple[str, float]:
    url = f"{GOOGLE_CREATE_SESSION_URL}?key={urllib.parse.quote(api_key, safe='')}"
    body = json.dumps(
        {"mapType": "satellite", "language": "en-US", "region": "DE"}
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Referer": GOOGLE_REFERER,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=GOOGLE_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Google createSession response must be a JSON object")
    session = payload.get("session")
    if not isinstance(session, str) or not session:
        raise ValueError("Google createSession response missing session")
    raw_expiry = payload.get("expiry")
    if raw_expiry is None:
        expiry = time.time() + GOOGLE_DEFAULT_TTL_SECONDS
    elif isinstance(raw_expiry, bool) or not isinstance(raw_expiry, int | float | str):
        raise ValueError("Google createSession expiry has invalid type")
    else:
        expiry = float(raw_expiry)
        if not math.isfinite(expiry):
            raise ValueError("Google createSession expiry is not finite")
    return session, expiry


def _google_session(api_key: str) -> str | None:
    with _GOOGLE_LOCK:
        cached = _GOOGLE_SESSIONS.get(api_key)
        if (
            cached is not None
            and time.time() < cached[1] - GOOGLE_REFRESH_MARGIN_SECONDS
        ):
            return cached[0]
        try:
            session, expiry = _create_google_session(api_key)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            _GOOGLE_SESSIONS.pop(api_key, None)
            return None
        _GOOGLE_SESSIONS[api_key] = (session, expiry)
        return session


def _google_satellite() -> Imagery | None:
    api_key = os.environ.get("LINKER_GOOGLE_MAP_TILES_KEY", "").strip()
    if not api_key:
        return None
    session = _google_session(api_key)
    if session is None:
        return None
    encoded_session = urllib.parse.quote(session, safe="")
    encoded_key = urllib.parse.quote(api_key, safe="")
    return Imagery(
        tiles=[
            f"{GOOGLE_TILE_URL}/{{z}}/{{x}}/{{y}}"
            f"?session={encoded_session}&key={encoded_key}"
        ],
        credit="Map data © Google",
        licence="Google Maps Platform Terms of Service",
        licence_url="https://cloud.google.com/maps-platform/terms",
    )


def for_state(state: str) -> Imagery | None:
    catalogue = _catalogue()
    states: dict[str, Any] = catalogue["states"]
    if state == "IT":
        google = _google_satellite()
        if google is not None:
            return google
        entry = states.get("IT")
        return _build(entry) if entry is not None else None
    entry = states.get(state)
    if entry is not None:
        return _build(entry)
    copernicus: dict[str, Any] | None = catalogue.get("copernicus_vhr")
    copernicus_countries = (
        set(copernicus.get("countries", ())) if copernicus is not None else set()
    )
    if state in geo.countries() or state in copernicus_countries:
        google = _google_satellite()
        if google is not None:
            return google
    if copernicus is not None and state in copernicus_countries:
        return _build(copernicus)
    return None


def for_country(country: str) -> Imagery | None:
    """The national or Copernicus VHR mosaic of a country, where verified."""
    return for_state(country)


def for_place(country: str, iso_region: str | None = None) -> Imagery | None:
    """The aerial imagery layer for a resolved place without region-code collisions.

    Only Germany publishes state-level orthophotos keyed by `DE-*`; outside
    Germany, GeoNames region codes such as `MD` (Madrid), `FR` (Fribourg) or
    `BE` (Bern) collide with ISO country codes and must never enter country
    imagery fallback.
    """
    if country == "DE" and iso_region:
        state_entry = _catalogue()["states"].get(iso_region)
        if state_entry is not None:
            return _build(state_entry)
    return for_country(country)
