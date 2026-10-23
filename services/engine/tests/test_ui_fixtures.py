"""The configurator's recorded engine answers are this engine's answers.

The stories and unit tests of plugins/linker-tools answer with the files in its
tests/fixtures/configurator: each is this engine's response to the request the
story sends, with the inputs the story types (App.stories.tsx,
roof/RoofStep.stories.tsx). This test sends every request again on the test
feed and fails when a presented answer changed, so the screens never show a wording or
a figure the engine no longer produces. Server dependency metadata is checked by
test_publication.py; the presentation fixtures retain the actual selection fingerprint.
To record them again:

    UPDATE_UI_FIXTURES=1 uv run pytest tests/test_ui_fixtures.py
"""

from __future__ import annotations

import json
import math
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import TRIFTSTRASSE_5
from fastapi.testclient import TestClient

UI_FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "plugins"
    / "linker-tools"
    / "tests"
    / "fixtures"
    / "configurator"
)
UPDATE = bool(os.environ.get("UPDATE_UI_FIXTURES"))
GENERATED_AT = "2026-10-09T12:00:00Z"
PROFILE = "load-profile-15min.csv"


def load_profile() -> str:
    """A year of 15-minute average power (kW) of a small manufacturing site.

    Synthetic, shaped like one: about 74 kW on workdays from 6:00 to 18:00,
    45 kW around the shift edges, 20 kW at night and at weekends, a winter
    surplus of up to 12 %, and machine starts that add 60 to 110 kW for 15 to
    45 minutes on 25 workdays. About 380 MWh a year; the annual peak falls
    above 150 kW only during those starts, which is what peak shaving is for.
    """
    rng = random.Random(14)
    start = datetime(2025, 1, 1)
    days = 365
    workdays = [d for d in range(days) if (start + timedelta(days=d)).weekday() < 5]
    starts = {
        (day, rng.randrange(7 * 4, 17 * 4)): rng.randint(1, 3)
        for day in rng.sample(workdays, 25)
    }
    values = []
    for index in range(days * 96):
        day, slot = divmod(index, 96)
        when = start + timedelta(days=day, minutes=15 * slot)
        hour = slot / 4
        season = 1 + 0.06 * (1 + math.cos(2 * math.pi * (day - 15) / 365))
        if when.weekday() < 5 and 6 <= hour < 18:
            kw = 74 * season + rng.gauss(0, 7)
        elif when.weekday() < 5 and (5 <= hour < 6 or 18 <= hour < 20):
            kw = 45 * season + rng.gauss(0, 4)
        else:
            kw = 20 * season + rng.gauss(0, 2)
        values.append(kw)
    for (day, slot), length in starts.items():
        extra = rng.uniform(60, 110)
        for offset in range(length):
            values[day * 96 + slot + offset] += extra
    return "".join(f"{max(value, 0):.1f}\n" for value in values)


def requests() -> dict[str, tuple[str, str, dict[str, Any] | None]]:
    """Each fixture's request, as the story's inputs make the configurator send it."""
    profile = load_profile()
    cases: dict[str, tuple[str, str, dict[str, Any] | None]] = {
        "place-80538": ("GET", "/geo/plz/80538", None),
    }
    for locale in ("en", "de"):
        household = {
            "locale": locale,
            "plz": "80538",
            "backup": "none",
            "heat_pump": False,
            "electric_vehicle": False,
        }
        commercial = {
            "locale": locale,
            "plz": "80538",
            "grid_connection_kva": 250,
            "annual_kwh": 380000,
            "load_profile_unit": "kW",
            "site": {"installation": "unknown", "notes": ""},
        }
        cases |= {
            f"residential-{locale}": (
                "POST",
                "/design/residential",
                household | {"annual_kwh": 5000, "pv_kwp": 10, "phase": 3},
            ),
            f"residential-none-{locale}": (
                "POST",
                "/design/residential",
                household
                | {"annual_kwh": 6000, "pv_kwp": 12, "phase": 1, "backup": "needed"},
            ),
            f"commercial-sized-{locale}": (
                "POST",
                "/design/commercial",
                commercial
                | {
                    "goals": ["peak_shaving"],
                    "target_peak_kw": 150,
                    "load_profile_csv": profile,
                },
            ),
            f"commercial-indicative-{locale}": (
                "POST",
                "/design/commercial",
                commercial
                | {
                    "goals": ["peak_shaving", "self_consumption"],
                    "peak_kw": 200,
                    "target_peak_kw": 150,
                    "pv_kwp": 120,
                },
            ),
            # The click lands on the building at Triftstraße 5.
            f"roof-{locale}": (
                "POST",
                "/roof/outline",
                {
                    "plz": "80538",
                    "location": {
                        "latitude": TRIFTSTRASSE_5[0],
                        "longitude": TRIFTSTRASSE_5[1],
                    },
                    "locale": locale,
                },
            ),
        }
    return cases


def compare(path: Path, written: str) -> None:
    if UPDATE:
        path.write_text(written)
    assert path.exists(), f"{path.name} is missing; record it (module docstring)"
    stored = path.read_text()
    if path.suffix == ".json":
        assert json.loads(stored) == json.loads(written), (
            f"{path.name} is stale; record it again (module docstring)"
        )
    else:
        assert stored == written, f"{path.name} is stale"


def test_the_load_profile_is_the_one_the_stories_upload() -> None:
    compare(UI_FIXTURES / PROFILE, load_profile())


@pytest.mark.parametrize("name", sorted(requests()))
def test_each_recorded_answer_is_the_engines_answer(
    name: str, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("linker_engine.app.now", lambda: GENERATED_AT)
    method, url, body = requests()[name]
    response = client.request(method, url, json=body)
    assert response.status_code == 200, response.text

    def presented(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: presented(item)
                for key, item in value.items()
                if key != "publication"
            }
        if isinstance(value, list):
            return [presented(item) for item in value]
        return value

    written = (
        json.dumps(presented(response.json()), ensure_ascii=False, indent="\t") + "\n"
    )
    compare(UI_FIXTURES / f"{name}.json", written)
