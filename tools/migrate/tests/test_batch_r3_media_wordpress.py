"""Retry an interrupted WebP registration on a local WordPress instance."""

import base64
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from batch_r3_pages import media_call

HERE = Path(__file__).resolve().parents[1]
WP = os.environ.get("LINKER_REVIEWED_PAIR_TEST_WP", "")
pytestmark = pytest.mark.skipif(not WP, reason="Requires owned local WordPress")


def php(code: str) -> str:
    return subprocess.run(
        [*shlex.split(WP), "eval", code], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_incomplete_registration_can_be_resumed_and_restored() -> None:
    assert urlsplit(php("echo home_url();")).hostname in {"localhost", "127.0.0.1"}
    source = (
        HERE.parents[1]
        / "plugins/linker-commerce/assets/home-configurator/project-en-390.webp"
    )
    name = "test-r3-photo-" + uuid4().hex
    relative = f"2026/11/{name}-r3.webp"
    before = media_call(WP, mode="inventory", names=[name])
    assert before["photos"][name] is None
    # Break at the point after the native attachment insert and before thumbnail generation.
    attachment = int(
        php(
            f"$file = wp_upload_dir('2026-11')['path'] . '/{name}-r3.webp';"
            "copy(WP_PLUGIN_DIR . '/linker-commerce/assets/home-configurator/project-en-390.webp', $file);"
            "echo wp_insert_attachment(['post_title'=>'R3 registration test','post_mime_type'=>'image/webp'], $file);"
        )
    )
    try:
        pending = media_call(WP, mode="inventory", names=[name])
        assert pending["photos"][name] == {"id": attachment, "file": relative}
        with pytest.raises(RuntimeError):
            media_call(WP, mode="readback", names=[name], ids=[])
        media_call(WP, mode="restore_registrations", before=pending, names=[name])
        assert php(f"echo get_post_type({attachment});") == "attachment"
        result = media_call(
            WP,
            mode="photo",
            name=name,
            data=base64.b64encode(source.read_bytes()).decode(),
        )
        assert result["id"] == attachment
        picture = media_call(WP, mode="readback", names=[name], ids=[])["photos"][name]
        assert picture["id"] == attachment and picture["srcset"]
        media_call(WP, mode="restore_registrations", before=before, names=[name])
        assert media_call(WP, mode="inventory", names=[name])["photos"][name] is None
    finally:
        php(f"wp_delete_attachment({attachment}, true);")
