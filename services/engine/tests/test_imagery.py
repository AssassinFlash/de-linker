"""Google 2D Satellite fallback and override rules for European imagery."""

from __future__ import annotations

import io
import json
import time
import urllib.error
import urllib.request
from typing import Any

import pytest

from linker_engine import imagery


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        return None


@pytest.fixture(autouse=True)
def _clean_google_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINKER_GOOGLE_MAP_TILES_KEY", raising=False)
    imagery._GOOGLE_SESSIONS.clear()


def test_italy_and_non_open_european_countries_use_google_when_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "test-key")
    seen: list[dict[str, Any]] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: int = 0
    ) -> _FakeResponse:
        assert isinstance(request.data, bytes)
        seen.append(
            {
                "url": request.full_url,
                "method": request.get_method(),
                "headers": {k.lower(): v for k, v in request.header_items()},
                "body": json.loads(request.data.decode("utf-8")),
                "timeout": timeout,
            }
        )
        expiry = str(int(time.time()) + 86400)
        return _FakeResponse(json.dumps({"session": "sess-123", "expiry": expiry}))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    italy = imagery.for_country("IT")
    assert italy is not None
    assert (
        italy.tiles[0]
        == "https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}?session=sess-123&key=test-key"
    )
    assert italy.credit == "Map data © Google"
    assert italy.licence == "Google Maps Platform Terms of Service"
    assert italy.licence_url == "https://cloud.google.com/maps-platform/terms"

    gb = imagery.for_country("GB")
    assert gb is not None
    assert "tile.googleapis.com/v1/2dtiles" in gb.tiles[0]

    ukraine = imagery.for_country("UA")
    assert ukraine is not None
    assert "tile.googleapis.com/v1/2dtiles" in ukraine.tiles[0]

    assert len(seen) == 1
    assert seen[0]["url"] == "https://tile.googleapis.com/v1/createSession?key=test-key"
    assert seen[0]["method"] == "POST"
    assert seen[0]["headers"]["content-type"] == "application/json"
    assert seen[0]["headers"]["referer"] == "https://de-linker.com/"
    assert seen[0]["body"] == {
        "mapType": "satellite",
        "language": "en-US",
        "region": "DE",
    }
    assert seen[0]["timeout"] == 10


def test_verified_open_orthophoto_states_stay_primary_even_with_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "test-key")

    def fail_if_called(*_: object, **__: object) -> Any:
        raise AssertionError("Google createSession must not be called for open WMS")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)

    for state, host in (
        ("DE-BY", "geoservices.bayern.de"),
        ("NL", "service.pdok.nl"),
        ("FR", "data.geopf.fr"),
        ("CH", "wms.geo.admin.ch"),
        ("AT", "mapsneu.wien.gv.at"),
    ):
        service = imagery.for_state(state)
        assert service is not None
        assert host in service.tiles[0]


def test_for_place_avoids_non_german_region_code_collisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "test-key")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_kw: _FakeResponse(json.dumps({"session": "sess-1"})),
    )

    es_madrid = imagery.for_place("ES", "MD")
    assert es_madrid is not None and "ign.es" in es_madrid.tiles[0]

    ch_bern = imagery.for_place("CH", "BE")
    ch_fribourg = imagery.for_place("CH", "FR")
    assert ch_bern is not None and "wms.geo.admin.ch" in ch_bern.tiles[0]
    assert ch_fribourg is not None and "wms.geo.admin.ch" in ch_fribourg.tiles[0]

    de_bayern = imagery.for_place("DE", "DE-BY")
    assert de_bayern is not None and "geoservices.bayern.de" in de_bayern.tiles[0]


def test_session_cache_refreshes_near_expiry_and_keys_by_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: now)

    calls: list[str] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: int = 0
    ) -> _FakeResponse:
        calls.append(request.full_url)
        index = len(calls)
        return _FakeResponse(
            json.dumps({"session": f"sess-{index}", "expiry": int(now + 7200)})
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "key-a")
    first = imagery.for_country("GB")
    assert first is not None and "session=sess-1&key=key-a" in first.tiles[0]

    now += 1000.0
    second = imagery.for_country("IT")
    assert second is not None and "session=sess-1&key=key-a" in second.tiles[0]
    assert len(calls) == 1

    # Within 3600s of expiry -> refreshes session.
    now += 3000.0
    third = imagery.for_country("GB")
    assert third is not None and "session=sess-2&key=key-a" in third.tiles[0]
    assert len(calls) == 2

    # Different API key gets its own session.
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "key-b")
    fourth = imagery.for_country("GB")
    assert fourth is not None and "session=sess-3&key=key-b" in fourth.tiles[0]
    assert len(calls) == 3


def test_session_defaults_expiry_when_absent_and_never_caches_missing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # First call without key -> Copernicus fallback for GB.
    without_key = imagery.for_country("GB")
    assert without_key is not None
    assert "image.discomap.eea.europa.eu" in without_key.tiles[0]

    # Setting key afterwards in same process must work (no permanent None cache).
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "late-key")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_kw: _FakeResponse(json.dumps({"session": "sess-late"})),
    )
    with_key = imagery.for_country("GB")
    assert with_key is not None
    assert "session=sess-late&key=late-key" in with_key.tiles[0]


@pytest.mark.parametrize(
    "exc_factory",
    [
        lambda: urllib.error.URLError("dns error"),
        lambda: TimeoutError("timed out"),
        lambda: urllib.error.HTTPError(
            "https://tile.googleapis.com/v1/createSession",
            403,
            "Forbidden",
            {},  # type: ignore[arg-type]
            io.BytesIO(b"forbidden"),
        ),
        lambda: ValueError("bad json"),
    ],
)
def test_create_session_failures_fall_back_cleanly(
    monkeypatch: pytest.MonkeyPatch, exc_factory: Any
) -> None:
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "bad-key")

    def failing_urlopen(*_a: object, **_kw: object) -> Any:
        raise exc_factory()

    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)

    italy = imagery.for_country("IT")
    assert italy is not None
    assert (
        italy.tiles[0]
        == "https://de-linker.com/wp-json/linker/v1/imagery/it?bbox={bbox-epsg-3857}"
    )

    gb = imagery.for_country("GB")
    assert gb is not None
    assert "image.discomap.eea.europa.eu" in gb.tiles[0]

    ukraine = imagery.for_country("UA")
    assert ukraine is None


def test_invalid_session_payload_falls_back_and_non_european_stays_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LINKER_GOOGLE_MAP_TILES_KEY", "test-key")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_kw: _FakeResponse("not-json{"),
    )
    assert imagery.for_country("UA") is None

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda *_a, **_kw: _FakeResponse(json.dumps({"expiry": "not-a-number"})),
    )
    assert imagery.for_country("UA") is None

    # Non-European / sub-national non-EU codes never hit Google.
    assert imagery.for_state("ZZ") is None
    assert imagery.for_state("ENG") is None
    assert imagery.for_state("") is None
