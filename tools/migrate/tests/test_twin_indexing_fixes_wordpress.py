"""The template repair keeps JSON-LD through a real WordPress KSES save.

Opt in with LINKER_TWIN_INDEXING_TEST_WP, the WP-CLI command of an owned local
snapshot containing posts 623, 6873 and 6881. The test restores the template
content and indexing meta it touches before returning.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any
from urllib.parse import urlsplit

import pytest

WP = os.environ.get("LINKER_TWIN_INDEXING_TEST_WP", "")
pytestmark = pytest.mark.skipif(
    not WP, reason="Requires an owned local snapshot WordPress"
)


def migration() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "twin-indexing-fixes.py"
    spec = importlib.util.spec_from_file_location("twin_indexing_fixes_wp", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def php(source: str) -> dict[str, Any]:
    result = subprocess.run(
        [*shlex.split(WP), "eval", source],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    line = next(
        line for line in result.stdout.splitlines() if line.startswith("@@seo@@")
    )
    value: dict[str, Any] = json.loads(line.removeprefix("@@seo@@"))
    return value


def test_the_real_template_keeps_its_jsonld_after_apply(tmp_path: Path) -> None:
    module = migration()
    prefix = shlex.split(WP)
    fixture = php(
        """
        $source = get_post(623);
        $twin = get_post(6873);
        $template = get_post(6881);
        if (!$source || !$twin || !$template) {
            throw new RuntimeException('The local snapshot lacks the measured objects.');
        }
        $host = wp_parse_url(home_url(), PHP_URL_HOST);
        if (!in_array($host, ['127.0.0.1', 'localhost'], true)) {
            throw new RuntimeException('Refusing a non-local site.');
        }
        $previous = [
            'content' => $template->post_content,
            'source_index' => get_post_meta(623, '_seopress_robots_index', true),
            'twin_index' => get_post_meta(6873, '_seopress_robots_index', true),
            'max_revision' => (int) $GLOBALS['wpdb']->get_var('SELECT MAX(ID) FROM ' . $GLOBALS['wpdb']->posts . ' WHERE post_parent = 6881'),
        ];
        kses_remove_filters();
        wp_update_post([
            'ID' => 6881,
            'post_content' => '<script type="application/ld+json">{"url":"[linker_site_url]de/blog/"}</script>',
        ], true);
        update_post_meta(623, '_seopress_robots_index', 'yes');
        echo '@@seo@@' . wp_json_encode($previous);
        """
    )
    assert urlsplit(
        str(php("echo '@@seo@@'.wp_json_encode(['home'=>home_url()]);")["home"])
    ).hostname in {
        "127.0.0.1",
        "localhost",
    }

    try:
        state = module.read_state(prefix)
        actions = module.plan(state)
        module.apply(prefix, actions, tmp_path / "backup.json")
        after = module.read_state(prefix)
        assert module.verify(after) == []
        assert after["template"]["scripts"] == 1
        assert after["template"]["doubled"] == 0
    finally:
        escaped = json.dumps(fixture)
        php(
            f"""
            $previous = json_decode({json.dumps(escaped)}, true);
            kses_remove_filters();
            wp_update_post([
                'ID' => 6881,
                'post_content' => $previous['content'],
            ], true);
            update_post_meta(623, '_seopress_robots_index', $previous['source_index']);
            update_post_meta(6873, '_seopress_robots_index', $previous['twin_index']);
            $GLOBALS['wpdb']->query(
                $GLOBALS['wpdb']->prepare(
                    'DELETE FROM ' . $GLOBALS['wpdb']->posts . ' WHERE post_parent = 6881 AND ID > %d',
                    $previous['max_revision']
                )
            );
            echo '@@seo@@' . wp_json_encode(['restored' => true]);
            """
        )
