#!/usr/bin/env python3
"""Put the two monitoring category archives in SEOPress's XML sitemap, indexable.

Runs against a WordPress through WP-CLI (the pattern of 69-seopress-schema.py):

    python3 tools/migrate/category-sitemap.py --wp "<wp-cli command>" plan
    python3 tools/migrate/category-sitemap.py --wp "<wp-cli command>" apply --write --backup <file>
    python3 tools/migrate/category-sitemap.py --wp "<wp-cli command>" verify [--base https://de-linker.com]

Why the archives are absent today (measured on production, 2026-10-27):

- SEOPress stores its sitemap taxonomy switches in
  `seopress_xml_sitemap_option_name`; `seopress_xml_sitemap_taxonomies_list`
  holds `category => array( 'include' => '' )`, so no category archive is
  written and `/category-sitemap1.xml` answers 404.
- SEOPress stores the taxonomy noindex defaults in
  `seopress_titles_option_name`; `seopress_titles_tax_titles.category.noindex`
  is `'1'`, so every category archive carries `noindex`.

Both are the plugin's own settings, not this repository's code. The plugin
already offers the per-term override this migration uses
(wp-seopress 10.3, read on production):

- `src/Services/Options/TitleOption.php::getTaxNoIndex()` returns `'yes'` when
  the term carries `_seopress_robots_index = yes`, before it reads the
  taxonomy default.
- `inc/functions/sitemap/template-xml-sitemaps.php` counts only terms whose
  `_seopress_robots_index` is absent or not `'yes'`.
- `inc/functions/sitemap/template-xml-sitemaps-single-term.php` drops every
  term whose `_seopress_robots_index` is truthy.

So the change is two SEOPress switches and one per-term rule:

1. `_seopress_robots_index = yes` on every category term that must stay
   noindexed and out of the sitemap: the four retired blog groups in both
   languages (applications-blog, battery-storage-blog,
   installation-commissioning, system-design) and `uncategorized`.
2. The same meta deleted from `monitoring-energy-management` and its German
   twin, so both become indexable.
3. `seopress_titles_tax_titles.category.noindex` cleared, because a term-level
   value can force noindex but cannot force index while the taxonomy default
   is `'1'`.
4. `seopress_xml_sitemap_taxonomies_list.category.include = '1'`, so the
   plugin writes `category-sitemap1.xml` and lists it in `sitemaps.xml`.

The four retired groups keep the state the owner ruled for them: noindex, not
in the sitemap. `uncategorized` keeps its current noindex too. Any other
category term is reported and the write refuses rather than guessing.

Idempotent: a second run plans nothing. `apply` records the previous values in
the `--backup` file and reads every write back before returning.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# WP-CLI's PHP diagnostics, which must not be parsed as the value.
PHP_DIAGNOSTIC = re.compile(
    r"^(PHP (Warning|Notice|Deprecated|Fatal error)|Warning:|Notice:|Deprecated:|Fatal error):"
)

# The category whose English and German archives become indexable and listed.
MONITORING_SLUG = "monitoring-energy-management"

# The four retired blog groups the owner does not want indexed or listed.
EXCLUDED_SLUGS = (
    "applications-blog",
    "battery-storage-blog",
    "installation-commissioning",
    "system-design",
)

# WordPress's default term. It has no posts; it stays noindex like today.
UNCATEGORIZED_SLUG = "uncategorized"

# SEOPress's own names (wp-seopress 10.3).
ROBOTS_INDEX_META = "_seopress_robots_index"
ROBOTS_CANONICAL_META = "_seopress_robots_canonical"
TITLES_OPTION = "seopress_titles_option_name"
SITEMAP_OPTION = "seopress_xml_sitemap_option_name"
TITLES_CATEGORY_PATH = ("seopress_titles_tax_titles", "category")
SITEMAP_CATEGORY_PATH = ("seopress_xml_sitemap_taxonomies_list", "category")

# The sitemap's own term query (template-xml-sitemaps.php): all languages,
# non-empty, and not carrying the noindex meta.
STATE_PHP = f"""
$terms = get_terms( array( 'taxonomy' => 'category', 'hide_empty' => false ) );
$out = array( 'terms' => array(), 'sitemap_ids' => array(), 'options' => array() );
foreach ( $terms as $term ) {{
    $translations = array();
    if ( function_exists( 'pll_get_term_translations' ) ) {{
        foreach ( (array) pll_get_term_translations( $term->term_id ) as $lang => $id ) {{
            $translations[ (string) $lang ] = (int) $id;
        }}
    }}
    $link = get_term_link( $term );
    $out['terms'][] = array(
        'id' => (int) $term->term_id,
        'slug' => (string) $term->slug,
        'name' => (string) $term->name,
        'count' => (int) $term->count,
        'language' => function_exists( 'pll_get_term_language' ) ? (string) pll_get_term_language( $term->term_id ) : '',
        'index' => (string) get_term_meta( $term->term_id, '{ROBOTS_INDEX_META}', true ),
        'canonical' => (string) get_term_meta( $term->term_id, '{ROBOTS_CANONICAL_META}', true ),
        'translations' => $translations,
        'url' => is_string( $link ) ? $link : '',
    );
}}
$sitemap_args = array(
    'taxonomy' => 'category',
    'hide_empty' => true,
    'lang' => '',
    'fields' => 'ids',
    'meta_query' => array(
        'relation' => 'OR',
        array( 'key' => '{ROBOTS_INDEX_META}', 'value' => '', 'compare' => 'NOT EXISTS' ),
        array( 'key' => '{ROBOTS_INDEX_META}', 'value' => 'yes', 'compare' => '!=' ),
    ),
);
$ids = get_terms( $sitemap_args );
$out['sitemap_ids'] = is_array( $ids ) ? array_map( 'intval', $ids ) : array();
$titles = get_option( '{TITLES_OPTION}' );
$sitemap = get_option( '{SITEMAP_OPTION}' );
$titles_category = is_array( $titles ) && isset( $titles['seopress_titles_tax_titles']['category'] ) && is_array( $titles['seopress_titles_tax_titles']['category'] )
    ? $titles['seopress_titles_tax_titles']['category']
    : array();
$sitemap_category = is_array( $sitemap ) && isset( $sitemap['seopress_xml_sitemap_taxonomies_list']['category'] ) && is_array( $sitemap['seopress_xml_sitemap_taxonomies_list']['category'] )
    ? $sitemap['seopress_xml_sitemap_taxonomies_list']['category']
    : array();
$out['options'] = array(
    'category_noindex' => array_key_exists( 'noindex', $titles_category ) ? (string) $titles_category['noindex'] : null,
    'category_include' => array_key_exists( 'include', $sitemap_category ) ? (string) $sitemap_category['include'] : null,
);
echo wp_json_encode( $out );
"""


@dataclass(frozen=True)
class Term:
    """One category term as SEOPress sees it."""

    id: int
    slug: str
    name: str
    count: int
    language: str
    index: str
    canonical: str
    translations: dict[str, int]
    url: str

    @property
    def label(self) -> str:
        """A short identity for reports."""
        return f"{self.id} {self.slug} [{self.language or '?'}]"


@dataclass(frozen=True)
class Options:
    """The two stored switches, as strings; None when the key is absent."""

    category_noindex: str | None
    category_include: str | None


@dataclass(frozen=True)
class State:
    """Everything the plan and the verify read."""

    terms: tuple[Term, ...]
    sitemap_ids: tuple[int, ...]
    options: Options


def clean(output: str) -> str:
    """Drop the phar's own diagnostic lines."""
    return "\n".join(
        line for line in output.splitlines() if not PHP_DIAGNOSTIC.match(line)
    )


def run(prefix: list[str], *args: str) -> str:
    """Run one WP-CLI command. A failing command stops the script."""
    result = subprocess.run(
        [*prefix, *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise SystemExit(
            f"wp {' '.join(args[:4])} failed (exit {result.returncode}):\n"
            f"{result.stderr.strip()}"
        )
    return clean(result.stdout)


def transport_of(prefix: list[str]) -> list[str]:
    """The ssh part of a remote WP-CLI prefix, or nothing for a local one."""
    if not prefix or prefix[0] != "ssh":
        return []
    for index, part in enumerate(prefix):
        if part == "wp" or part.endswith("/wp"):
            return prefix[:index]
    raise SystemExit(f"no wp binary in the remote command: {' '.join(prefix)}")


def php(prefix: list[str], code: str) -> str:
    """Run PHP through `wp eval-file`, so no shell ever parses it.

    The command prefix may be `ssh host /usr/local/bin/wp --path=…`, whose
    remote shell would expand `$` and reject parentheses in an `eval` argument.
    A file has neither problem. A remote prefix receives the file through its
    ssh transport; a local prefix gets a local temp file.
    """
    with tempfile.NamedTemporaryFile(
        "w", suffix=".php", prefix="category-sitemap-", delete=False
    ) as handle:
        handle.write("<?php " + code)
        local = Path(handle.name)
    transport = transport_of(prefix)
    try:
        if transport:
            remote = f"/tmp/{local.name}"
            with local.open() as stream:
                sent = subprocess.run(
                    [*transport, f"cat > {shlex.quote(remote)}"],
                    stdin=stream,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            if sent.returncode != 0:
                raise SystemExit(
                    f"copying the eval file failed (exit {sent.returncode}):\n"
                    f"{sent.stderr.strip()}"
                )
            try:
                return run(prefix, "eval-file", remote)
            finally:
                subprocess.run(
                    [*transport, f"rm -f {shlex.quote(remote)}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
        return run(prefix, "eval-file", str(local))
    finally:
        local.unlink(missing_ok=True)


def term_from_json(raw: Any) -> Term:
    """One term out of `wp eval` JSON."""
    if not isinstance(raw, dict):
        raise SystemExit(f"not a term: {raw!r}")
    translations_raw = raw.get("translations")
    translations: dict[str, int] = {}
    if isinstance(translations_raw, dict):
        for language, term_id in translations_raw.items():
            if isinstance(language, str) and isinstance(term_id, int):
                translations[language] = term_id
    return Term(
        id=int(raw["id"]),
        slug=str(raw["slug"]),
        name=str(raw["name"]),
        count=int(raw["count"]),
        language=str(raw["language"]),
        index=str(raw["index"]),
        canonical=str(raw["canonical"]),
        translations=translations,
        url=str(raw["url"]),
    )


def read_state(prefix: list[str]) -> State:
    """The category terms and the two SEOPress switches, read in one process."""
    raw = php(prefix, STATE_PHP)
    start = raw.find("{")
    if start < 0:
        raise SystemExit(f"no state in wp eval output:\n{raw[:400]}")
    data = json.loads(raw[start:])
    if not isinstance(data, dict) or not isinstance(data.get("terms"), list):
        raise SystemExit("wp eval did not return a state object")
    options_raw = data.get("options")
    if not isinstance(options_raw, dict):
        raise SystemExit("wp eval returned no options object")

    def string_or_none(key: str) -> str | None:
        value = options_raw.get(key)
        return value if isinstance(value, str) else None

    ids_raw = data.get("sitemap_ids")
    ids = tuple(int(value) for value in ids_raw) if isinstance(ids_raw, list) else ()
    return State(
        terms=tuple(term_from_json(term) for term in data["terms"]),
        sitemap_ids=ids,
        options=Options(
            category_noindex=string_or_none("category_noindex"),
            category_include=string_or_none("category_include"),
        ),
    )


def monitoring_pair(terms: tuple[Term, ...]) -> tuple[Term, Term]:
    """The English monitoring category and its German twin."""
    source = next(
        (
            term
            for term in terms
            if term.slug == MONITORING_SLUG and term.language == "en"
        ),
        None,
    )
    if source is None:
        source = next((term for term in terms if term.slug == MONITORING_SLUG), None)
    if source is None:
        raise SystemExit(f"no category {MONITORING_SLUG!r}")
    twin_id = source.translations.get("de")
    twin = next((term for term in terms if term.id == twin_id), None)
    if twin is None or twin.language != "de":
        raise SystemExit(
            f"no German translation of {MONITORING_SLUG!r} (de id {twin_id!r})"
        )
    return source, twin


def excluded_terms(terms: tuple[Term, ...]) -> list[Term]:
    """The four retired blog groups in both languages, plus `uncategorized`."""
    out: list[Term] = []
    seen: set[int] = set()
    for slug in EXCLUDED_SLUGS:
        source = next(
            (term for term in terms if term.slug == slug and term.language == "en"),
            None,
        )
        if source is None:
            source = next((term for term in terms if term.slug == slug), None)
        if source is None:
            raise SystemExit(f"no category {slug!r}")
        if source.id not in seen:
            seen.add(source.id)
            out.append(source)
        twin_id = source.translations.get("de")
        twin = next((term for term in terms if term.id == twin_id), None)
        if twin is None:
            raise SystemExit(f"no German translation of category {slug!r}")
        if twin.id not in seen:
            seen.add(twin.id)
            out.append(twin)
    uncategorized = next(
        (term for term in terms if term.slug == UNCATEGORIZED_SLUG), None
    )
    if uncategorized is not None and uncategorized.id not in seen:
        out.append(uncategorized)
    return out


def plan(state: State) -> tuple[list[dict[str, Any]], list[Term]]:
    """The writes, and any category term this migration does not know."""
    keep_source, keep_twin = monitoring_pair(state.terms)
    keep = {keep_source.id, keep_twin.id}
    noindex = excluded_terms(state.terms)
    known = keep | {term.id for term in noindex}
    unknown = [term for term in state.terms if term.id not in known]

    actions: list[dict[str, Any]] = []
    for term in noindex:
        if term.index != "yes":
            actions.append(
                {
                    "kind": "term",
                    "id": term.id,
                    "slug": term.slug,
                    "language": term.language,
                    "from": term.index,
                    "to": "yes",
                }
            )
    for term in (keep_source, keep_twin):
        if term.index != "":
            actions.append(
                {
                    "kind": "term",
                    "id": term.id,
                    "slug": term.slug,
                    "language": term.language,
                    "from": term.index,
                    "to": "",
                }
            )
    if state.options.category_noindex != "":
        actions.append(
            {
                "kind": "option",
                "name": "titles-noindex",
                "from": state.options.category_noindex,
                "to": "",
            }
        )
    if state.options.category_include != "1":
        actions.append(
            {
                "kind": "option",
                "name": "sitemap-include",
                "from": state.options.category_include,
                "to": "1",
            }
        )
    return actions, unknown


def refuse_unknown(unknown: list[Term]) -> None:
    """A category this migration has no ruling for stops the write."""
    if not unknown:
        return
    listed = ", ".join(term.label for term in unknown)
    raise SystemExit(
        f"unclassified category term(s): {listed}. Nothing is written; decide "
        "whether each one is indexable and whether it belongs in the sitemap, "
        "then extend this migration."
    )


def report(state: State, actions: list[dict[str, Any]], unknown: list[Term]) -> None:
    """Print the plan in the operator's words."""
    keep_source, keep_twin = monitoring_pair(state.terms)
    print("indexable and in the sitemap:")
    for term in (keep_source, keep_twin):
        print(f"  KEEP  {term.label} count={term.count} {term.url}")
    print("noindex and out of the sitemap:")
    for term in excluded_terms(state.terms):
        print(f"  NOINDEX {term.label} count={term.count}")
    if unknown:
        print("unclassified:")
        for term in unknown:
            print(f"  UNKNOWN {term.label} count={term.count}")
    if not actions:
        print("nothing to do: every switch and term already matches")
        return
    print(f"{len(actions)} write(s):")
    for action in actions:
        if action["kind"] == "term":
            what = (
                "set _seopress_robots_index=yes"
                if action["to"] == "yes"
                else "delete _seopress_robots_index"
            )
            print(
                f"  {action['id']} {action['slug']} [{action['language']}]: "
                f"{what} (was {action['from']!r})"
            )
        else:
            print(f"  {action['name']}: {action['from']!r} -> {action['to']!r}")


def backup(state: State, actions: list[dict[str, Any]], path: Path) -> None:
    """Record the values this run replaces, before it replaces them."""
    touched = {int(action["id"]) for action in actions if action["kind"] == "term"}
    data = {
        "taken_at": datetime.now(UTC).isoformat(),
        "options": {
            f"{TITLES_OPTION}.seopress_titles_tax_titles.category.noindex": (
                state.options.category_noindex
            ),
            f"{SITEMAP_OPTION}.seopress_xml_sitemap_taxonomies_list.category.include": (
                state.options.category_include
            ),
        },
        "term_meta": {
            str(term.id): {
                "slug": term.slug,
                "language": term.language,
                ROBOTS_INDEX_META: term.index,
            }
            for term in state.terms
            if term.id in touched
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"backup written to {path}")


def apply_actions(prefix: list[str], actions: list[dict[str, Any]]) -> None:
    """Write the plan through WordPress's own APIs, then read it back."""
    statements: list[str] = []
    for action in actions:
        if action["kind"] == "term":
            if action["to"] == "yes":
                statements.append(
                    f"update_term_meta({int(action['id'])},'{ROBOTS_INDEX_META}','yes');"
                )
            else:
                statements.append(
                    f"delete_term_meta({int(action['id'])},'{ROBOTS_INDEX_META}');"
                )
            continue
        if action["name"] == "titles-noindex":
            statements.append(
                f"$o=get_option('{TITLES_OPTION}');"
                "if(!is_array($o)){$o=array();}"
                "if(!isset($o['seopress_titles_tax_titles']['category'])||"
                "!is_array($o['seopress_titles_tax_titles']['category'])){"
                "$o['seopress_titles_tax_titles']['category']=array();}"
                "$o['seopress_titles_tax_titles']['category']['noindex']='';"
                f"update_option('{TITLES_OPTION}',$o);"
            )
            continue
        if action["name"] == "sitemap-include":
            statements.append(
                f"$o=get_option('{SITEMAP_OPTION}');"
                "if(!is_array($o)){$o=array();}"
                "if(!isset($o['seopress_xml_sitemap_taxonomies_list']['category'])||"
                "!is_array($o['seopress_xml_sitemap_taxonomies_list']['category'])){"
                "$o['seopress_xml_sitemap_taxonomies_list']['category']=array();}"
                "$o['seopress_xml_sitemap_taxonomies_list']['category']['include']='1';"
                f"update_option('{SITEMAP_OPTION}',$o);"
            )
            continue
        raise SystemExit(f"unknown action: {action!r}")
    php(prefix, "".join(statements))


def verify_state(state: State) -> list[str]:
    """Every check the database alone can make."""
    problems: list[str] = []
    keep_source, keep_twin = monitoring_pair(state.terms)
    keep = {keep_source.id, keep_twin.id}

    if state.options.category_noindex != "":
        problems.append(
            "seopress_titles_tax_titles.category.noindex is "
            f"{state.options.category_noindex!r}, not ''"
        )
    if state.options.category_include != "1":
        problems.append(
            "seopress_xml_sitemap_taxonomies_list.category.include is "
            f"{state.options.category_include!r}, not '1'"
        )
    for term in (keep_source, keep_twin):
        if term.index:
            problems.append(f"{term.label} still carries robots index {term.index!r}")
    for term in excluded_terms(state.terms):
        if term.index != "yes":
            problems.append(
                f"{term.label} is not noindexed (robots index {term.index!r})"
            )

    listed = set(state.sitemap_ids)
    if listed != keep:
        problems.append(
            f"the sitemap term query returns {sorted(listed)}, expected {sorted(keep)}"
        )
    return problems


def fetch(url: str) -> str:
    """One public GET, as text."""
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            body: bytes = response.read()
            return body.decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as error:
        raise SystemExit(f"GET {url} failed: {error}") from error


def verify_http(base: str, state: State) -> list[str]:
    """What the public sitemap files say, after the write."""
    problems: list[str] = []
    root = base.rstrip("/")
    index = fetch(f"{root}/sitemaps.xml")
    if "category-sitemap1.xml" not in index:
        problems.append(f"{root}/sitemaps.xml does not list category-sitemap1.xml")
    sitemap = fetch(f"{root}/category-sitemap1.xml")
    locs = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
    keep_source, keep_twin = monitoring_pair(state.terms)
    for term in (keep_source, keep_twin):
        if term.url not in locs:
            problems.append(f"{term.url} is not in {root}/category-sitemap1.xml")
    for term in excluded_terms(state.terms):
        if term.url in locs:
            problems.append(f"{term.url} is in {root}/category-sitemap1.xml")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--wp", required=True, help="WP-CLI command of the site")
    parser.add_argument("command", choices=("plan", "apply", "verify"))
    parser.add_argument("--write", action="store_true", help="required by apply")
    parser.add_argument(
        "--backup", type=Path, help="where apply writes the previous values"
    )
    parser.add_argument(
        "--base",
        help="site root for the HTTP readback, e.g. https://de-linker.com",
    )
    args = parser.parse_args(argv)

    prefix = shlex.split(args.wp)
    state = read_state(prefix)
    actions, unknown = plan(state)
    report(state, actions, unknown)

    if args.command == "plan":
        refuse_unknown(unknown)
        return 0
    if args.command == "apply":
        refuse_unknown(unknown)
        if not args.write:
            raise SystemExit("apply refuses to write without --write")
        if args.backup is None:
            raise SystemExit("apply requires --backup <file>")
        backup(state, actions, args.backup)
        if not actions:
            print("nothing to write")
            return 0
        apply_actions(prefix, actions)
        problems = verify_state(read_state(prefix))
        if problems:
            raise SystemExit("readback failed:\n- " + "\n- ".join(problems))
        print("readback: every switch and term matches the plan")
        return 0

    problems = verify_state(state)
    if args.base:
        problems.extend(verify_http(args.base, state))
    if problems:
        print("FAIL")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
