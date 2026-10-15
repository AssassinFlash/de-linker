#!/usr/bin/env python3
"""#9 migration: the old linker-i18n's German becomes German versions under Polylang.

Runs against a WordPress through WP-CLI, locally or over SSH:

    python3 tools/migrate/9-i18n.py --wp ~/de-linker-local/t9/wp.sh --user local-admin plan
    python3 tools/migrate/9-i18n.py --wp ~/de-linker-local/t9/wp.sh --user local-admin apply --write
    python3 tools/migrate/9-i18n.py --wp ~/de-linker-local/t9/wp.sh verify --urls de-sitemap.json
    python3 tools/migrate/9-i18n.py --wp "ssh hostinger-de-linker /usr/local/bin/wp --path=..." ...

The steps (docs/specs/9-i18n.md, "迁移"):

1. Polylang configured by `wp linker-i18n setup` (the plugin's own
   configuration), and every existing object without a language made English.
   Creating the German language makes Polylang create German default terms
   ("Uncategorized", slug uncategorized-de, for every taxonomy with a
   default_<taxonomy> option: category, product_cat); setup deletes the empty
   ones right away - their archives are not among the site's German URLs.
2. German product categories, post categories and attribute terms: names and
   slugs from the old plugin's data (below), descriptions from its dictionary.
3. German pages, posts, products and LiveCanvas partials and templates from
   the `_linker_de_*` meta, with the German slugs of the old slug map (pages
   and posts; products keep their slug) and the German SEO title and
   description from the dictionary.
4. Links in the German content rewritten to German pages (`wp linker-i18n relink`).
5. `verify`: the German URLs of the old sitemap answer 200 with German HTML.

Fields with English and no German are left to the translator: those objects
are pending and the plugin translates them once DEEPSEEK_API_KEY is set
(`wp linker-i18n translate --pending`). Nothing old is deleted: the
`_linker_de_*` meta, the slug map and the dictionary stay where they are.

Rollback (`rollback --write`): the German versions become drafts; deactivating
Polylang and restoring the old plugin is the cutover's (#17) next step.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

# German names and slugs of the product categories, as the old plugin serves
# them: its data/taxonomy-de.json and data/shelf-slugs-de.json (linker-i18n
# 0.5.78), checked against the live German category pages on 2026-10-09
# (plugins/linker-i18n/tests/fixtures/live/product-categories.json). These
# files leave with the old plugin at the cutover, so the values live here.
PRODUCT_CATEGORIES: dict[str, tuple[str, str]] = {
    "inverters": ("Wechselrichter", "wechselrichter"),
    "home-storage": ("Heimspeicher", "heimspeicher"),
    "commercial-storage": ("Gewerbespeicher", "gewerbespeicher"),
    "all-in-one-systems": ("All-in-One-Systeme", "all-in-one-systeme"),
    "battery-systems": ("Batteriesysteme", "batteriesysteme"),
    "ems-monitoring": ("EMS & Monitoring", "ems-monitoring"),
    "ev-chargers": ("Ladestationen", "ladestationen"),
    "accessories": ("Zubehör", "zubehoer"),
    "meters-current-transformers": (
        "Energiezähler & Stromwandler",
        "energiezaehler-stromwandler",
    ),
    "backup-power": ("Notstrom", "notstrom"),
}

# Post category names from the same taxonomy-de.json, and the slug the live
# German archive actually answers on. Measured 2026-10-13 (docs/debt/
# DE-PARITY-2026-10-13.md §4.1): /de/category/system-design/ is 200 de-DE,
# titled Systemauslegung; /de/category/systemauslegung/ is 404. The other four
# live German archives are the same English slugs (applications-blog,
# battery-storage-blog, installation-commissioning,
# monitoring-energy-management). Sharing the English slug is allowed once the
# term has its language (SameSlug\TermSlugs; product category ems-monitoring
# already does this). The earlier "no German archive URL, slug follows the
# German name" note was wrong: it minted systemauslegung, and Polylang then
# 301'd /de/category/system-design/ back to the English term. Named
# POST_CATEGORY_NAMES to stay distinct from Twins::POST_CATEGORIES (the
# snapshot's post→term ids in plugins/linker-i18n/includes/Twins.php).
POST_CATEGORY_NAMES: dict[str, tuple[str, str]] = {
    "System Design": ("Systemauslegung", "system-design"),
    "Battery Storage": ("Batteriespeicher", "battery-storage-blog"),
    "Installation & Commissioning": (
        "Installation & Inbetriebnahme",
        "installation-commissioning",
    ),
    "Monitoring & Energy Management": (
        "Überwachung & Energiemanagement",
        "monitoring-energy-management",
    ),
    "Applications": ("Anwendungen", "applications-blog"),
}

# Attribute values have no German on the live site (it shows the old payload,
# not the attributes). Decided here from the words the live German pages use
# for the same things (einphasig, dreiphasig, Hochvolt, Gewerbe, Wohngebäude;
# tests/fixtures/live, 2026-10-09).
ATTRIBUTE_TERMS: dict[str, str] = {
    "Single-phase": "Einphasig",
    "Three-phase": "Dreiphasig",
    "High Voltage": "Hochvolt",
    "Low Voltage": "Niedervolt",
    "Home": "Wohngebäude",
    "Commercial": "Gewerbe",
    "Commercial & Industrial": "Gewerbe & Industrie",
}

# The old plugin's fixed German page segments (data/slug-bases-de.json), used
# for a page slug its slug map does not hold. The product, category and shop
# segments are the new plugin's (UrlSegments).
PAGE_BASES: dict[str, str] = {
    "cart": "warenkorb",
    "proforma-request": "proforma-anfrage",
    "my-account": "mein-konto",
    "application": "anwendung",
    "solution": "loesung",
    "services": "leistungen",
    "about": "ueber-uns",
    "contact": "kontakt",
    "request-a-project": "projekt-anfragen",
    "products": "produkte",
}

# Content types the migration translates. lc_partial and lc_dynamic_template
# are NOT here on purpose: their German twins are owned by the repository's
# presentation channel (`present`), and this script writing their post_content
# made it the second writer — on 2026-10-15 it overwrote the freshly deployed
# German header, footer and page-type templates with the old site's payload
# (issue #182). Pairing of those objects is `linker-i18n repair-partials`' job.
TRANSLATED_TYPES = ("page", "post", "product")
# What the old German sitemap lists (/de-sitemap.xml: pages, posts, products, product categories).
SITEMAP_KINDS = ("page", "post", "product", "product_cat")
PRODUCT_TAXONOMIES = ("product_cat",)
ATTRIBUTE_TAXONOMIES = (
    "pa_phase",
    "pa_battery-voltage",
    "pa_application",
    "pa_product-family",
    "pa_installation-type",
    "pa_monitoring-communication",
)
SEO_KEYS = ("_seopress_titles_title", "_seopress_titles_desc")
LEGACY_KEYS = ("_linker_de_title", "_linker_de_content", "_linker_de_excerpt")

# A PHP diagnostic the WP-CLI phar printed into stdout: a severity word, a
# message, a source file and a line number. Data lines never have this shape:
# query output is tab-separated base64, JSON is one blob.
PHP_DIAGNOSTIC = re.compile(
    r"^(?:PHP )?(?:Deprecated|Warning|Notice|Fatal error|Parse error): "
    r".+ in .+ on line \d+$"
)


class WP:
    """WP-CLI, as a command prefix."""

    def __init__(self, command: str, user: str | None) -> None:
        self.prefix = shlex.split(command)
        self.user = user

    def run(self, *args: str, stdin: str | None = None, as_user: bool = False) -> str:
        """Run one command; as_user signs it in as the administrator, because the
        plugin's commands check manage_options and refuse without a user.

        A prefix that starts with `ssh` is remote, and its arguments travel
        quoted as one word: ssh joins its argv with spaces and the login shell
        splits again, so a SQL statement would break apart (measured
        2026-10-14, against the production host: the category lookup died on
        "Too many positional arguments"). A local prefix keeps argv semantics.
        """
        tail = list(args)
        if as_user and self.user:
            tail.append(f"--user={self.user}")
        if self.prefix and self.prefix[0] == "ssh":
            command = [
                *self.prefix[:-1],
                " ".join([self.prefix[-1], *(shlex.quote(arg) for arg in tail)]),
            ]
        else:
            command = [*self.prefix, *tail]
        result = subprocess.run(
            command, input=stdin, capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            raise SystemExit(
                f"wp {' '.join(args[:3])} failed:\n{result.stderr.strip()}"
            )
        # PHP prints deprecations of the WP-CLI phar's own vendors to stdout
        # (react/promise on this machine's wp-cli 2.12 since 2026-10-10),
        # ahead of the value; every reader here treats stdout as data, so the
        # diagnostic lines - "Deprecated: … in phar://… on line N" - go.
        lines = result.stdout.splitlines()
        return "\n".join(line for line in lines if not PHP_DIAGNOSTIC.match(line))

    def json(self, *args: str, stdin: str | None = None, as_user: bool = False) -> Any:
        out = self.run(*args, stdin=stdin, as_user=as_user)
        start = min((i for i in (out.find("["), out.find("{")) if i >= 0), default=-1)
        return json.loads(out[start:]) if start >= 0 else None

    def query(self, sql: str) -> list[list[str]]:
        """Rows of a SELECT; values that may hold any byte come back base64-encoded by the query.

        No REPLACE() in the SQL: WP-CLI takes a query with that word for a write
        and prints the affected rows instead of the result.
        """
        out = self.run("db", "query", sql, "--skip-column-names", "--batch")
        return [line.split("\t") for line in out.splitlines() if line.strip()]


def b64(value: str) -> str:
    """A TO_BASE64() value: MySQL breaks it every 76 characters, which batch output shows as a literal \\n."""
    value = value.replace("\\n", "").strip()
    return base64.b64decode(value).decode("utf-8") if value not in ("", "NULL") else ""


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


class Migration:
    def __init__(self, wp: WP) -> None:
        self.wp = wp
        self.prefix = wp.run("db", "prefix").strip()

    # Step 1.
    def configure(self) -> None:
        print(self.wp.run("linker-i18n", "setup", "--assign", as_user=True).strip())

    # Sources.
    def legacy_meta(self) -> dict[int, dict[str, str]]:
        keys = ", ".join(sql_string(key) for key in LEGACY_KEYS + SEO_KEYS)
        rows = self.wp.query(
            f"SELECT post_id, meta_key, TO_BASE64(meta_value) FROM {self.prefix}postmeta WHERE meta_key IN ({keys})"
        )
        meta: dict[int, dict[str, str]] = {}
        for post_id, key, value in rows:
            meta.setdefault(int(post_id), {})[key] = b64(value)
        return meta

    def dictionary(self, sources: set[str]) -> dict[str, str]:
        """German for English strings from the old dictionary table (a person's row first), then its chrome map."""
        found: dict[str, str] = {}
        wanted = {s for s in sources if s.strip()}
        if not wanted:
            return found
        tables = self.wp.query(f"SHOW TABLES LIKE '{self.prefix}linker_string'")
        if tables:
            shas = {hashlib.sha1(s.encode("utf-8")).hexdigest(): s for s in wanted}
            in_list = ", ".join(sql_string(sha) for sha in shas)
            rows = self.wp.query(
                f"SELECT source_sha, status, TO_BASE64(target) FROM {self.prefix}linker_string WHERE source_sha IN ({in_list}) ORDER BY status ASC"
            )
            for (
                sha,
                _status,
                target,
            ) in rows:  # ascending status: a person's row (2) is read last and wins
                if b64(target).strip():
                    found[shas[sha]] = b64(target)
        chrome = self.option("linker_i18n_chrome_map")
        if isinstance(chrome, dict):
            for source in wanted - set(found):
                if isinstance(chrome.get(source), str) and chrome[source].strip():
                    found[source] = chrome[source]
        return found

    def option(self, name: str) -> Any:
        out = (
            self.wp.run("option", "get", name, "--format=json")
            if self.option_exists(name)
            else ""
        )
        return json.loads(out) if out.strip() else None

    def option_exists(self, name: str) -> bool:
        return bool(
            self.wp.query(
                f"SELECT option_id FROM {self.prefix}options WHERE option_name = {sql_string(name)}"
            )
        )

    def status(self) -> list[dict[str, Any]]:
        rows = self.wp.json("linker-i18n", "status", "--format=json")
        return rows if isinstance(rows, list) else []

    # Steps 2 and 3: the plan.
    def plan(self) -> list[dict[str, Any]]:
        # Every object of a translated type except the German versions a
        # previous run made: the plan does not depend on languages being set.
        # A post category is the exception. Its German term is planned again
        # even when it already exists: the first run minted a slug from the
        # German name (systemauslegung) and copied the post relationships only
        # while the term was new, so a re-run has to rename the term to the
        # live German archive slug and put the posts back. import updates an
        # existing twin instead of minting another.
        german_ids = {
            (row["kind"], int(row["german"]))
            for row in self.status()
            if row["german"] and row["kind"] != "category"
        }
        term_data: dict[int, dict[str, Any]] = {}
        terms: list[dict[str, Any]] = []
        for taxonomy in PRODUCT_TAXONOMIES + ("category",) + ATTRIBUTE_TAXONOMIES:
            if not self.wp.query(
                f"SELECT term_id FROM {self.prefix}term_taxonomy WHERE taxonomy = {sql_string(taxonomy)} LIMIT 1"
            ):
                continue
            for term in (
                self.wp.json(
                    "term",
                    "list",
                    taxonomy,
                    "--fields=term_id,name,slug,description,parent",
                    "--format=json",
                )
                or []
            ):
                if (taxonomy, int(term["term_id"])) not in german_ids:
                    term_data[int(term["term_id"])] = term
                    terms.append({"kind": taxonomy, "source": int(term["term_id"])})
        post_data = {
            int(p["ID"]): p
            for p in self.wp.json(
                "post",
                "list",
                "--post_type=" + ",".join(TRANSLATED_TYPES),
                "--post_status=any",
                "--fields=ID,post_type,post_name,post_parent",
                "--format=json",
            )
            or []
        }
        posts = [
            {"kind": post["post_type"], "source": post_id}
            for post_id, post in post_data.items()
            if (post["post_type"], post_id) not in german_ids
        ]
        meta = self.legacy_meta()
        wanted = {
            term_data[int(row["source"])]["description"]
            for row in terms
            if int(row["source"]) in term_data
        }
        for row in posts:
            wanted.update(
                meta.get(int(row["source"]), {}).get(key, "") for key in SEO_KEYS
            )
        german = self.dictionary({w for w in wanted if w})
        slug_map = self.option("linker_i18n_slug_map")
        slug_map = slug_map if isinstance(slug_map, dict) else {}

        items: list[dict[str, Any]] = []
        for row in sorted(
            terms,
            key=lambda r: (
                r["kind"],
                int(term_data.get(int(r["source"]), {}).get("parent", 0)) != 0,
            ),
        ):
            term = term_data.get(int(row["source"]))
            if not term:
                continue
            name = html_unescape(term["name"])
            if row["kind"] == "product_cat" and term["slug"] in PRODUCT_CATEGORIES:
                de_name, de_slug = PRODUCT_CATEGORIES[term["slug"]]
            elif row["kind"] == "category" and name in POST_CATEGORY_NAMES:
                de_name, de_slug = POST_CATEGORY_NAMES[name]
            elif row["kind"] in ATTRIBUTE_TAXONOMIES and name in ATTRIBUTE_TERMS:
                de_name, de_slug = ATTRIBUTE_TERMS[name], ""
            else:
                continue  # no German known: the translator makes it when the term is saved or translated
            term_fields = {"name": de_name}
            if term["description"].strip() and term["description"] in german:
                term_fields["description"] = german[term["description"]]
            items.append(
                {
                    "kind": "term",
                    "source": int(row["source"]),
                    "slug": de_slug,
                    "fields": term_fields,
                    "label": f"{row['kind']}:{term['slug']}",
                }
            )

        def depth(post_id: int) -> int:
            level = 0
            while post_data.get(post_id, {}).get("post_parent") and level < 20:
                post_id = int(post_data[post_id]["post_parent"])
                level += 1
            return level

        for row in sorted(posts, key=lambda r: depth(int(r["source"]))):
            source = int(row["source"])
            legacy = meta.get(source, {})
            if not any(legacy.get(key, "").strip() for key in LEGACY_KEYS):
                continue
            post = post_data.get(source, {})
            fields: dict[str, str] = {}
            for key, field in (
                ("_linker_de_title", "post_title"),
                ("_linker_de_content", "post_content"),
                ("_linker_de_excerpt", "post_excerpt"),
            ):
                if legacy.get(key, "").strip():
                    fields[field] = legacy[key]
            for key in SEO_KEYS:
                english = legacy.get(key, "")
                if english.strip() and english in german:
                    fields["meta:" + key] = german[english]
            slug = ""
            if row["kind"] in ("page", "post"):
                english_slug = post.get("post_name", "")
                # PAGE_BASES first: the old plugin served the curated bases of
                # its data/slug-bases-de.json (about -> ueber-uns, solution ->
                # loesung; live /de/ueber-uns/ and /de/loesung/ answer 200,
                # the minted map's /de/anwendung/ 301s to /de/loesung/), and
                # the minted slug_map alone is only the fallback routing.
                slug = (
                    PAGE_BASES.get(english_slug)
                    or slug_map.get(english_slug)
                    or english_slug
                )
            items.append(
                {
                    "kind": "post",
                    "source": source,
                    "slug": slug,
                    "fields": fields,
                    "label": f"{row['kind']}:{post.get('post_name', '')}",
                }
            )
        return items

    # Steps 2–4.
    def apply(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        # The LiveCanvas partial pairs first: an instance imported before
        # Twins ensured the source's language has them unpaired or
        # mislabelled, and import finds an existing German version through
        # the translation group only - repairing after import would mint
        # duplicates instead of updating the twins.
        print(self.wp.run("linker-i18n", "repair-partials", as_user=True).strip())
        # 20 per batch: the small batches of the research's walkthrough
        # (docs/research/2026-10-09/i18n-opensource-replication.md §8.2) - one
        # JSON payload through WP-CLI's stdin stays small and a failed batch is
        # re-runnable, since import is idempotent by English object.
        for start in range(0, len(items), 20):
            batch = [
                {key: value for key, value in item.items() if key != "label"}
                for item in items[start : start + 20]
            ]
            out = self.wp.json(
                "linker-i18n",
                "import",
                "--input=-",
                "--format=json",
                stdin=json.dumps(batch, ensure_ascii=False),
                as_user=True,
            )
            results += out if isinstance(out, list) else []
            print(f"imported {min(start + 20, len(items))}/{len(items)}", flush=True)
        # After the posts exist. The category copy during import finds nothing
        # when the English relationships are already gone, and the insert of a
        # German post clears them (see Twins::post()). This write uses the
        # snapshot's post→term list, not the rows in the database.
        print(
            self.wp.run("linker-i18n", "repair-post-categories", as_user=True).strip()
        )
        print(self.wp.run("linker-i18n", "relink").strip())
        return results

    def rollback(self) -> None:
        german = [
            row["german"]
            for row in self.status()
            if row["kind"] in TRANSLATED_TYPES and row["german"]
        ]
        # 50 per `wp post update` call: one command line of ids stays short;
        # the size carries no guarantee (unlike apply's 20), it only keeps the
        # invocation readable in the cutover log.
        for start in range(0, len(german), 50):
            self.wp.run(
                "post",
                "update",
                *german[start : start + 50],
                "--post_status=draft",
                as_user=True,
            )
        print(f"{len(german)} German posts are drafts now")

    # Step 5.
    def verify(self, urls: list[str], require_all: bool) -> bool:
        """The old German URLs answer in German.

        With require_all every listed URL must; otherwise (a subset of the site,
        such as the test fixture) every German page, post, product and product
        category must have a listed URL that does. A redirect counts when it
        stays on the site in German (WooCommerce sends an empty checkout to the
        cart); it is reported as one.
        """
        home = self.wp.run("option", "get", "home").strip().rstrip("/")
        listed = {re.sub(r"^https?://[^/]+", "", url) for url in urls}
        # The status query (a full walk of the translation groups) is needed
        # only to check the German objects against a subset of the site; with
        # require_all the listed URLs alone decide, and the walk - tens of
        # seconds of WP-CLI under the shared Redis's load - is skipped.
        german = (
            {
                re.sub(r"^https?://[^/]+", "", row["url"]): row
                for row in self.status()
                if row["german"] and row["url"] and row["kind"] in SITEMAP_KINDS
            }
            if not require_all
            else {}
        )
        ok = True
        checked = sorted(listed) if require_all else sorted(german)
        for path in checked:
            code, lang, final = fetch(home + path, home)
            fine = (
                code == 200
                and lang.startswith("de")
                and (require_all or path in listed)
            )
            note = "" if final == path else f" -> {final}"
            if not require_all and path not in listed:
                note += "  (not one of the old German URLs)"
            print(f"{'ok ' if fine else 'BAD'} {code} lang={lang or '-'} {path}{note}")
            ok = ok and fine
        if not require_all:
            print(
                f"{len(german)} German pages, posts, products and categories; {len(listed & set(german))} of the {len(listed)} listed URLs are theirs"
            )
        return ok


def html_unescape(text: str) -> str:
    return html.unescape(text)


def fetch(url: str, home: str) -> tuple[int, str, str]:
    """Status and html lang of a page, following redirects that stay on the site; and the path it ended on."""
    for _ in range(5):
        request = urllib.request.Request(
            url, headers={"User-Agent": "linker-migrate-9"}
        )
        try:
            with urllib.request.build_opener(NoRedirect).open(
                request, timeout=60
            ) as response:
                body = response.read().decode("utf-8", "replace")
                match = re.search(r"<html[^>]*\slang=\"([^\"]+)\"", body)
                return (
                    response.status,
                    match.group(1) if match else "",
                    url[len(home) :],
                )
        except urllib.error.HTTPError as error:
            target = error.headers.get("Location", "")
            if error.code in (301, 302, 307, 308) and target.startswith(home):
                url = target
                continue
            return error.code, "", url[len(home) :]
    return 310, "", url[len(home) :]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--wp", required=True, help="WP-CLI command prefix, e.g. 'ssh host wp --path=…'"
    )
    parser.add_argument(
        "--user", help="administrator login for the steps that need one"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="print what apply would import")
    apply_parser = sub.add_parser("apply", help="steps 1–4")
    apply_parser.add_argument(
        "--write", action="store_true", help="without it, only the plan is printed"
    )
    verify_parser = sub.add_parser("verify", help="step 5")
    verify_parser.add_argument(
        "--urls", required=True, help="JSON list of the old German URLs"
    )
    verify_parser.add_argument(
        "--all",
        action="store_true",
        help="every listed URL must answer (the full site); otherwise every German object must have a listed URL that answers",
    )
    rollback_parser = sub.add_parser("rollback", help="German versions back to drafts")
    rollback_parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    migration = Migration(WP(args.wp, args.user))
    if args.command == "verify":
        with open(args.urls, encoding="utf-8") as handle:
            urls = json.load(handle)
        return 0 if migration.verify(urls, args.all) else 1
    if args.command == "rollback":
        if not args.write:
            print("dry run: add --write to make the German versions drafts")
            return 0
        migration.rollback()
        return 0
    if args.command == "apply" and args.write:
        migration.configure()
    items = migration.plan()
    for item in items:
        print(
            f"{item['kind']:4} {item['source']:>6} {item['label']:60} slug={item['slug'] or '-'} fields={','.join(sorted(item['fields']))}"
        )
    if args.command == "plan" or not getattr(args, "write", False):
        print(
            f"{len(items)} objects; dry run"
            + ("" if args.command == "plan" else ": add --write")
        )
        return 0
    results = migration.apply(items)
    pending = [row for row in results if row.get("status") != "synced"]
    for row in pending:
        print(
            f"{row['kind']} {row['source']} -> {row.get('german') or '-'}: {row['status']}"
        )
    print(
        f"{len(results)} imported, {len(results) - len(pending)} synced, {len(pending)} not synced"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
