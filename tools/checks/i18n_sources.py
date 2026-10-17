"""Locate catalog messages in PHP, JS/build and LiveCanvas source fragments."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path

QUOTED = re.compile(r"(['\"`])((?:\\.|(?!\1).)*?)\1", re.DOTALL)
CODE_TOKEN = re.compile(r"/\*.*?\*/|//[^\n]*|#[^\n]*|" + QUOTED.pattern, re.DOTALL)
GETTEXT_CALL = re.compile(
    r"\b(?:__|_e|_x|_ex|_n|_nx|_n_noop|_nx_noop|"
    r"esc_html__|esc_attr__|esc_html_e|esc_attr_e|esc_html_x|esc_attr_x)"
    r"\s*(?:\)\s*)?\(\s*"
)
EXCLUDED = {"vendor", "node_modules", "tests", "languages", ".git"}
SOURCE_SUFFIXES = {".php", ".js", ".jsx", ".ts", ".tsx", ".html"}


def catalog_entries(catalog: Path, *, obsolete: bool = False) -> list[dict[str, str]]:
    """Use gettext's parser, including retained obsolete messages when requested."""
    result = subprocess.run(
        [
            "msgattrib",
            "--only-obsolete" if obsolete else "--clear-obsolete",
            "--no-wrap",
            "--no-location",
            str(catalog),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    entries = []
    for block in result.stdout.split("\n\n"):
        entry = {}
        current = None
        for row in block.splitlines():
            line = row.removeprefix("#~ ")
            if line.startswith(("msgctxt ", "msgid ", "msgid_plural ")):
                name, value = line.split(" ", 1)
                entry[name] = json.loads(value)
                current = name
            elif line.startswith('"') and current is not None:
                entry[current] += json.loads(line)
            else:
                current = None
        if entry.get("msgid"):
            entries.append(entry)
    return entries


def catalog_msgids(catalog: Path, *, obsolete: bool = False) -> list[str]:
    """The message ids whose source presence the coverage gate checks."""
    return [entry["msgid"] for entry in catalog_entries(catalog, obsolete=obsolete)]


def quoted_strings(source: str) -> list[tuple[str, int]]:
    """Literal strings, including escaped PHP quotes/dollars and built JS strings."""
    escapes = {"n": "\n", "r": "\r", "t": "\t"}
    found = []
    for match in QUOTED.finditer(source):
        value = re.sub(
            r"\\([\\'\"`$nrt])",
            lambda escaped: escapes.get(escaped[1], escaped[1]),
            match[2],
        )
        found.append((value, source.count("\n", 0, match.start()) + 1))
    return found


def gettext_strings(source: str) -> list[tuple[str, int]]:
    """Message literals in gettext calls, excluding comments and technical values."""
    found = []
    starts = {call.end() for call in GETTEXT_CALL.finditer(source)}
    for token in CODE_TOKEN.finditer(source):
        if token[1] is None or token.start() not in starts:
            continue
        value = quoted_strings(token[0])[0][0]
        found.append((value, source.count("\n", 0, token.start()) + 1))
    return found


class FragmentStrings(HTMLParser):
    """LC text and accessible labels; CSS classes and identifiers are not copy."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.strings: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"aria-label", "title", "placeholder", "alt"} and value:
                self.strings.append((value, self.getpos()[0]))

    def handle_data(self, data: str) -> None:
        self.strings.append((data, self.getpos()[0]))
        # LC shortcodes can carry labels as quoted attribute values.
        self.strings.extend(
            (value, self.getpos()[0] + line - 1) for value, line in quoted_strings(data)
        )


def source_references(
    plugin: Path, msgids: list[str], *, fragments_only: bool = False
) -> dict[str, list[tuple[str, int]]]:
    """Find exact messages in source, independent of POT reference/obsolete flags."""
    normalized = {" ".join(msgid.split()): msgid for msgid in msgids}
    found: dict[str, list[tuple[str, int]]] = {}
    source_root = plugin / "content/livecanvas" if fragments_only else plugin
    if not source_root.is_dir():
        return found
    for path in sorted(source_root.rglob("*")):
        if path.suffix not in SOURCE_SUFFIXES or EXCLUDED.intersection(path.parts):
            continue
        source = path.read_text(encoding="utf-8")
        if path.suffix == ".html":
            parser = FragmentStrings()
            parser.feed(source)
            strings = parser.strings
        else:
            strings = gettext_strings(source)
        for value, line in strings:
            msgid = normalized.get(" ".join(value.split()))
            if msgid is not None:
                reference = (str(path.relative_to(plugin)), line)
                if reference not in found.setdefault(msgid, []):
                    found[msgid].append(reference)
    return found


def fragment_pot(plugin: Path, output: Path) -> None:
    """Extract known catalog messages still used in language-specific LC markup.

    LC's EN/DE twins already own their prose. The catalog is the dictionary of
    gettext messages to retain, including obsolete translations; source is the
    authority on whether each message remains live. No old POT is read.
    """
    entries = catalog_entries(plugin / "languages" / f"{plugin.name}-de_DE_formal.po")
    references = source_references(
        plugin, [entry["msgid"] for entry in entries], fragments_only=True
    )
    lines = [
        'msgid ""',
        'msgstr ""',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        "",
    ]
    for entry in entries:
        if entry["msgid"] not in references:
            continue
        for path, line in references[entry["msgid"]]:
            lines.append(f"#: {path}:{line}")
        for name in ("msgctxt", "msgid", "msgid_plural"):
            if name in entry:
                lines.append(f"{name} {json.dumps(entry[name], ensure_ascii=False)}")
        if "msgid_plural" in entry:
            # The source catalog's English plural has singular and plural forms.
            lines.extend(['msgstr[0] ""', 'msgstr[1] ""'])
        else:
            lines.append('msgstr ""')
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"LC fragments: {len(references)} live catalog messages -> {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract live LC catalog messages.")
    parser.add_argument("plugin", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    fragment_pot(args.plugin, args.output)
