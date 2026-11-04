#!/usr/bin/env python3
"""Commerce vocabulary gate: customer-visible copy never describes a shop.

The site has one customer link — product → inquiry, presented as a Proforma —
and everything after it happens offline (AGENTS.md §1). Copy that names a
checkout, a payment, a shipping step, a basket or a catalogue describes a
purchase path that does not exist, so a customer follows it and finds nothing.

The wordlist `commerce-terms.txt` beside this file is the single authority
(issue #905): AGENTS.md §3 and docs/specs/11-commerce.md point at it instead of
carrying their own copies, so the list cannot drift between the two documents
and the gate.

Surfaces
--------
Only copy that reaches a customer is read, and only as copy:

1. Plugin, theme and planner sources — the literal arguments of gettext calls
   (`__()`, `_e()`, `esc_html__()`, `_n()`, … plus their `_x` forms) in
   `.php`, `.ts`, `.tsx`, `.js` and `.jsx` under `plugins/`, `themes/` and
   `apps/planner/src`. In this tree every customer-visible React string goes
   through `@wordpress/i18n`, so this is exactly the shipped UI copy; a bare
   string literal is markup plumbing, not prose.
2. LiveCanvas exports and partials — `*.html` under a plugin's `content/`,
   read as prose: text nodes and `aria-label`/`title`/`placeholder`/`alt`.
   Three things that look like text are not, and each is removed before the
   wordlist runs:
   - shortcode syntax. `[lc_get_cats ... orderby="name" order="ASC"]` names a
     rendering instruction, and `[woocommerce_cart]` names a shortcode. Both
     are markup: the words a customer reads come from the shortcode's copy
     attributes (measured, not assumed: `label`, `prefix`, `suffix`,
     `screen_reader_text`, `title_li`) and from the prose outside the brackets.
     Configuration attributes (`orderby`, `order`, `taxonomy`, `count`, `depth`,
     `type`, `name`, `param`, `surface`, `class`, `href`, …) are dropped whole.
   - merge placeholders. `{order_number}` renders as a number, so
     "Your inquiry #{order_number}" shows no banned word to a customer.
   - script and style bodies. `var base = 'tv-article-section-'` is code.
3. Catalogs — every active entry of `plugins/*/languages/*.po`, both the
   `msgid` (the English source the customer reads) and the `msgstr` (the
   German the customer reads). The compiled `.mo` is not read: it is built
   from the `.po` and would only repeat a hit whose source is already here.

Compiled bundles (`build/`, `dist/`) are not scanned: they are generated from
these sources, so a hit there is either a duplicate of one found here or stale.
Tests, `vendor/`, `node_modules/` and `languages/` (read separately as
catalogs) are not customer surfaces either.

`mu-plugins/` is absent, and the reason is narrower than "no copy there": the
four gettext strings in it are one REST refusal ("Sorry, you are not allowed to
do that.") repeated four times, shown to a blocked API caller. Including the
directory would cost four extractions to watch one sentence, and that sentence
would be baselined the moment it needed a word this gate lists. If a customer
sentence ever appears there, this comment is the place that says why it was
missed — and the fix is to add the root, not to add an exemption.

Failure policy — a ratchet
--------------------------
New copy must be clean. Copy that already contains a word may not grow:
`commerce-terms-baseline.json` records every existing hit per file and term
together with the reason it stands. The gate fails when

- a hit has no baseline entry (a new one),
- a file holds more occurrences of a baselined string than the baseline records,
- a baseline entry is stale (its string is gone — the baseline shrinks or the
  entry is wrong), or
- a baseline entry carries no justification string.

Live database content
---------------------
`--wp-cli` scans the published pages and posts of a running site through
WP-CLI, read-only, for the deploy smoke. It shares the wordlist, the prose
extractor and the baseline (keyed `db:<post_type>:<slug>`), so a page added in
the database cannot introduce vocabulary the repository gate would reject.

It reads content through a bulk listing, and per row through
`wp post get <id> --field=post_content` when the listing omits the column. A
build that silently dropped the content would otherwise report a clean site
for copy that is not clean, which is the one failure mode a smoke must not
have: an unreadable row raises instead of counting as clean.

The four legal pages (privacy policy, terms of sale and their German twins)
are exempt from failing: real legal text is protected copy (owner ruling
2026-10-25), and a statute or a translated standard names things this gate
bans. They are not silently skipped — every hit is printed in a separate legal
report so the deploy reviewer can apply the sentence triage recorded in
docs/acceptance/2026-11-04/905/copy-review.md. Their hits are never baselined;
the report line is the record.

Exit 0 when no finding stands outside the baseline. Exit 1 otherwise, printing
one line per finding.

Usage:
    python3 tools/checks/commerce-terms.py
    python3 tools/checks/commerce-terms.py --wp-cli --wp /usr/local/bin/wp
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from i18n_sources import gettext_strings, quoted_strings

ROOT = Path(__file__).resolve().parents[2]
HEREDIR = Path(__file__).resolve().parent
WORDS_PATH = HEREDIR / "commerce-terms.txt"
BASELINE_PATH = HEREDIR / "commerce-terms-baseline.json"

CODE_ROOTS = ("plugins", "themes", "apps/planner/src")
CODE_SUFFIXES = {".php", ".ts", ".tsx", ".js", ".jsx"}
FRAGMENT_ROOTS = ("plugins",)
CATALOG_GLOB = "plugins/*/languages/*.po"
EXCLUDED_PARTS = {
    "vendor",
    "node_modules",
    "tests",
    "build",
    "dist",
    "languages",
    ".git",
}

# Owner ruling 2026-10-25 protects real legal text. The slugs are the four live
# pages (issue #905, verified against production wp_posts); they exempt a page
# from failing while its hits are still reported.
LEGAL_SLUGS = ("privacy-policy", "datenschutz", "terms-of-sale", "verkaufsbedingungen")

# [^\W_] is a letter or digit (unicode): the same word boundary the shared
# German list uses (Linker\I18n\Translation\Rules::banned_in).
_WORD = r"[^\W_]"

PLURAL_MSGSTR = re.compile(r"msgstr\[\d+\] ")

# Shortcode configuration, measured over the shipped fragments' attributes. A
# value of one of these names selects data; it is never read as copy.
CONFIG_ATTRIBUTES = frozenset(
    {
        "categories",
        "class",
        "condition",
        "conjunction",
        "count",
        "date_format",
        "depth",
        "format",
        "href",
        "id",
        "intent",
        "key",
        "lang",
        "name",
        "of",
        "offset",
        "order",
        "orderby",
        "page",
        "param",
        "part",
        "placement",
        "post",
        "rel",
        "role",
        "size",
        "src",
        "style",
        "surface",
        "target",
        "taxonomy",
        "type",
        "use_desc_for_title",
        "value",
        "width",
        "height",
    }
)
CONFIG_PAIR = re.compile(
    r"""\b(?:%s)\s*=\s*(?:"[^"]*"|'[^']*')"""
    % "|".join(sorted(CONFIG_ATTRIBUTES))
)
SHORTCODE = re.compile(r"\[[^\[\]]*\]")

# A merge field renders as data ("Your inquiry #1042"), so its name is not
# copy. `%d`/`%s` and `%%` are the same idea in the printf style.
MERGE_FIELD = re.compile(r"\{[^{}]*\}|%%|%[1-9]?\$?[dsf]")

# The statute citation is not the blog word: "Article 3 installed power"
# cites a regulation, the same allowance german-copy.py carries for the German
# "Artikel <number>" (banned-de.json _source).
ALLOWANCES: dict[str, re.Pattern[str]] = {
    "article": re.compile(rf"(?<!{_WORD})Article\s+\d", re.IGNORECASE),
    "articles": re.compile(rf"(?<!{_WORD})Article\s+\d", re.IGNORECASE),
}


class CopyStrings(HTMLParser):
    """The prose of a LiveCanvas export: text, labels, and shortcode labels.

    `FragmentStrings` in i18n_sources reads every quoted value in a text node,
    which is right for catalog extraction and wrong here: a shortcode's
    `orderby="name"` would read as the word "order". This extractor drops the
    configuration pairs, then keeps both the remaining quoted values (the copy
    attributes) and the prose outside the shortcodes.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.strings: list[tuple[str, int]] = []
        self._verbatim = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._verbatim += 1
            return
        for name, value in attrs:
            if name in {"aria-label", "title", "placeholder", "alt"} and value:
                self.strings.append((value, self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._verbatim:
            self._verbatim -= 1

    def handle_data(self, data: str) -> None:
        if self._verbatim:
            return
        line = self.getpos()[0]
        text = CONFIG_PAIR.sub("", data)
        for value, offset in quoted_strings(text):
            self.strings.append((value, line + offset - 1))
        prose = SHORTCODE.sub(" ", text)
        if prose.strip():
            self.strings.append((prose, line))


@dataclass(frozen=True)
class Hit:
    """One banned word in one piece of customer copy."""

    surface: str
    source: str
    line: int
    text: str
    term: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.term, normalise(self.text))


def normalise(text: str) -> str:
    """Whitespace-collapsed copy, so a reflow does not read as a new string."""
    return " ".join(text.split())


def term_pattern(term: str) -> re.Pattern[str]:
    """A wordlist term as a regex; a trailing `*` widens it to a prefix.

    German writes its compounds closed, with the head last: the shipping word
    is the second element in "Lagerversand", "Paketversand" and
    "Expressversand". A pattern anchored only at the start sees none of them,
    and the list has carried "Versand*" since its first version while the
    German home said "Lagerversand" three times. The same shape reaches
    "Nachbestellung", "Kundenbestellung", "Teilzahlung", "Vorauszahlung".

    So the four heads below drop the leading anchor and match anywhere inside a
    word. Not a general rule: doing it for "Kasse" would match "Kasserolle",
    "Kassette" and "Kassierer", different words that start with the same
    letters. The heads were chosen by trying them against the shipped copy —
    every string the looser form newly matches is a real compound of the term.
    """
    stem = term.rstrip("*")
    trailing = "" if term.endswith("*") else rf"(?!{_WORD})"
    leading = "" if term in COMPOUND_HEADS else rf"(?<!{_WORD})"
    return re.compile(rf"{leading}{re.escape(stem)}{trailing}", re.IGNORECASE)


COMPOUND_HEADS = ("Versand*", "Bestell*", "Zahlung*", "Warenkorb*")


def load_terms(path: Path = WORDS_PATH) -> list[str]:
    """The wordlist terms, or one loud failure when the one list is gone."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RuntimeError(f"cannot read the commerce wordlist {path}: {error}") from error
    terms = [
        stripped
        for stripped in (line.split("#", 1)[0].strip() for line in lines)
        if stripped
    ]
    if not terms:
        raise RuntimeError(f"the commerce wordlist {path} carries no terms")
    return terms


def matched_terms(text: str, patterns: list[tuple[str, re.Pattern[str]]]) -> list[str]:
    """The wordlist terms this copy contains, in wordlist order.

    Merge fields and printf placeholders are removed first: they render as
    data, and a customer reading "Your inquiry #1042" never sees `order`.
    """
    haystack = MERGE_FIELD.sub(" ", text)
    found: list[str] = []
    for term, pattern in patterns:
        if not pattern.search(haystack):
            continue
        allowance = ALLOWANCES.get(term)
        if allowance is not None:
            # Drop the permitted forms, then ask whether a real one remains.
            if not pattern.search(allowance.sub(" ", haystack)):
                continue
        found.append(term)
    return found


def source_paths(root: Path, roots: tuple[str, ...], suffixes: set[str]) -> list[Path]:
    """Every file of the given suffixes under the roots, minus build output."""
    found: list[Path] = []
    for relative in roots:
        base = root / relative
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in suffixes or not path.is_file():
                continue
            if EXCLUDED_PARTS.intersection(path.relative_to(root).parts):
                continue
            found.append(path)
    return found


def po_messages(path: Path) -> list[tuple[str, str, int]]:
    """(msgid, msgstr, line) of every active entry; header and `#~` skipped.

    Plural entries keep both msgstr[N] branches: each reaches a customer. The
    msgid_plural text is dropped — the singular msgid is what ships in the UI,
    and the German side is covered by the msgstr branches.
    """
    entries: list[tuple[str, str, int]] = []
    msgid: list[str] | None = None
    msgstr: list[str] = []
    target: str | None = None
    start = 0
    obsolete = False
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines() + [""], start=1
    ):
        if line.startswith("#~"):
            obsolete = True
        stripped = line.removeprefix("#~ ")
        if stripped.startswith("msgid "):
            close(entries, msgid, msgstr, start, obsolete)
            msgid = [json.loads(stripped[len("msgid ") :])]
            msgstr = []
            target = "msgid"
            start = number
            obsolete = False
        elif stripped.startswith("msgid_plural "):
            target = None
        elif PLURAL_MSGSTR.match(stripped) or stripped.startswith("msgstr "):
            msgstr.append(json.loads(stripped.split(" ", 1)[1]))
            target = "msgstr"
        elif stripped.startswith('"'):
            if target == "msgstr" and msgstr:
                msgstr[-1] += json.loads(stripped)
            elif target == "msgid" and msgid:
                msgid[-1] += json.loads(stripped)
        elif stripped == "":
            close(entries, msgid, msgstr, start, obsolete)
            msgid = None
            msgstr = []
            target = None
            obsolete = False
    return entries


def close(
    entries: list[tuple[str, str, int]],
    msgid: list[str] | None,
    msgstr: list[str],
    start: int,
    obsolete: bool,
) -> None:
    if msgid is None or obsolete:
        return
    message = "".join(msgid)
    if message == "":
        return  # The catalog header: metadata, not copy.
    entries.append((message, "".join(msgstr), start))


def fragment_strings(content: str) -> list[tuple[str, int]]:
    """The prose of a LiveCanvas export: text nodes and accessible labels."""
    parser = CopyStrings()
    parser.feed(content)
    return parser.strings


def repo_hits(root: Path, terms: list[str]) -> list[Hit]:
    """Every banned word in every customer-visible repository source."""
    patterns = [(term, term_pattern(term)) for term in terms]
    hits: list[Hit] = []

    for path in source_paths(root, CODE_ROOTS, CODE_SUFFIXES):
        relative = str(path.relative_to(root))
        source = path.read_text(encoding="utf-8")
        for value, line in gettext_strings(source, php=path.suffix == ".php"):
            hits.extend(
                Hit("gettext", relative, line, value, term)
                for term in matched_terms(value, patterns)
            )

    for path in source_paths(root, FRAGMENT_ROOTS, {".html"}):
        parts = path.relative_to(root).parts
        if "content" not in parts:
            continue  # A theme or plugin template, not a LiveCanvas export.
        relative = str(path.relative_to(root))
        for value, line in fragment_strings(path.read_text(encoding="utf-8")):
            hits.extend(
                Hit("fragment", relative, line, value, term)
                for term in matched_terms(value, patterns)
            )

    for path in sorted(root.glob(CATALOG_GLOB)):
        relative = str(path.relative_to(root))
        for msgid, msgstr, line in po_messages(path):
            for surface, value in (("po-id", msgid), ("po-str", msgstr)):
                hits.extend(
                    Hit(surface, relative, line, value, term)
                    for term in matched_terms(value, patterns)
                )

    return hits


def wp_run(wp: str, *args: str) -> str:
    """Run one read-only WP-CLI command and return its stdout."""
    result = subprocess.run(
        [wp, *args], check=False, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"wp {' '.join(args[:2])} failed: {result.stderr.strip()}"
        )
    return result.stdout


def live_documents(wp: str) -> list[tuple[str, str, str]]:
    """(post type, slug, content) of the published pages and posts, read-only.

    The bulk listing asks for `post_content` among its fields. Whether a given
    WP-CLI build honours that for this column is not something this gate should
    depend on — a build that silently drops the field would report a clean site
    for copy that is not clean. Any row that comes back without the key is
    fetched with `wp post get <id> --field=post_content`, which is the
    documented, unambiguous path. A row whose content cannot be read raises
    rather than counting as clean.
    """
    rows = json.loads(
        wp_run(
            wp,
            "post",
            "list",
            "--post_type=page,post",
            "--post_status=publish",
            "--fields=ID,post_name,post_type,post_content",
            "--format=json",
            "--posts_per_page=-1",
        )
        or "[]"
    )
    if not isinstance(rows, list):
        raise RuntimeError("wp post list did not return a list")
    documents: list[tuple[str, str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "post_content" in row:
            content = str(row.get("post_content") or "")
        else:
            identifier = row.get("ID")
            if identifier is None:
                raise RuntimeError("wp post list returned a row without ID")
            content = wp_run(
                wp, "post", "get", str(identifier), "--field=post_content"
            ).rstrip("\n")
        documents.append(
            (
                str(row.get("post_type", "")),
                str(row.get("post_name", "")),
                content,
            )
        )
    return documents


def live_hits(documents: list[tuple[str, str, str]], terms: list[str]) -> list[Hit]:
    """Every banned word in published page and post content."""
    patterns = [(term, term_pattern(term)) for term in terms]
    hits: list[Hit] = []
    for post_type, slug, content in documents:
        source = f"db:{post_type}:{slug}"
        for value, line in fragment_strings(content):
            hits.extend(
                Hit("db", source, line, value, term)
                for term in matched_terms(value, patterns)
            )
    return hits


def is_legal(hit: Hit) -> bool:
    """A hit on one of the four protected legal pages."""
    return hit.source.startswith("db:") and hit.source.rsplit(":", 1)[-1] in LEGAL_SLUGS


def load_baseline(path: Path = BASELINE_PATH) -> dict[tuple[str, str, str], dict]:
    """The ratchet's recorded hits, keyed (source, term, normalised string)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError(f"cannot read the baseline {path}: {error}") from error
    files = data.get("files")
    if not isinstance(files, dict):
        raise RuntimeError(f"the baseline {path} has no files object")
    entries: dict[tuple[str, str, str], dict] = {}
    for source, rows in files.items():
        if not isinstance(rows, list):
            raise RuntimeError(f"the baseline {path} entry {source!r} is not a list")
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"the baseline {path} entry {source!r} is not an object")
            missing = {"term", "string"} - set(row)
            if missing:
                raise RuntimeError(
                    f"the baseline {path} entry {source!r} lacks {sorted(missing)}"
                )
            key = (source, str(row["term"]), normalise(str(row["string"])))
            justification = str(row.get("justification", "")).strip()
            if not justification:
                # An exemption with no reason is a silent hole, not a decision.
                raise RuntimeError(
                    f"the baseline {path} entry {source!r} {key[1]!r} has no justification"
                )
            entries[key] = {"count": int(row.get("count", 1)), "why": justification}
    return entries


def apply_baseline(
    hits: list[Hit], baseline: dict[tuple[str, str, str], dict], *, live: bool
) -> tuple[list[str], int]:
    """The findings, and how many hits the baseline already covers.

    Only the baseline entries belonging to the surface that was scanned take
    part. The repository scan reports file paths and the live scan reports
    `db:<post_type>:<slug>`, so the two sets are disjoint; comparing one
    against the other's entries would report every entry as stale and fail a
    clean site's own deploy smoke.
    """
    scoped = {key: entry for key, entry in baseline.items() if key[0].startswith("db:") == live}
    counts: dict[tuple[str, str, str], list[Hit]] = {}
    for hit in hits:
        counts.setdefault(hit.key, []).append(hit)
    findings: list[str] = []
    covered = 0
    for key in sorted(counts):
        rows = counts[key]
        entry = scoped.get(key)
        if entry is None:
            first = rows[0]
            findings.append(
                f"new {key[1]!r} ({first.surface}) {key[0]}:{first.line}: "
                f"{excerpt(key[2], key[1])}"
            )
            continue
        covered += len(rows)
        if len(rows) > entry["count"]:
            findings.append(
                f"grew from {entry['count']} to {len(rows)} {key[1]!r} in "
                f"{key[0]}: {excerpt(key[2], key[1])}"
            )
    for key in sorted(set(scoped) - set(counts)):
        findings.append(
            f"stale baseline entry {key[1]!r} in {key[0]}: {key[2][:60]!r} is gone"
        )
    return findings, covered


def excerpt(text: str, needle: str) -> str:
    """A short piece of the finding around the match."""
    match = re.search(rf"(?<!{_WORD}){re.escape(needle.rstrip('*'))}", text, re.IGNORECASE)
    start = max(0, (match.start() if match else 0) - 24)
    return repr(text[start : start + 64])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commerce vocabulary gate.")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--words", type=Path, default=WORDS_PATH)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument(
        "--wp-cli",
        action="store_true",
        help="scan the published pages and posts of a live site instead",
    )
    parser.add_argument("--wp", default="wp", help="the WP-CLI binary")
    args = parser.parse_args(argv)

    try:
        terms = load_terms(args.words)
        baseline = load_baseline(args.baseline)
        if args.wp_cli:
            hits = live_hits(live_documents(args.wp), terms)
        else:
            hits = repo_hits(args.root, terms)
    except (RuntimeError, OSError, ValueError) as error:
        print(f"commerce-terms: {error}", file=sys.stderr)
        return 1

    legal = [hit for hit in hits if is_legal(hit)]
    findings, covered = apply_baseline(
        [hit for hit in hits if not is_legal(hit)], baseline, live=args.wp_cli
    )

    for finding in findings:
        print(finding)

    if legal:
        print(
            f"commerce-terms: {len(legal)} hit(s) on protected legal pages "
            "(exempt; triage in docs/acceptance/2026-11-04/905/copy-review.md)"
        )
        for hit in sorted(legal, key=lambda item: (item.source, item.line, item.term)):
            print(
                f"  legal {hit.source}:{hit.line} {hit.term!r}: "
                f"{excerpt(hit.text, hit.term)}"
            )

    print(
        f"commerce-terms: hits={len(hits) - len(legal)} baselined={covered} "
        f"legal={len(legal)} findings={len(findings)}"
    )
    if findings:
        print("commerce-terms: FAIL", file=sys.stderr)
        return 1
    print("commerce-terms: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
