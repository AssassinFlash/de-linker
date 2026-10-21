"""Keep the service-page content while making the WordPress input stable."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "service_repair", Path(__file__).parents[1] / "repair-page-inline-blocks.py"
)
assert spec and spec.loader
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def test_only_blank_lines_in_inline_blocks_and_status_bar_newlines_change():
    content = '<p>Current copy. Grüße.</p>\n\n<header class="lk-topbar">\n<a href="/account/">Portal</a>\n<span>·</span>\n<a href="mailto:sales@example.test">Mail</a>\n</header>\n<script>\nvar a=1;\n\n// retained comment\nvar b=2;\n</script>\n<style>\na{color:red}\n\nspan{color:blue}\n</style>\n<p>Unchanged end.</p>'
    fixed = service.repair(content)
    assert fixed.startswith("<p>Current copy. Grüße.</p>\n\n<header")
    assert fixed.endswith("<p>Unchanged end.</p>")
    assert '<a href="/account/">Portal</a> <span>·</span>' in fixed
    assert "var a=1;\n// retained comment\nvar b=2;" in fixed
    assert service.repair(fixed) == fixed


def test_utility_comparisons_survive_texturize_without_changing_prose():
    content = '<div id="tv-utility-page-v1"><p>Keep <strong>copy</strong>.</p><script>if(i<3&&position<0&&dx<0&&delta<0&&track.scrollLeft<width)run();\n\nend();</script></div>'
    fixed = service.repair(content)
    assert "<p>Keep <strong>copy</strong>.</p>" in fixed
    assert "if(3>i&&0>position&&0>dx&&0>delta&&width>track.scrollLeft)" in fixed
    assert service.repair(fixed) == fixed
