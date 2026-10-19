"""German copy gate behavior against isolated plugin trees (#265).

The gate is the CI surface: its main() exit code and printed findings are
what `just german-copy` and CI consume. Fixtures plant one defect at a time
in a temporary repository tree; the shared banned-word list is the real one
the translator enforces (plugins/linker-i18n/data/banned-de.json).
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

CHECKS = Path(__file__).resolve().parents[2] / "checks"
BANNED_SOURCE = (
    Path(__file__).resolve().parents[3] / "plugins/linker-i18n/data/banned-de.json"
)


def load_gate() -> ModuleType:
    sys.path.insert(0, str(CHECKS))
    spec = importlib.util.spec_from_file_location(
        "german_copy", CHECKS / "german-copy.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = load_gate()


def tree() -> Path:
    """The gate's repository root, typed (a module attribute is Any)."""
    return Path(gate.ROOT)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository tree with the shared banned-word list and nothing else."""
    data = tmp_path / "plugins/linker-i18n/data"
    data.mkdir(parents=True)
    shutil.copy(BANNED_SOURCE, data / "banned-de.json")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return tmp_path


def write_po(plugin: str, name: str, *entries: tuple[str, str]) -> Path:
    """Write one de_DE_formal catalog; each entry is (msgid, msgstr)."""
    languages = tree() / "plugins" / plugin / "languages"
    languages.mkdir(parents=True, exist_ok=True)
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        '"Plural-Forms: nplurals=2; plural=(n != 1);\\n"',
        "",
    ]
    for msgid, msgstr in entries:
        lines.append(f'msgid "{msgid}"')
        lines.append(f'msgstr "{msgstr}"')
        lines.append("")
    catalog = languages / f"{name}-de_DE_formal.po"
    catalog.write_text("\n".join(lines), encoding="utf-8")
    return catalog


def test_a_banned_word_in_a_po_msgstr_fails_the_gate(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_po(
        "linker-commerce",
        "linker-commerce",
        ("Add to cart", "In den Warenkorb legen"),
    )

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "Warenkorb" in out
    assert "linker-commerce-de_DE_formal.po" in out


def test_a_clean_po_msgstr_passes_the_gate(repo: Path) -> None:
    write_po(
        "linker-commerce",
        "linker-commerce",
        ("Add to solution draft", "Zum Lösungsentwurf hinzufügen"),
    )

    assert gate.main() == 0


def test_the_du_form_in_a_po_msgstr_fails_the_gate(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_po("linker-tools", "linker-tools", ("Your roof", "Dein Dach"))

    assert gate.main() == 1
    out = capsys.readouterr().out
    # The shared list's pronoun entries are the du-form rule (its _source
    # documents them); the finding names the matched stem and the excerpt.
    assert "banned word (dein)" in out
    assert "Dein Dach" in out


def test_an_obsolete_po_entry_is_dead_copy(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The catalog's `#~` entries no longer ship; only active msgstr counts."""
    languages = repo / "plugins/linker-commerce/languages"
    languages.mkdir(parents=True)
    (languages / "linker-commerce-de_DE_formal.po").write_text(
        'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=UTF-8\\n"\n\n'
        '#~ msgid "Add to cart"\n#~ msgstr "In den Warenkorb"\n\n'
        'msgid "Send inquiry"\nmsgstr "Anfrage senden"\n',
        encoding="utf-8",
    )

    assert gate.main() == 0


def test_a_missing_shared_banned_list_disarms_both_fences(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Database German is kept by auto-translation through the same list."""
    (repo / "plugins/linker-i18n/data/banned-de.json").unlink()

    assert gate.main() == 1
    assert "banned-word list" in capsys.readouterr().err


@pytest.mark.parametrize(
    "msgstr",
    [
        "Veröffentlicht am October 19",  # English month before the day
        "Veröffentlicht am 19 October 2026",  # day before the English month
        "May 29, 2026",  # the format the audit found on the German blog
        "Gültig ab 2026-10-19",  # ISO date in German prose
    ],
)
def test_an_english_date_in_a_po_msgstr_fails_the_gate(
    repo: Path, msgstr: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write_po("linker-commerce", "linker-commerce", ("Published", msgstr))

    assert gate.main() == 1
    assert "English date" in capsys.readouterr().out


@pytest.mark.parametrize(
    "msgstr",
    [
        "Veröffentlicht am 19. Oktober 2026",  # the site's long German date
        "Veröffentlicht am 29.05.2026",  # the site's numeric German date
        "Version 2.1.3 vom 19. Oktober 2026",  # version numbers stay legal
    ],
)
def test_german_dates_pass_the_gate(repo: Path, msgstr: str) -> None:
    write_po("linker-commerce", "linker-commerce", ("Published", msgstr))

    assert gate.main() == 0


@pytest.mark.parametrize(
    "msgstr",
    [
        "Artikel lesen",  # the blog word the audit found (M3)
        "Alle Artikel anzeigen",
        "Artikelkontext",  # compounds carry the meaning too
        "Fracht für mehrere Artikel",
    ],
)
def test_the_blog_article_word_fails_the_gate(
    repo: Path, msgstr: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write_po("linker-commerce", "linker-commerce", ("Read article", msgstr))

    assert gate.main() == 1
    assert "article word (Artikel)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "msgstr",
    [
        "Artikel 6 DSGVO",  # the legal citation the shared list itself notes
        "Siehe Artikel 13 der DSGVO",
        "Artikelnummer: DLK-SAJ-B2100HV1",  # the SKU compound allowance
        "Ohne Artikelnummer",
    ],
)
def test_legal_citations_and_sku_numbers_pass_the_gate(repo: Path, msgstr: str) -> None:
    write_po("linker-commerce", "linker-commerce", ("Legal", msgstr))

    assert gate.main() == 0


def write_json(plugin: str, name: str, messages: dict[str, object]) -> Path:
    """One generated script catalog in make-json's shape: metadata string
    keys at the top, the messages under locale_data, the '' header an
    object, each msgid a translation list."""
    languages = tree() / "plugins" / plugin / "languages"
    languages.mkdir(parents=True, exist_ok=True)
    path = languages / f"{name}-de_DE_formal-00000000000000000000000000000000.json"
    path.write_text(
        json.dumps(
            {
                "translation-revision-date": "2026-10-19 00:00+0000",  # metadata, not copy
                "generator": "WP-CLI",
                "locale_data": {"messages": messages},
            }
        ),
        encoding="utf-8",
    )
    return path


def test_a_hand_edited_german_json_value_fails_the_gate(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """JSON is generated from the PO; its German values are checked directly."""
    write_json("linker-tools", "linker-tools", {"Your roof": ["Dein Dach"]})

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "json" in out
    assert "banned word (dein)" in out


def test_generated_json_metadata_is_not_copy(repo: Path) -> None:
    write_json(
        "linker-tools",
        "linker-tools",
        {"": {"domain": "messages", "plural-forms": "nplurals=2; plural=(n != 1);"}},
    )

    assert gate.main() == 0


def write_german_template(relative: str, html: str) -> Path:
    """One German LiveCanvas export anywhere a plugin's content keeps a de/ tree."""
    path = tree() / "plugins" / "linker-commerce" / "content" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def test_the_du_form_in_a_german_template_fails_the_gate(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_german_template("livecanvas/de/blog_index.html", "<h2>Deine Auswahl</h2>")

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "de/blog_index.html" in out
    assert "banned word (deine)" in out


def test_a_german_templates_attributes_are_not_prose(repo: Path) -> None:
    """`dir="ltr"` and friends are markup, not du-form copy."""
    write_german_template(
        "livecanvas/partials/de/header.html",
        '<html dir="ltr"><body>Ihre Auswahl</body></html>',
    )

    assert gate.main() == 0


def test_a_german_templates_label_attributes_are_copy(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_german_template(
        "livecanvas/de/search.html",
        '<input placeholder="Artikel suchen">',
    )

    assert gate.main() == 1
    assert "article word (Artikel)" in capsys.readouterr().out


@pytest.mark.parametrize(
    "php_format",
    [
        "M j, Y",  # printed "May 29, 2026" on the German blog (audit M1)
        "F j, Y",
        "Y-m-d",
    ],
)
def test_an_english_date_format_in_a_german_template_fails_the_gate(
    repo: Path, php_format: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write_german_template(
        "livecanvas/de/blog_index.html",
        f'<field name="publish_date" date_format="{php_format}"></field>',
    )

    assert gate.main() == 1
    assert "date_format" in capsys.readouterr().out


@pytest.mark.parametrize("php_format", ["d.m.Y", "j. F Y"])
def test_a_german_date_format_in_a_german_template_passes(
    repo: Path, php_format: str
) -> None:
    write_german_template(
        "livecanvas/de/blog_index.html",
        f'<field name="publish_date" date_format="{php_format}"></field>',
    )

    assert gate.main() == 0


def test_english_templates_are_out_of_scope(repo: Path) -> None:
    """The English export keeps its own vocabulary and date conventions."""
    english = tree() / "plugins/linker-commerce/content/livecanvas/blog_index.html"
    english.parent.mkdir(parents=True)
    english.write_text(
        '<h2>Your choice</h2><field name="publish_date" date_format="M j, Y"></field>',
        encoding="utf-8",
    )

    assert gate.main() == 0


def write_journal_titles(entries: dict[str, dict[str, dict[str, str]]]) -> Path:
    path = tree() / "plugins/linker-commerce/content/journal-titles.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_a_banned_word_in_a_journal_title_fails_the_gate(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_journal_titles(
        {
            "a-post": {
                "full": {"en": "A title", "de": "Ihr Warenkorb im Blick"},
                "label": {"en": "Cart view", "de": "Warenkorb"},
            }
        }
    )

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "journal-titles.json" in out
    assert "banned word (Warenkorb)" in out


def test_the_english_half_of_a_journal_title_is_not_german_copy(repo: Path) -> None:
    write_journal_titles(
        {
            "a-post": {
                "full": {"en": "Browse the catalogue", "de": "Das Sortiment"},
                "label": {"en": "Catalogue", "de": "Sortiment"},
            }
        }
    )

    assert gate.main() == 0


# The paths and exclusions of the previous inline justfile grep, unchanged.
CATALOGUE_PATHS = (
    "plugins/linker-commerce/content/livecanvas",
    "plugins/linker-commerce/templates",
    "plugins/linker-commerce/languages",
    "plugins/linker-tools/content",
)


def write_repo_file(relative: str, text: str) -> Path:
    path = tree() / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "relative",
    [
        "plugins/linker-commerce/templates/emails/an-email.php",
        "plugins/linker-commerce/languages/linker-commerce.pot",
    ],
)
def test_the_english_catalogue_word_fails_the_gate(
    repo: Path, relative: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """The vocabulary rule the old justfile grep carried, now inside the gate."""
    write_repo_file(relative, 'msgid "Browse the catalogue"\n')

    assert gate.main() == 1
    out = capsys.readouterr().out
    assert f"catalogue {relative}:1" in out


def test_the_catalogue_exclusions_stay(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The old grep's allowances: the SKU word on German copy, the legacy
    redirect data outside the scanned content trees. Katalognummer is a
    legacy data word Materials rewrites at runtime; new German copy does
    not reintroduce it (the shared list's semantics are unchanged)."""
    write_repo_file(
        "plugins/linker-commerce/content/livecanvas/de/single_product.html",
        "<span>Artikelnummer</span>",
    )
    write_repo_file(
        "plugins/linker-commerce/data/legacy-redirects.json",
        '"/katalog/": "/produkte/"',
    )

    assert gate.main() == 0

    write_repo_file(
        "plugins/linker-commerce/content/livecanvas/de/single_product.html",
        "<span>Die Katalognummer</span>",
    )

    assert gate.main() == 1
    assert "banned word (Katalog)" in capsys.readouterr().out
