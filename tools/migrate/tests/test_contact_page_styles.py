"""The Contact migration detaches only the reviewed bilingual style block."""

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

spec = importlib.util.spec_from_file_location(
    "contact_page_styles", Path(__file__).parents[1] / "contact-page-styles.py"
)
assert spec and spec.loader
contact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contact)


def test_reviewed_block_is_detached_without_changing_either_localized_body() -> None:
    block = contact.original_block()
    bodies = {
        "28": '<div id="tv-contact-v1">Contact us</div>',
        "6907": '<div id="tv-contact-v1">Kontakt</div>',
    }
    pages = {post: block + content for post, content in bodies.items()}
    changes = contact.plan(pages)
    assert {str(row["id"]): row["after"] for row in changes} == bodies
    assert contact.plan(bodies) == []
    pages["6907"] = bodies["6907"]
    with pytest.raises(ValueError, match="different migration states"):
        contact.plan(pages)
    pages["6907"] = pages["28"].replace("#tv-contact-v1{", "#other{")
    with pytest.raises(ValueError, match="stylesheet changed"):
        contact.plan(pages)


def test_rollback_refuses_subsequent_translation_edits_and_recovers_interrupted_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    block = contact.original_block()
    pages = {post: f'<div id="tv-contact-v1">{post}</div>' for post in ("28", "6907")}
    before: dict[str, Any] = {
        "home": "https://example.test",
        "pages": {key: block + page for key, page in pages.items()},
        "metadata": {
            "28": {"status": ["synced"]},
            "6907": {
                "_linker_i18n_source_hash": [
                    "562380e17ddd6a2ee7af3575361307264acb2486"
                ],
                "units": ["reviewed title and excerpt"],
            },
        },
        "current": True,
    }
    state = copy.deepcopy(before)
    calls = []
    backup = tmp_path / "contact.json"
    monkeypatch.setattr(contact.wp, "read", lambda *args: copy.deepcopy(state))

    def invoke(prefix: str, change: dict[str, Any]) -> dict[str, Any]:
        calls.append(change["mode"])
        assert change["metadata_before"] == state["metadata"]
        for entry in change["changes"]:
            assert state["pages"][str(entry["id"])] == entry["before"]
            state["pages"][str(entry["id"])] = entry["after"]
        if change["mode"] == "adopt":
            state["metadata"]["6907"]["_linker_i18n_source_hash"] = [
                "880b191dbd4f760e5297e5c13db0e53209a91c36"
            ]
            assert (
                json.loads(backup.read_text())["expected_metadata"] == state["metadata"]
            )
            raise OSError("lost connection after commit")
        state["metadata"] = copy.deepcopy(change["metadata_restore"])
        return {"expected_metadata": state["metadata"]}

    monkeypatch.setattr(contact.wp, "invoke", invoke)
    monkeypatch.setattr(sys, "argv", ["contact", "--wp", "wp", "--apply", str(backup)])
    with pytest.raises(OSError, match="lost connection"):
        contact.main()
    contact.main()
    after = copy.deepcopy(state)
    monkeypatch.setattr(
        sys, "argv", ["contact", "--wp", "wp", "--restore", str(backup)]
    )
    state["metadata"]["6907"]["units"] = ["later approved title and excerpt"]
    with pytest.raises(ValueError, match="changed"):
        contact.main()
    assert calls == ["adopt"]
    state.update(after)
    contact.main()
    assert state == before
    assert calls == ["adopt", "restore"]
