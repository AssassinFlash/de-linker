"""The public-page command supports all five published bilingual pairs."""

import subprocess
import sys
from pathlib import Path


def test_public_page_command_lists_each_native_pair() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "public-page-copy.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    for page in ("about", "services", "utility", "privacy", "imprint"):
        assert page in result.stdout


def test_release_restores_manual_copy_only_if_translation_state_still_matches(
    tmp_path, monkeypatch
) -> None:
    import importlib.util
    import json

    root = Path(__file__).parents[1]
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location(
        "public_page_copy", root / "public-page-copy.py"
    )
    assert spec and spec.loader
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    original = {
        "home": "http://review.test",
        "current": False,
        "pages": {"862": "EN", "6865": "DE"},
        "metadata": {"862": {"_linker_i18n_status": ["structure_mismatch"]}},
    }
    state = dict(original)
    after = {"862": "EN registration", "6865": "DE Registrierung"}
    monkeypatch.setattr(release, "planned", lambda *args: after)
    monkeypatch.setattr(release.wp, "read", lambda *args: dict(state))

    def save(prefix, payload):
        assert payload["mode"] == "restore"
        assert state["metadata"] == payload["metadata_before"]
        state["pages"] = {str(row["id"]): row["after"] for row in payload["changes"]}
        state["metadata"] = payload["metadata_restore"]

    monkeypatch.setattr(release.wp, "invoke", save)
    argv = [
        "public-page-copy.py",
        "--page",
        "about",
        "--wp",
        "wp",
        "--backup-dir",
        str(tmp_path),
    ]
    monkeypatch.setattr(sys, "argv", [*argv, "--write"])
    release.main()
    assert state["pages"] == after
    release.main()
    saved = json.loads((tmp_path / "review.test-about.json").read_text())
    assert saved["published_metadata"] == state["metadata"]
    state["metadata"] = {"862": {"_linker_i18n_status": ["synced"]}}
    monkeypatch.setattr(sys, "argv", [*argv, "--restore"])
    import pytest

    with pytest.raises(ValueError, match="changed"):
        release.main()
    assert state["pages"] == after
    state["metadata"] = original["metadata"]
    release.main()
    release.main()
    assert state == original
