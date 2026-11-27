#!/usr/bin/env python3
"""Check public copy for unsupported warehouse and local-stock claims."""

import argparse
import importlib
import json
import re
import shlex
import subprocess
from pathlib import Path

from i18n_sources import gettext_strings, quoted_strings

copy = importlib.import_module("commerce-terms")
ROOT = Path(__file__).resolve().parents[2]
PHRASE = re.compile(
    r"\b(?:german\s+warehouse\s+stock|warehouse\s+stock|warehouse\s+in\s+germany"
    r"|warehouse\s+location|warehouse\s+delivery|our\s+(?:german\s+)?warehouse"
    r"|in\s+its\s+warehouse|stock(?:ed)?\s+in\s+(?:germany|barleben)"
    r"|(?:from|against)\s+(?:our\s+)?stock|local\s+stock|confirmed\s+stock\s+availability"
    r"|lagerbestand(?:\s+in\s+deutschland)?|lagerware(?:\s+in\s+deutschland)?"
    r"|(?:ab|im)\s+(?:deutschen\s+)?lager|auf\s+lager\s+in\s+(?:deutschland|barleben)"
    r"|aus\s+(?:dem|unserem)\s+(?:deutschen\s+)?lager|lager\s+in\s+deutschland"
    r"|lagerverfügbarkeit|lagerlieferung|lagerstandort)\b",
    re.IGNORECASE,
)

# Inline markup can split one phrase; separate headings, cards and cells cannot.
BLOCK_TAGS = set(
    "address article aside blockquote button caption dd details div dl dt fieldset "
    "figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr label li main nav "
    "ol option p pre section summary table td th tr ul".split()
)
META_KEYS = (
    "_seopress_titles_desc",
    "_seopress_social_fb_desc",
    "_seopress_social_twitter_desc",
)


class VisibleCopy(copy.CopyStrings):
    def __init__(self, include_attributes):
        super().__init__()
        self.include_attributes = include_attributes
        self.inline = []
        self.start_line = 1

    def flush(self):
        if self.inline:
            self.strings.append(("".join(self.inline), self.start_line))
            self.inline.clear()

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.flush()
        elif tag == "br":
            self.inline.append(" ")
        super().handle_starttag(tag, attrs if self.include_attributes else [])

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS:
            self.flush()
        super().handle_endtag(tag)

    def handle_data(self, data):
        if self._verbatim:
            return
        line = self.getpos()[0]
        for shortcode in copy.SHORTCODE.finditer(data):
            for value, offset in quoted_strings(copy.CONFIG_PAIR.sub("", shortcode[0])):
                self.strings.append((value, line + offset - 1))
        if not self.inline:
            self.start_line = line
        self.inline.append(copy.SHORTCODE.sub(" ", data))


def visible_text(html, include_attributes=True):
    parser = VisibleCopy(include_attributes)
    parser.feed(html)
    parser.close()
    parser.flush()
    return [(line, text) for text, line in parser.strings if text.strip()]


def json_text(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for child in node.values():
            yield from json_text(child)
    elif isinstance(node, list):
        for child in node:
            yield from json_text(child)


def gettext_sources(root, folders):
    for path in copy.source_paths(root, folders, copy.CODE_SUFFIXES):
        if path.stem.endswith((".test", ".spec")):
            continue
        source = path.read_text(encoding="utf-8")
        for value, line in gettext_strings(
            source, php=path.suffix == ".php", include_plural=True
        ):
            for offset, text in visible_text(value):
                yield str(path.relative_to(root)), line + offset - 1, text


def catalog_text(path):
    """Read each active singular, plural and translated form as one message."""
    source = path.read_text(encoding="utf-8")
    for entry in re.split(r"\n[ \t]*\n", source):
        fields = []
        for match in re.finditer(
            r'^(msgid(?:_plural)?|msgstr(?:\[\d+\])?) (".*"(?:\n".*")*)',
            entry,
            re.MULTILINE,
        ):
            value = "".join(json.loads(line) for line in match[2].splitlines())
            fields.append((match[1], value))
        if any(name == "msgid" and value for name, value in fields):
            yield from (value for _, value in fields)


def repo_strings(root):
    yield from gettext_sources(root, copy.CODE_ROOTS)
    for path in sorted(root.glob("plugins/*/content/**/*.html")):
        for line, text in visible_text(path.read_text(encoding="utf-8")):
            yield str(path.relative_to(root)), line, text

    for path in sorted(root.glob(copy.CATALOG_GLOB)):
        for value in catalog_text(path):
            for _, text in visible_text(value):
                yield str(path.relative_to(root)), None, text

    data_dir = root / "plugins/linker-commerce/data"
    for filename in ("operating-policies.json", "faq-trade.json"):
        path = data_dir / filename
        if path.is_file():
            for value in json_text(json.loads(path.read_text(encoding="utf-8"))):
                for _, text in visible_text(value):
                    yield str(path.relative_to(root)), None, text


def live_rows(wp):
    # Query the published records directly so Polylang's current language
    # cannot filter the second member of a page pair out of the scan.
    php = """<?php
global $wpdb;
$rows = $wpdb->get_results("SELECT ID, post_type, post_name, post_content FROM $wpdb->posts
    WHERE post_status = 'publish' AND post_type IN ('page', 'post') ORDER BY ID", ARRAY_A);
if ($wpdb->last_error) { WP_CLI::error($wpdb->last_error); }
update_meta_cache('post', array_column($rows, 'ID'));
foreach ($rows as &$row) {
    foreach (%s as $key) { $row[$key] = get_post_meta($row['ID'], $key, true); }
}
echo wp_json_encode($rows);
""" % json.dumps(META_KEYS)
    result = subprocess.run(
        [*shlex.split(wp), "eval-file", "-"],
        input=php,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


def live_strings(rows):
    for row in rows:
        page = f"db:{row['post_type']}:{row['ID']}:{row['post_name']}"
        for key in ("post_content", *META_KEYS):
            for line, text in visible_text(row[key], include_attributes=False):
                yield f"{page}:{key}", line, text


def findings(strings):
    for location, line, text in strings:
        for match in PHRASE.finditer(text):
            yield (
                location,
                line and line + text.count("\n", 0, match.start()),
                " ".join(match[0].split()),
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gettext-dir", help="check gettext in one frontend CI package")
    mode.add_argument(
        "--wp-cli",
        action="store_true",
        help="scan published pages, posts and SEO descriptions",
    )
    parser.add_argument(
        "--wp", default="wp", help="WP-CLI command, optionally prefixed with ssh"
    )
    args = parser.parse_args()
    if args.wp_cli:
        rows = live_rows(args.wp)
        print(f"Published pages and posts scanned: {len(rows)}")
        sources = live_strings(rows)
    elif args.gettext_dir:
        sources = gettext_sources(ROOT, (args.gettext_dir,))
    else:
        sources = repo_strings(ROOT)
    hits = list(findings(sources))
    for location, line, match in hits:
        print(f"{location}{':' + str(line) if line else ''}: {match}")
    print(f"Warehouse stock claims: {len(hits)}")
    return int(bool(hits))


if __name__ == "__main__":
    raise SystemExit(main())
