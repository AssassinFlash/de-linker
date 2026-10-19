#!/usr/bin/env python3
r"""German copy gate: every German surface in the repository follows the
owner's language rulings (issue #265, audit S5: "German text is scattered
over four places with no unified check").

Surfaces and rules
------------------
Kinds of German text the repository itself carries, each with its single
owner (docs/specs/265-german-checks.md):

1. Plugin catalogs `plugins/*/languages/*-de_DE_formal.po` — the owner of
   every plugin PHP/JS string. The gate reads each msgstr (active entries
   only; obsolete `#~` entries are dead and skipped, the header entry too).
2. Script translation JSON `plugins/*/languages/*-de_DE_formal-*.json` —
   generated from the catalogs by `wp i18n make-json`, never hand-edited.
   The gate reads the German values directly, so a hand-edit fails here
   even on a machine without WP-CLI (the byte-for-byte reproduction check
   of `just i18n-coverage` is the other fence).
3. German LiveCanvas exports — every `de/**/*.html` under a plugin's
   `content/` (page twins under `content/livecanvas/de/` and the header
   and footer partials under `content/livecanvas/partials/de/`). Owned by
   the repository and installed by `present`; the migration never writes
   them. The gate reads their human text (text nodes, aria-label, title,
   placeholder, alt and quoted shortcode labels — the same extraction the
   coverage gate uses, so attributes like `dir="ltr"` are not prose).
4. `plugins/linker-commerce/content/journal-titles.json` — the reviewed
   journal labels; its `de` values are repo-owned German copy.

Rules applied to that German text:

- Banned words: the one list `plugins/linker-i18n/data/banned-de.json`,
  the same list the auto-translation enforces on database content
  (Linker\I18n\Translation\Rules::banned_in). Matching semantics are
  ported from that method: a word matches as a whole word ignoring case,
  a trailing * matches compounds and inflections. The pronouns in the
  list (du, dich, dir, dein*, euch, euer*) are the du-form rule: German
  is written in the Sie form (AGENTS.md §3, locale de_DE_formal). Word
  boundaries keep "Dichtung" away from "dich". Known limit, recorded in
  the audit (M5-3) and left to the Genie line: du-imperatives without a
  pronoun ("Nenne mir …") are verb forms no word list can catch.
- The article word: "Artikel" as the blog word is banned (AGENTS.md §3;
  audit M3: "Artikel lesen" → "Beitrag"). Two documented exceptions: the
  legal citation "Artikel <number>" (the reason the shared list itself
  does not carry the word, banned-de.json _source) and the SKU compound
  "Artikelnummer(n)" (the allowance the previous justfile grep carried).
- English date formats: German dates are day-first ("19. Oktober 2026",
  "29.05.2026"; audit M1, fixed by #264). Banned: English month names
  next to a day number ("October 19", "19 October 2026"), ISO dates
  ("2026-10-19") in prose, and in German LiveCanvas exports a
  `date_format="…"` attribute whose first token is not a day token
  (d or j) — "M j, Y" printed "May 29, 2026" on the German blog.
- The English word "catalogue": the vocabulary rule the previous inline
  justfile grep carried (AGENTS.md §3), with its exclusions (the SKU
  compounds Katalognummer and Artikelnummer, and the data/legacy-redirects
  payload), over the raw lines of the plugin content, template and
  language directories.

Database German content (pages, posts, products, terms, SEOPress meta)
has no repository files; auto-translation owns it and enforces the same
banned-de.json at write time. The gate fails when that list is missing,
unparseable or empty: it is the one list both fences share, and losing
it would silently disarm both (issue #265's "a check per kind that
something stays in its place").

Exit code: 0 = every rule holds, 1 = at least one finding (each printed
as `surface path:line rule: excerpt`).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from i18n_sources import FragmentStrings

ROOT = Path(__file__).resolve().parents[2]
BANNED_RELATIVE = Path("plugins/linker-i18n/data/banned-de.json")

# [^\W_] is a letter or digit (unicode): the port of Rules::banned_in's
# (?<![\p{L}\p{N}]) / (?![\p{L}\p{N}]) boundaries to Python's re.
_WORD = r"[^\W_]"

# German dates are day-first ("19. Oktober 2026", "29.05.2026"): an English
# month name next to a day number, or an ISO date, is the English format
# (audit M1; the owner's 2026-10-17 German-only ruling).
_ENGLISH_MONTHS = (
    "January|February|March|April|May|June|July|"
    "August|September|October|November|December"
)
ENGLISH_DATE = re.compile(
    rf"\b(?:{_ENGLISH_MONTHS})\s+\d{{1,2}}\b"
    rf"|\b\d{{1,2}}\s+(?:{_ENGLISH_MONTHS})\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

# "Artikel" as the blog word is banned (AGENTS.md §3; audit M3) with prefix
# semantics, so compounds carry the meaning too ("Artikelkontext",
# "mehrere Artikel(n)"), with the two allowances the shared list documents
# and the previous gate carried: the legal citation "Artikel <number>"
# (banned-de.json _source, the reason the shared list itself does not carry
# the word) and the SKU compound Artikelnummer(n) (the old grep's exclusion).
ARTIKEL = re.compile(rf"(?<!{_WORD})Artikel", re.IGNORECASE)
ARTIKEL_ALLOWED = re.compile(r"(?:\s+\d|nummer)")

# LiveCanvas prints a field's date with PHP's date() tokens; the German
# templates render the day first ("d.m.Y", "j. F Y" — audit M1's fix). An
# attribute whose format does not begin with a day token prints the English
# shape ("M j, Y" printed "May 29, 2026" on the German blog).
DATE_FORMAT_ATTRIBUTE = re.compile(r"""date_format\s*=\s*["']([^"']*)["']""")
DAY_FIRST = re.compile(r"\s*[dj]")


def load_banned(root: Path) -> list[str]:
    """The shared banned-word list, or one loud failure."""
    path = root / BANNED_RELATIVE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        words = data["words"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError(
            f"cannot read the shared banned-word list {BANNED_RELATIVE}: {error}"
        ) from error
    usable = isinstance(words, list) and words and all(
        isinstance(word, str) and word for word in words
    )
    if not usable:
        raise RuntimeError(
            f"the shared banned-word list {BANNED_RELATIVE} carries no words"
        )
    return words


def banned_in(text: str, words: list[str]) -> list[str]:
    """The banned words a German text contains (Rules::banned_in ported)."""
    found: list[str] = []
    for word in words:
        stem = word.rstrip("*")
        pattern = (
            rf"(?<!{_WORD}){re.escape(stem)}"
            + ("" if word.endswith("*") else rf"(?!{_WORD})")
        )
        if re.search(pattern, text, re.IGNORECASE):
            found.append(stem)
    return found


def po_msgstrs(catalog: Path) -> list[tuple[str, int]]:
    """(msgstr, msgid line) of every active entry; header and `#~` skipped."""
    entries: list[tuple[str, int]] = []
    msgid: list[str] | None = None
    msgstr: list[str] | None = None
    obsolete = False
    line_number = 0
    for number, line in enumerate(
        catalog.read_text(encoding="utf-8").splitlines() + [""], start=1
    ):
        if line.startswith("#~"):
            obsolete = True
        stripped = line.removeprefix("#~ ")
        if stripped.startswith("msgid "):
            _flush(entries, msgid, msgstr, line_number, obsolete)
            msgid = [json.loads(stripped[len("msgid ") :])]
            msgstr = None
            obsolete = False
            line_number = number
        elif stripped.startswith("msgstr"):
            inline = stripped.split(" ", 1)[1] if " " in stripped else '""'
            msgstr = [json.loads(inline)]
        elif stripped.startswith('"') and msgstr is not None:
            msgstr.append(json.loads(stripped))
        elif stripped.startswith('"') and msgid is not None:
            msgid.append(json.loads(stripped))
        elif stripped == "":
            _flush(entries, msgid, msgstr, line_number, obsolete)
            msgid = None
            msgstr = None
            obsolete = False
    return entries


def _flush(
    entries: list[tuple[str, int]],
    msgid: list[str] | None,
    msgstr: list[str] | None,
    line_number: int,
    obsolete: bool,
) -> None:
    if msgid is None or msgstr is None or obsolete:
        return
    if "".join(msgid) == "":
        return  # The catalog header: metadata, not copy.
    entries.append(("".join(msgstr), line_number))


def json_german_values(catalog: Path) -> list[tuple[str, str]]:
    """(msgid, value) pairs of a make-json script catalog.

    make-json's shape nests the messages under locale_data; the top level
    carries metadata as strings (translation-revision-date, generator,
    source), the '' header is an object, and each message's translations
    are a list — only list items are German copy.
    """
    data = json.loads(catalog.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    locale = data.get("locale_data")
    messages = locale.get("messages") if isinstance(locale, dict) else None
    if not isinstance(messages, dict):
        return []
    pairs: list[tuple[str, str]] = []
    for msgid, value in messages.items():
        if isinstance(value, list):
            pairs.extend((msgid, item) for item in value if isinstance(item, str))
    return pairs


def german_templates(root: Path) -> list[Path]:
    """Every German HTML export: any `de/` directory under a plugin's content."""
    found: list[Path] = []
    for content in sorted(root.glob("plugins/*/content")):
        for path in sorted(content.rglob("*.html")):
            if "de" in path.relative_to(content).parts:
                found.append(path)
    return found


def template_findings(path: Path, root: Path, words: list[str]) -> list[str]:
    """The text rules on extracted prose plus the date_format attribute rule."""
    relative = path.relative_to(root)
    html = path.read_text(encoding="utf-8")
    findings: list[str] = []
    parser = FragmentStrings()
    parser.feed(html)
    for value, line in parser.strings:
        findings.extend(_text_findings("template", relative, line, value, words))
    for match in DATE_FORMAT_ATTRIBUTE.finditer(html):
        if not DAY_FIRST.match(match.group(1)):
            line = html.count("\n", 0, match.start()) + 1
            findings.append(
                f"template {relative}:{line} date_format is not day-first "
                f"(d.m.Y, j. F Y): {match.group(1)!r}"
            )
    return findings


def journal_de_values(path: Path) -> list[tuple[str, str]]:
    """(key path, value) of every `de` string in the reviewed journal labels."""
    data = json.loads(path.read_text(encoding="utf-8"))
    values: list[tuple[str, str]] = []

    def walk(node: object, keys: list[str]) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "de" and isinstance(child, str):
                    values.append((".".join(keys + [key]), child))
                else:
                    walk(child, keys + [str(key)])
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, keys + [str(index)])

    walk(data, [])
    return values


# The vocabulary rule the previous inline justfile grep carried, with its
# paths and exclusions unchanged (AGENTS.md §3): no "catalogue"/"katalog"
# line in the plugins' content, template and language directories.
CATALOGUE_PATHS = (
    "plugins/linker-commerce/content/livecanvas",
    "plugins/linker-commerce/templates",
    "plugins/linker-commerce/languages",
    "plugins/linker-tools/content",
)
CATALOGUE_LINE = re.compile(r"catalogue|katalog", re.IGNORECASE)
CATALOGUE_ALLOWED = re.compile(
    r"Katalognummer|Artikelnummer|data/legacy-redirects", re.IGNORECASE
)


def catalogue_findings(root: Path) -> list[str]:
    """The absorbed justfile grep: raw lines, allowances included."""
    findings: list[str] = []
    for relative_dir in CATALOGUE_PATHS:
        directory = root / relative_dir
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # Binaries (the compiled .mo) are not prose.
            for number, line in enumerate(text.splitlines(), start=1):
                if CATALOGUE_LINE.search(line) and not CATALOGUE_ALLOWED.search(
                    f"{path.relative_to(root)}:{number}:{line}"
                ):
                    findings.append(
                        f"catalogue {path.relative_to(root)}:{number}: {line.strip()[:60]}"
                    )
    return findings


def german_findings(root: Path, words: list[str]) -> list[str]:
    """Every rule violation on every German surface."""
    findings: list[str] = []
    for catalog in sorted(root.glob("plugins/*/languages/*-de_DE_formal.po")):
        relative = catalog.relative_to(root)
        for msgstr, line in po_msgstrs(catalog):
            findings.extend(_text_findings("po", relative, line, msgstr, words))
    for catalog in sorted(root.glob("plugins/*/languages/*-de_DE_formal-*.json")):
        relative = catalog.relative_to(root)
        for msgid, value in json_german_values(catalog):
            findings.extend(_text_findings("json", relative, msgid, value, words))
    for path in german_templates(root):
        findings.extend(template_findings(path, root, words))
    titles = root / "plugins/linker-commerce/content/journal-titles.json"
    if titles.is_file():
        relative = titles.relative_to(root)
        for key, value in journal_de_values(titles):
            findings.extend(_text_findings("journal", relative, key, value, words))
    return findings


def _text_findings(
    surface: str, name: Path | str, line: int | str, text: str, words: list[str]
) -> list[str]:
    """The word and date rules on one piece of German copy."""
    findings = []
    where = f"{surface} {name}:{line}"
    for stem in banned_in(text, words):
        findings.append(f"{where} banned word ({stem}): {_excerpt(text, stem)}")
    match = ENGLISH_DATE.search(text)
    if match:
        findings.append(f"{where} English date: {match.group(0)!r}")
    for match in ARTIKEL.finditer(text):
        if not ARTIKEL_ALLOWED.match(text, match.end()):
            findings.append(f"{where} article word (Artikel): {_excerpt(text, 'Artikel')}")
            break
    return findings


def _excerpt(text: str, needle: str) -> str:
    """A short piece of the finding around the match."""
    match = re.search(re.escape(needle), text, re.IGNORECASE)
    start = max(0, (match.start() if match else 0) - 20)
    return text[start : start + 50].replace("\n", " ")


def main() -> int:
    try:
        words = load_banned(ROOT)
    except RuntimeError as error:
        print(f"german-copy: {error}", file=sys.stderr)
        return 1
    findings = german_findings(ROOT, words) + catalogue_findings(ROOT)
    for finding in findings:
        print(finding)
    if findings:
        print(f"german-copy: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("german-copy: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
