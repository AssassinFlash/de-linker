"""Viewing and editable aerial imagery for European regions and countries.

When ``LINKER_GOOGLE_MAP_TILES_KEY`` is configured, Google 2D Satellite imagery
is the primary layer across all verified European countries and German states.
When the key is unset or Google session creation fails, each lookup falls back
cleanly to the state's or country's open orthophoto service in
``data/imagery.json`` or the EU Copernicus VHR mosaic, or ``None``.
Roof editing uses only catalogue licences that permit derived geometry.
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

# These catalogue licences explicitly allow altered/derived data. The provider
# credit and licence link remain attached to every returned editing layer.
# CC BY/CC0, DL-DE and Licence Ouverte terms are at these canonical URLs.
# Representative provider declarations:
# https://geodatenonline.bayern.de/geodatenonline/seiten/wms_dop20cm
# https://www.pdok.nl/-/luchtfoto-2025-nu-beschikbaar-bij-pdok
EDITING_LICENCE_URLS = frozenset(
    {
        "https://creativecommons.org/licenses/by/4.0/",
        "https://creativecommons.org/publicdomain/zero/1.0/",
        "https://www.govdata.de/dl-de/by-2-0",
        "https://www.govdata.de/dl-de/zero-2-0",
        "https://www.data.gouv.fr/pages/legal/licences/etalab-2-0",
        "https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices",
    }
)


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


def for_viewing(country: str) -> Imagery | None:
    """The official Copernicus viewing mosaic without a Google tile session."""
    entry = _catalogue().get("copernicus_vhr")
    if entry is not None and country in entry["countries"]:
        return _build(entry)
    return None


def for_state(state: str) -> Imagery | None:
    states: dict[str, Any] = _catalogue()["states"]
    viewing = for_viewing(state)
    if state not in states and state not in geo.countries() and viewing is None:
        return None
    google = _google_satellite()
    if google is not None:
        return google
    entry = states.get(state)
    return _build(entry) if entry is not None else viewing


def for_country(country: str) -> Imagery | None:
    """The Google Satellite or open orthophoto mosaic of a European country."""
    return for_state(country)


def for_place(country: str, iso_region: str | None = None) -> Imagery | None:
    """The aerial imagery layer for a resolved place without region-code collisions.

    Only Germany publishes state-level orthophotos keyed by `DE-*`; outside
    Germany, GeoNames region codes such as `MD` (Madrid), `FR` (Fribourg) or
    `BE` (Bern) collide with ISO country codes and must never enter country
    imagery fallback.
    """
    if country == "DE" and iso_region and iso_region in _catalogue()["states"]:
        return for_state(iso_region)
    return for_country(country)


def for_editing(country: str, iso_region: str | None = None) -> Imagery | None:
    """Return a catalogue layer whose licence permits deriving roof geometry.

    Google Map Tiles disallow derived content and Copernicus VHR is a viewing
    service. Neither is an editing fallback, even when a Google key is set.
    https://developers.google.com/maps/documentation/tile/policies
    """
    key = iso_region if country == "DE" and iso_region else country
    entry = _catalogue()["states"].get(key)
    if entry is None or entry["licence_url"] not in EDITING_LICENCE_URLS:
        return None
    return _build(entry)
