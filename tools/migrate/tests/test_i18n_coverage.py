"""Coverage gate behavior against isolated plugin sources and catalogs (#302)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_gate() -> ModuleType:
    checks = Path(__file__).resolve().parents[2] / "checks"
    sys.path.insert(0, str(checks))
    spec = importlib.util.spec_from_file_location(
        "i18n_coverage", checks / "i18n-coverage.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()


@pytest.fixture
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    plugin = tmp_path / "plugins/linker-tools"
    languages = plugin / "languages"
    languages.mkdir(parents=True)
    (languages / "linker-tools-de_DE_formal.po").write_text(
        'msgid ""\nmsgstr ""\n'
        '"Language: de_DE_formal\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n\n'
        'msgid "Save solution"\nmsgstr "Lösung speichern"\n',
        encoding="utf-8",
    )
    exemptions = tmp_path / "exempt.json"
    exemptions.write_text(json.dumps({"catalogs": {}}), encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "EXEMPT_PATH", exemptions)
    return plugin


@pytest.mark.parametrize(
    "source", ["src/screen.tsx", "build/screen.js", "includes/Screen.php"]
)
def test_gate_rejects_a_source_message_missing_from_po(
    plugin: Path, source: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = plugin / source
    path.parent.mkdir(parents=True)
    path.write_text("__('Your roof', 'linker-tools');", encoding="utf-8")

    assert gate.main() == 1
    assert "Your roof" in capsys.readouterr().out


def test_gate_checks_gettext_inside_template_interpolation(
    plugin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (plugin / "screen.js").write_text(
        "const label = ` · ${ __('page %d', 'linker-tools') }`;", encoding="utf-8"
    )
    assert gate.main() == 1
    assert "page %d" in capsys.readouterr().out


def test_gate_checks_javascript_after_a_hash_in_a_regular_expression(
    plugin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (plugin / "screen.js").write_text(
        "const fragment = /#roof/; __('Your roof', 'linker-tools');", encoding="utf-8"
    )
    assert gate.main() == 1
    assert "Your roof" in capsys.readouterr().out


def test_gate_rejects_a_handwritten_script_json(
    plugin: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (
        plugin / "languages/linker-tools-de_DE_formal-linker-tools-screen.json"
    ).write_text(
        json.dumps({"locale_data": {"messages": {"Your roof": ["Ihr Dach"]}}}),
        encoding="utf-8",
    )

    assert gate.main() == 1
    assert "JSON" in capsys.readouterr().out


@pytest.fixture
def generated_json(plugin: Path) -> Path:
    catalog = plugin / "languages/linker-tools-de_DE_formal.po"
    catalog.write_text(
        catalog.read_text(encoding="utf-8").replace(
            'msgid "Save solution"', '#: build/screen.js\nmsgid "Save solution"'
        ),
        encoding="utf-8",
    )
    wp = shutil.which("wp")
    assert wp is not None, "WP-CLI is required by the script-catalog coverage gate"
    subprocess.run(
        [
            os.environ.get("PHP", "php"),
            wp,
            "i18n",
            "make-json",
            str(catalog),
            "--no-purge",
        ],
        check=True,
        capture_output=True,
    )
    return next(catalog.parent.glob("*.json"))


def test_gate_accepts_native_json_without_purging_po(
    generated_json: Path, plugin: Path
) -> None:
    catalog = plugin / "languages/linker-tools-de_DE_formal.po"
    before = catalog.read_bytes()
    assert gate.main() == 0
    assert catalog.read_bytes() == before
    assert generated_json.exists()


@pytest.mark.parametrize("mutation", ["translation", "plural", "missing"])
def test_gate_rejects_modified_or_missing_generated_json(
    generated_json: Path, mutation: str, capsys: pytest.CaptureFixture[str]
) -> None:
    if mutation == "missing":
        generated_json.unlink()
    else:
        data = json.loads(generated_json.read_text(encoding="utf-8"))
        data["locale_data"]["messages"]["Save solution"] = (
            ["Changed"]
            if mutation == "translation"
            else ["Lösung speichern", "Unexpected"]
        )
        generated_json.write_text(json.dumps(data), encoding="utf-8")

    assert gate.main() == 1
    assert "JSON" in capsys.readouterr().out


def test_gate_ignores_development_files_and_commented_calls(plugin: Path) -> None:
    (plugin / "screen.test.tsx").write_text("__('Test only', 'linker-tools');")
    (plugin / "screen.stories.tsx").write_text("__('Story only', 'linker-tools');")
    (plugin / "screen.js").write_text("/* __('Comment only', 'linker-tools') */")
    assert gate.main() == 0


def test_gate_checks_only_the_plugins_text_domain(plugin: Path) -> None:
    (plugin / "screen.js").write_text(
        "__('>', 'not a translation'); __('Other plugin', 'woocommerce');"
        "__('Save solution', 'linker-tools');"
    )
    assert gate.main() == 0
