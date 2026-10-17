"""Licences after a load (#252): the owner's key file, live's activation state."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from linker_pull import licenses, live

KEY = "0123456789abcdef0123456789abcdef"  # a stand-in, not the owner's key
APIKEY = "f" * 50  # live's lc_apikey is 50 characters (read 2026-10-17)


class FakeWp:
    def __init__(self) -> None:
        self.options: dict[str, str] = {}
        self.calls: list[tuple[str, ...]] = []

    def run(self, *args: str, stdin: Iterator[bytes] | None = None) -> str:
        self.calls.append(args)
        assert args[:2] == ("option", "update") and stdin is not None
        self.options[args[2]] = b"".join(stdin).decode()
        return ""


@pytest.fixture
def key_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("LINKER_LICENSE_DIR", str(tmp_path))
    (tmp_path / "seopress.env").write_text(f"SEOPRESS_LICENSE_KEY={KEY}\n")
    return tmp_path


def live_state(name: str) -> str:
    return {
        "lc_apikey": APIKEY,
        "seopress_pro_license_status": "valid",
        "seopress_pro_license_expiry": "1812240000",
    }[name]


def test_both_licences_land_through_standard_input_only(key_dir: Path) -> None:
    wp = FakeWp()

    report = licenses.apply(wp, live_state)

    assert report == {"seopress-pro": "applied", "livecanvas": "applied"}
    assert wp.options == {
        "seopress_pro_license_key": KEY,
        "seopress_pro_license_status": "valid",
        "seopress_pro_license_expiry": "1812240000",
        "lc_apikey": APIKEY,
    }
    # No value ever reaches an argument list (or a log built from one).
    flat = " ".join(" ".join(call) for call in wp.calls)
    assert KEY not in flat and APIKEY not in flat
    assert all("--skip-plugins" in call for call in wp.calls)


def test_a_missing_key_file_is_reported_not_guessed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LINKER_LICENSE_DIR", str(tmp_path / "nowhere"))
    wp = FakeWp()

    report = licenses.apply(wp, live_state)

    assert report["seopress-pro"].startswith("not applied: no SEOPRESS_LICENSE_KEY")
    assert "seopress_pro_license_key" not in wp.options
    assert report["livecanvas"] == "applied"


def test_an_unreachable_live_site_leaves_the_licences_out_and_says_why(
    key_dir: Path,
) -> None:
    def unreachable(name: str) -> str:
        raise live.LiveError(f"wp option get {name}: exit 255")

    wp = FakeWp()
    report = licenses.apply(wp, unreachable)

    assert wp.options == {}
    assert report == {
        "seopress-pro": "not applied: wp option get seopress_pro_license_status: exit 255",
        "livecanvas": "not applied: wp option get lc_apikey: exit 255",
    }


def test_quoted_values_and_other_lines_of_the_key_file(tmp_path: Path) -> None:
    file = tmp_path / "seopress.env"
    file.write_text(f"# the owner's key\nOTHER=1\nSEOPRESS_LICENSE_KEY='{KEY}'\n")

    assert licenses.env_value(file, "SEOPRESS_LICENSE_KEY") == KEY
    assert licenses.env_value(file, "MISSING") is None
    assert licenses.env_value(tmp_path / "absent.env", "SEOPRESS_LICENSE_KEY") is None
