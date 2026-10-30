"""Private loaded-data version across a nightly feed rotation and process restart."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from conftest import FIXTURES, publication_feed
from fastapi.testclient import TestClient

from linker_engine.app import SOURCE, Services, Settings, create_app
from linker_engine.version import digest, source_bytes

TOKEN = {"X-Linker-Service-Token": "synthetic-version-token"}
POLYGON = [
    [11.58836, 48.14024],
    [11.58850, 48.14024],
    [11.58850, 48.14030],
    [11.58836, 48.14030],
]


def test_private_version_is_loaded_data_not_later_disk_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-version-token")
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("LINKER_ENGINE_CACHE", str(tmp_path / "cache"))
    feed, contract = tmp_path / "feed.json", tmp_path / "compatibility.json"
    feed.write_text(
        json.dumps(
            publication_feed(
                json.loads((FIXTURES / "feed.json").read_text()),
                json.loads((FIXTURES / "compatibility.json").read_text()),
            )
        )
    )
    shutil.copyfile(FIXTURES / "compatibility.json", contract)
    settings = Settings(feed, contract, tmp_path / "cache")
    feed_a, contract_a = feed.read_bytes(), contract.read_bytes()
    loaded = Services(settings, SOURCE)
    canonical_contract = json.dumps(
        json.loads(contract_a),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert loaded.version == digest(SOURCE, feed_a, canonical_contract)
    with TestClient(create_app(settings)) as before:
        assert before.get("/resource/version").status_code == 401
        version_a = before.get("/resource/version", headers=TOKEN).json()["version"]
        assert version_a == loaded.version
        document = json.loads(feed_a)
        document["generated_at"] = "2026-10-22T03:40:00Z"
        feed.write_text(json.dumps(document))
        document = json.loads(contract_a)
        document["version"] = "synthetic-nightly-rotation"
        contract.write_text(json.dumps(document))
        revised = json.loads(feed.read_text())
        revised["compatibility"] = document
        revised["compatibility_version"] = document["version"]
        feed.write_text(json.dumps(revised))
        assert (
            before.get("/resource/version", headers=TOKEN).json()["version"]
            == version_a
        )
        assert loaded.engine.products.generated_at == json.loads(feed_a)["generated_at"]
        with TestClient(create_app(settings)) as restarted:
            reply = restarted.get("/resource/version", headers=TOKEN)
            version_b = reply.json()["version"]
            assert reply.headers["cache-control"] == "private, no-store"
            assert version_b != version_a
            canonical_contract = json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
            assert version_b == digest(SOURCE, feed.read_bytes(), canonical_contract)
            headers = {
                **TOKEN,
                "X-Linker-Resource-Subject": "a" * 64,
                "X-Linker-Engine-Version": version_a,
            }
            stale = restarted.post(
                "/roof/pack", headers=headers, content="not even parsed"
            )
            assert stale.status_code == 409
            assert stale.json()["detail"] == "engine version changed"
            headers["X-Linker-Engine-Version"] = version_b
            computed = restarted.post(
                "/roof/pack",
                headers=headers,
                json={"polygon": POLYGON, "tilt_deg": 30, "azimuth_deg": 180},
            )
            assert computed.status_code == 200
            assert computed.headers["x-linker-engine-version"] == version_b


def test_services_use_current_woo_projection(tmp_path: Path) -> None:
    document = publication_feed(
        json.loads((FIXTURES / "feed.json").read_text()),
        json.loads((FIXTURES / "compatibility.json").read_text()),
    )
    feed, contract = tmp_path / "feed.json", tmp_path / "compatibility.json"
    feed.write_text(json.dumps(document))
    contract.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": "retired-static-input",
                "pairs": [],
                "requirements": [],
            }
        )
    )
    settings = Settings(feed, contract, tmp_path / "cache")
    loaded = Services(settings, SOURCE)
    assert loaded.engine.compatibility.version == document["compatibility_version"]
    canonical_contract = json.dumps(
        document["compatibility"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    assert loaded.version == digest(SOURCE, feed.read_bytes(), canonical_contract)
    document["compatibility_version"] = "different-generation"
    feed.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="not one generation"):
        Services(settings, SOURCE)
    document.pop("compatibility")
    feed.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="current Woo compatibility projection"):
        Services(settings, SOURCE)


def test_private_version_failure_and_source_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "enforce")
    monkeypatch.setenv("GENIE_SERVICE_TOKEN", "synthetic-version-token")
    missing = Settings(
        tmp_path / "missing-feed", tmp_path / "missing-contract", tmp_path
    )
    with TestClient(create_app(missing)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/resource/version").status_code == 401
        assert client.get("/resource/version", headers=TOKEN).status_code == 503
        monkeypatch.setenv("LINKER_ENGINE_GATE_MODE", "off")
        assert client.get("/resource/version", headers=TOKEN).status_code == 503
    code = tmp_path / "code"
    code.mkdir()
    (code / "app.py").write_bytes(b"synthetic-source-a")
    captured = source_bytes(code)
    (code / "app.py").write_bytes(b"synthetic-source-b")
    assert digest(captured, b"feed", b"contract") != digest(
        source_bytes(code), b"feed", b"contract"
    )
