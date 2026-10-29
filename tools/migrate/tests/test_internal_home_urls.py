"""The internal-address gate's German-export rule (#265, audit M2)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

CHECKS = Path(__file__).resolve().parents[2] / "checks"


def load_gate() -> ModuleType:
    sys.path.insert(0, str(CHECKS))
    spec = importlib.util.spec_from_file_location(
        "internal_home_urls", CHECKS / "internal-home-urls.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()


def german_export(tree: Path, html: str) -> Path:
    path = tree / "plugins/linker-commerce/content/livecanvas/de/category_archive.html"
    path.parent.mkdir(parents=True)
    path.write_text(html, encoding="utf-8")
    return path


def test_an_english_site_path_in_a_german_export_fails(tmp_path: Path) -> None:
    """A literal internal href on the German export must stay German (M2:
    /de/category/system-design/ linked to /product/, a 404)."""
    german_export(tmp_path, '<a href="/product/">Unsere Produkte ansehen</a>')

    found = gate.scan_root(tmp_path)
    assert len(found) == 1
    name, line, _text = found[0]
    assert name == "plugins/linker-commerce/content/livecanvas/de/category_archive.html"
    assert line == 1


def test_german_dynamic_and_offsite_hrefs_pass(tmp_path: Path) -> None:
    german_export(
        tmp_path,
        '<a href="/de/produkte/">Produkte</a>'
        '<a href="{Field url}">Beitrag</a>'
        '<a href="#tv-body">Springen</a>'
        "<a href=\"[lc_wc_get_page_url page='shop']\">Shopseite</a>"
        '<a href="mailto:sales@de-linker.com">Mail</a>'
        '<a href="tel:+491744276991">Anruf</a>'
        '<a href="https://example.com/">Extern</a>'
        '<a href="//cdn.example.com/x">CDN</a>',
    )

    assert gate.scan_root(tmp_path) == []


def test_german_site_url_cannot_repeat_its_language_prefix(tmp_path: Path) -> None:
    german_export(
        tmp_path,
        '<script type="application/ld+json">'
        '{"url": "[linker_site_url]de/blog/"}'
        "</script>",
    )

    found = gate.scan_root(tmp_path)

    assert len(found) == 1
    assert found[0][0].endswith("de/category_archive.html")
    assert found[0][2] == "[linker_site_url]de/"


def test_the_english_export_is_out_of_scope(tmp_path: Path) -> None:
    english = (
        tmp_path / "plugins/linker-commerce/content/livecanvas/category_archive.html"
    )
    english.parent.mkdir(parents=True)
    english.write_text('<a href="/products/">Our products</a>', encoding="utf-8")

    assert gate.scan_root(tmp_path) == []


def test_the_php_literal_rule_still_fires(tmp_path: Path) -> None:
    """The gate's original rule (#263): no home_url( '/…' ) literals."""
    plugin = tmp_path / "plugins/linker-commerce/includes/View.php"
    plugin.parent.mkdir(parents=True)
    plugin.write_text("<?php echo home_url( '/contact/' );", encoding="utf-8")

    found = gate.scan_root(tmp_path)
    assert len(found) == 1
    assert found[0][0] == "plugins/linker-commerce/includes/View.php"
