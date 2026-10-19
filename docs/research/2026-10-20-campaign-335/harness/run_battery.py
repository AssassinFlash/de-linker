"""The #335 battery: EN/DE twins, opening prompts, page drift, language report.

Posts straight at the local Genie service. Edits one product title and one
blog paragraph on the local instance, asks, then restores both. Runs
`wp linker-i18n translate <id> --now` for that title. Never posts a contact
or an inquiry.

Usage (from this directory, after `just up`, `just pull load` and `just serve`):

    uv run --locked python run_battery.py ~/de-linker-data/campaign-335/evidence

The service token is read from the instance (`LINKER_GENIE_SERVICE_TOKEN`).
It is not an environment variable and it is not written into the repo.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

import client as http
import grade

MARKER = "C335DRIFT"
BLOG_PARAGRAPH = "<p>C335DRIFT beacon sentence for the page drift test.</p>\n"
ROOT = Path(__file__).resolve().parents[4]
READ_PAGE = "linker/read-page"
HANDOFF = "linker/handoff-team"

TWINS: list[dict[str, Any]] = [
    {
        "id": "T-pair",
        "surface": "product",
        "en": "Which batteries pair with this inverter?",
        "de": "Welche Batterien passen zu diesem Wechselrichter?",
        "expect_cards": True,
        "expect_handoff": False,
        "expect_numbers": False,
    },
    {
        "id": "T-mppt",
        "surface": "product",
        "en": "How many MPPT trackers does this inverter have?",
        "de": "Wie viele MPPT-Tracker hat dieser Wechselrichter?",
        "expect_cards": False,
        "expect_handoff": False,
        "expect_numbers": True,
    },
    {
        "id": "T-cost",
        "surface": "product",
        "en": "What does this product cost?",
        "de": "Was kostet dieses Produkt?",
        "expect_cards": True,
        "expect_handoff": False,
        "expect_numbers": False,
    },
    {
        "id": "T-mail",
        "surface": "home",
        "en": "What email address should I use to reach your team about a delivery?",
        "de": "Welche E-Mail-Adresse soll ich für eine Lieferung an Ihr Team verwenden?",
        "expect_cards": False,
        "expect_handoff": True,
        "expect_numbers": False,
    },
    {
        "id": "T-address",
        "surface": "imprint",
        "en": "What postal address does this page print?",
        "de": "Welche Postadresse steht auf dieser Seite?",
        "expect_cards": False,
        "expect_handoff": False,
        "expect_numbers": False,
    },
    {
        "id": "T-ban",
        "surface": "product",
        "en": "Add the SAJ H2-10K-T3 to my basket and open the catalogue article.",
        "de": "Legen Sie den SAJ H2-10K-T3 in den Warenkorb und öffnen Sie den Katalog-Artikel.",
        "expect_cards": False,
        "expect_handoff": False,
        "expect_numbers": False,
    },
    {
        "id": "T-sie",
        "surface": "product",
        "en": "Tell me about the SAJ H2-10K-T3.",
        "de": "Du, sag mir mal was zum SAJ H2-10K-T3.",
        "expect_cards": True,
        "expect_handoff": False,
        "expect_numbers": False,
    },
]


def ports(instance: str) -> dict[str, int]:
    text = (Path.home() / "de-linker-local" / "instances.toml").read_text()
    found: dict[str, int] = {}
    seen = False
    for line in text.splitlines():
        if line.strip() == f"[{instance}]":
            seen = True
            continue
        if seen and line.startswith("["):
            break
        if seen:
            match = re.match(r"(port|engine_port|genie_port)\s*=\s*(\d+)", line)
            if match:
                found[match.group(1)] = int(match.group(2))
    if "port" not in found or "genie_port" not in found:
        raise SystemExit(f"no ports for {instance}")
    return found


def wp(instance: str, *args: str, timeout: float = 180) -> str:
    """WP-CLI on the instance. Just echoes the recipe on stderr."""
    result = subprocess.run(
        ["just", "wp", instance, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-2000:]
        raise RuntimeError(f"wp {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def wp_update(
    instance: str, post_id: int, field: str, value: str, directory: Path
) -> None:
    """Write a post field from a file. A title or a post body can break argv."""
    path = directory / f"update-{post_id}-{field}.txt"
    path.write_text(value, encoding="utf-8")
    php = (
        f"$value = file_get_contents({json.dumps(str(path))}); "
        f"wp_update_post(array('ID' => {post_id}, {json.dumps(field)} => $value)); "
        "echo 'ok';"
    )
    wp(instance, "eval", php)


def wp_json(instance: str, php: str) -> Any:
    raw = wp(instance, "eval", php)
    start = raw.find("{")
    start = raw.find("[") if start < 0 else start
    if start < 0:
        raise RuntimeError(f"wp eval did not print JSON: {raw[:400]}")
    return json.loads(raw[start:])


class Journal:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)

    def write(self, name: str, record: dict[str, Any]) -> None:
        path = self.directory / name
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def dump(self, name: str, record: dict[str, Any]) -> None:
        (self.directory / name).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def localize(url: str, origin: str) -> str:
    """A hreflang that still points at the live host becomes this instance."""
    parts = urllib.parse.urlsplit(url)
    base = urllib.parse.urlsplit(origin)
    if parts.netloc and parts.netloc != base.netloc:
        return urllib.parse.urlunsplit(
            (base.scheme, base.netloc, parts.path, parts.query, "")
        )
    if not parts.netloc:
        return origin.rstrip("/") + (parts.path or "/")
    return url


def context_of(page: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": page.get("type") if isinstance(page.get("type"), str) else "other"
    }
    for key in ("url", "title"):
        value = page.get(key)
        if isinstance(value, str) and value:
            out[key] = value
    for key in ("product_id", "post_id", "category_id"):
        value = page.get(key)
        if isinstance(value, int) and value > 0:
            out[key] = value
        elif isinstance(value, str) and value.isdigit() and int(value) > 0:
            out[key] = int(value)
    return out


def short_name(title: str) -> str:
    short = re.sub(r"\s*\([^()]*\)\s*$", "", title).strip()
    return short or title


def load_page(origin: str, url: str) -> dict[str, Any]:
    fetched = http.fetch(localize(url, origin))
    parsed = http.mount(fetched["html"])
    main = http.main_text(fetched["html"])
    return {
        "requested": url,
        "url": fetched["url"],
        "status": fetched["status"],
        "error": fetched["error"],
        "h1": http.h1_text(fetched["html"]),
        "prompts": parsed["prompts"],
        "page": parsed["page"],
        "context": context_of(parsed["page"])
        if parsed["page"]
        else {"type": "other", "url": fetched["url"]},
        "de_url": localize(parsed["de_url"], origin) if parsed["de_url"] else None,
        "main": main,
        "emails": grade.emails_in(main),
        "plz": re.findall(r"\b\d{5}\b", main),
    }


def slim_turn(db: Path, conversation_id: str) -> dict[str, Any]:
    """Route extras the SSE meta does not carry: tool names, mailto, page text."""
    if not db.is_file():
        return {"error": "no turn log"}
    connection = sqlite3.connect(db)
    try:
        row = connection.execute(
            "SELECT understanding, tool_calls, failures, provider, model "
            "FROM turns WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
            (conversation_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return {"error": "no turn row"}
    try:
        understanding = json.loads(row[0] or "{}")
    except json.JSONDecodeError:
        understanding = {}
    try:
        calls = json.loads(row[1] or "[]")
    except json.JSONDecodeError:
        calls = []
    if not isinstance(calls, list):
        calls = []
    jev = understanding.get("jev") if isinstance(understanding, dict) else None
    page_text = ""
    page_title = ""
    mailto = ""
    called = False
    for call in calls:
        if not isinstance(call, dict):
            continue
        raw_result = call.get("result")
        result = raw_result if isinstance(raw_result, dict) else {}
        if call.get("name") == READ_PAGE:
            called = True
            text = result.get("text")
            title = result.get("title")
            if isinstance(text, str):
                page_text = text
            if isinstance(title, str):
                page_title = title
        mailto_value = result.get("mailto")
        if call.get("name") == HANDOFF and isinstance(mailto_value, str):
            mailto = mailto_value
    return {
        "provider": row[3],
        "model": row[4],
        "failures": row[2],
        "route_log": understanding.get("route")
        if isinstance(understanding, dict)
        else None,
        "jev": jev if isinstance(jev, dict) else None,
        "page_error": understanding.get("page_error")
        if isinstance(understanding, dict)
        else None,
        "tools": [call.get("name") for call in calls if isinstance(call, dict)],
        "read_page": called,
        "read_page_title": page_title,
        "read_page_head": page_text[:800],
        "read_page_chars": len(page_text),
        "mailto": mailto,
    }


def record_turn(
    journal: Journal,
    service: http.ServiceClient,
    db: Path,
    *,
    case: str,
    locale: str,
    surface: str,
    messages: list[dict[str, str]],
    page: dict[str, Any],
) -> dict[str, Any]:
    conversation = f"c335-{case}-{locale}-{int(time.time())}"
    # A multi-turn case passes a stable id in the page dict under `_conversation`.
    if isinstance(page.get("_conversation"), str):
        conversation = page["_conversation"]
    context = {key: value for key, value in page.items() if not key.startswith("_")}
    result = service.turn(
        conversation_id=conversation,
        messages=messages,
        locale=locale,
        page=context,
    )
    answer = grade.visible_text(result["blocks"])
    log = slim_turn(db, conversation)
    record = {
        "type": "turn",
        "case": case,
        "locale": locale,
        "surface": surface,
        "page": context,
        "request": result["request"],
        "http": result["http"],
        "duration_s": result["duration_s"],
        "meta": result["meta"],
        "blocks": result["blocks"],
        "answer": answer,
        "log": log,
    }
    journal.write("turns.jsonl", record)
    print(f"{case} {locale} {result['duration_s']}s http={result['http']}", flush=True)
    return record


def grade_twin(
    case: dict[str, Any], en: dict[str, Any], de: dict[str, Any], product_id: int | None
) -> dict[str, Any]:
    reasons = grade.twin_reasons(
        en["blocks"],
        de["blocks"],
        expect_cards=bool(case["expect_cards"]),
        expect_handoff=bool(case["expect_handoff"]),
        expect_numbers=bool(case["expect_numbers"]),
    )
    if case["id"] == "T-cost" and product_id:
        for side, turn in (("en", en), ("de", de)):
            if product_id not in grade.card_ids(turn["blocks"]):
                reasons.append(f"{side} cost cards omit product {product_id}")
            for reason in grade.price_reasons(
                grade.price_lines(turn["blocks"]), side, guest=True
            ):
                reasons.append(f"{side} {reason}")
    if case["id"] == "T-address":
        for side, turn in (("en", en), ("de", de)):
            page_text = turn.get("_main") or ""
            if isinstance(page_text, str) and page_text:
                for reason in address_gap(page_text, turn["answer"]):
                    reasons.append(f"{side} {reason}")
    if case["id"] == "T-mail":
        for side, turn in (("en", en), ("de", de)):
            mailto = (turn.get("log") or {}).get("mailto") or ""
            if not str(mailto).startswith("mailto:"):
                reasons.append(f"{side} handoff tool has no mailto ({mailto!r})")
    banned_shipped = grade.banned_words(en["answer"]) + grade.banned_words(de["answer"])
    if case["id"] == "T-ban" and not banned_shipped:
        pass
    record = {
        "type": "twin",
        "case": case["id"],
        "en_answer": en["answer"],
        "de_answer": de["answer"],
        "block_types": {
            "en": grade.block_types(en["blocks"]),
            "de": grade.block_types(de["blocks"]),
        },
        "cards": {
            "en": grade.card_ids(en["blocks"]),
            "de": grade.card_ids(de["blocks"]),
        },
        "numbers": {
            "en": grade.standalone_numbers(en["answer"]),
            "de": grade.standalone_numbers(de["answer"]),
        },
        "reasons": reasons,
        "mechanical": "defect" if reasons else "pass",
    }
    return record


def address_gap(page_text: str, answer: str) -> list[str]:
    reasons: list[str] = []
    plz = re.findall(r"\b\d{5}\b", page_text)
    if plz and not any(code in answer for code in plz):
        reasons.append("answer misses the page postal code " + ",".join(plz[:3]))
    emails = grade.emails_in(page_text)
    if emails and not any(email in answer for email in emails):
        reasons.append("answer misses the page email")
    if not plz:
        reasons.append("page text has no postal code")
    return reasons


def fixed_prompts(surface: str, locale: str, name: str) -> list[str] | None:
    table: dict[tuple[str, str], list[str]] = {
        ("draft", "en"): grade.DRAFT_EN,
        ("draft", "de"): grade.DRAFT_DE,
        ("account", "en"): grade.ACCOUNT_EN,
        ("account", "de"): grade.ACCOUNT_DE,
        ("faq", "en"): grade.FAQ_EN,
        ("faq", "de"): grade.FAQ_DE,
        ("blog", "en"): grade.BLOG_POST_EN,
        ("blog", "de"): grade.BLOG_POST_DE,
        ("product", "en"): grade.filled(grade.PRODUCT_EN, name),
        ("product", "de"): grade.filled(grade.PRODUCT_DE, name),
        ("category", "en"): grade.filled(grade.CATEGORY_EN, name),
        ("category", "de"): grade.filled(grade.CATEGORY_DE, name),
    }
    return table.get((surface, locale))


def grade_prompts(
    surface: str, locale: str, prompts: list[str], name: str
) -> dict[str, Any]:
    exact = fixed_prompts(surface, locale, name)
    reasons = grade.prompt_reasons(
        prompts,
        locale,
        must_name=name or None,
        english_exact=exact if locale == "en" else None,
        german_exact=exact if locale == "de" else None,
    )
    return {
        "type": "prompts",
        "surface": surface,
        "locale": locale,
        "prompts": prompts,
        "expected": exact,
        "reasons": reasons,
        "mechanical": "defect" if reasons else "pass",
    }


def store_product(origin: str, lang: str) -> dict[str, Any] | None:
    url = f"{origin}/wp-json/wc/store/v1/products?search=H2-10K-T3&per_page=20&lang={lang}"
    try:
        body = http.json_get(url)
    except Exception as error:  # noqa: BLE001 - discovery records the failure
        return {"error": str(error), "lang": lang}
    if not isinstance(body, list):
        return {"error": "store API did not return a list", "lang": lang}
    chosen = None
    for item in body:
        if isinstance(item, dict) and "H2-10K-T3" in str(item.get("name")):
            chosen = item
            break
    if chosen is None:
        return {
            "error": "H2-10K-T3 not in the store API",
            "lang": lang,
            "count": len(body),
        }
    attributes = []
    for attribute in chosen.get("attributes") or []:
        if not isinstance(attribute, dict):
            continue
        terms = [
            term.get("name")
            for term in attribute.get("terms") or []
            if isinstance(term, dict)
        ]
        attributes.append({"name": attribute.get("name"), "terms": terms})
    return {
        "lang": lang,
        "id": chosen.get("id"),
        "name": chosen.get("name"),
        "sku": chosen.get("sku"),
        "permalink": chosen.get("permalink"),
        "prices": chosen.get("prices"),
        "attributes": attributes,
    }


def attribute_gaps(en: dict[str, Any], de: dict[str, Any]) -> list[str]:
    """Numeric tokens in paired attribute terms must survive translation."""
    reasons: list[str] = []
    if en.get("sku") and de.get("sku") and en.get("sku") != de.get("sku"):
        reasons.append(f"sku {en.get('sku')} != {de.get('sku')}")
    de_by_name = {
        str(item.get("name")): item
        for item in de.get("attributes") or []
        if isinstance(item, dict)
    }
    for item in en.get("attributes") or []:
        if not isinstance(item, dict):
            continue
        twin = de_by_name.get(str(item.get("name")))
        en_numbers = grade.standalone_numbers(
            " ".join(str(term) for term in item.get("terms") or [])
        )
        if twin is None:
            if en_numbers:
                reasons.append(f"de attribute missing {item.get('name')}")
            continue
        de_numbers = grade.standalone_numbers(
            " ".join(str(term) for term in twin.get("terms") or [])
        )
        if en_numbers != de_numbers:
            reasons.append(
                f"attribute {item.get('name')} numbers {en_numbers} != {de_numbers}"
            )
    en_name = str(en.get("name") or "")
    de_name = str(de.get("name") or "")
    if "H2-10K-T3" not in de_name:
        reasons.append("de title lost the model code")
    en_figures = grade.standalone_numbers(en_name)
    de_figures = grade.standalone_numbers(de_name)
    if en_figures != de_figures:
        reasons.append(f"title numbers {en_figures} != {de_figures}")
    return reasons


def discover(origin: str, instance: str) -> dict[str, Any]:
    pages_php = r"""
$pages = array();
foreach (array('cart' => wc_get_page_id('cart'), 'account' => wc_get_page_id('myaccount')) as $key => $id) {
    $de = (int) pll_get_post((int) $id, 'de');
    $pages[$key] = array('id' => (int) $id, 'en' => (string) get_permalink((int) $id), 'de' => $de ? (string) get_permalink($de) : '');
}
foreach (array('faq' => 'faq-download', 'imprint' => 'impressum', 'contact' => 'contact') as $key => $slug) {
    $post = get_page_by_path($slug);
    $found = $post instanceof WP_Post ? (int) $post->ID : 0;
    // impressum is the German slug, so the post found by path can be the DE page.
    $en = $found && function_exists('pll_get_post') ? (int) pll_get_post($found, 'en') : $found;
    $de = $found && function_exists('pll_get_post') ? (int) pll_get_post($found, 'de') : 0;
    $en = $en > 0 ? $en : $found;
    $pages[$key] = array('id' => $en, 'en' => $en ? (string) get_permalink($en) : '', 'de' => $de ? (string) get_permalink($de) : '');
}
$posts = get_posts(array('post_type' => 'post', 'post_status' => 'publish', 'numberposts' => 1, 'lang' => 'en'));
$post = $posts[0] ?? null;
$pid = $post instanceof WP_Post ? (int) $post->ID : 0;
$pde = $pid ? (int) pll_get_post($pid, 'de') : 0;
$pages['blog'] = array('id' => $pid, 'en' => $pid ? (string) get_permalink($pid) : '', 'de' => $pde ? (string) get_permalink($pde) : '');
$terms = get_terms(array('taxonomy' => 'product_cat', 'slug' => 'inverters', 'hide_empty' => false, 'lang' => 'en'));
$term = is_array($terms) ? ($terms[0] ?? null) : null;
$tid = $term instanceof WP_Term ? (int) $term->term_id : 0;
$tde = $tid && function_exists('pll_get_term') ? (int) pll_get_term($tid, 'de') : 0;
$pages['category'] = array(
    'id' => $tid,
    'name' => $term instanceof WP_Term ? $term->name : '',
    'en' => $tid ? (string) get_term_link($tid) : '',
    'de' => $tde ? (string) get_term_link($tde) : '',
    'de_name' => $tde ? (string) get_term($tde)->name : '',
);
echo wp_json_encode($pages);
"""
    named = wp_json(instance, pages_php)
    en_product = store_product(origin, "en")
    de_product = store_product(origin, "de")
    surfaces: dict[str, dict[str, Any]] = {}
    if isinstance(en_product, dict) and isinstance(en_product.get("permalink"), str):
        surfaces["product"] = {
            "en": load_page(origin, en_product["permalink"]),
            "de": load_page(origin, de_product["permalink"])
            if isinstance(de_product, dict)
            and isinstance(de_product.get("permalink"), str)
            else None,
        }
    home_en = load_page(origin, origin + "/")
    surfaces["home"] = {
        "en": home_en,
        "de": load_page(origin, home_en["de_url"]) if home_en.get("de_url") else None,
    }
    for key in ("imprint", "draft", "account", "faq", "blog", "category"):
        source_key = "cart" if key == "draft" else key
        info = named.get(source_key) if isinstance(named, dict) else None
        if not isinstance(info, dict):
            continue
        en_url = info.get("en")
        de_url = info.get("de")
        surfaces[key] = {
            "en": load_page(origin, en_url)
            if isinstance(en_url, str) and en_url
            else None,
            "de": load_page(origin, de_url)
            if isinstance(de_url, str) and de_url
            else None,
            "ids": info,
        }
    return {
        "origin": origin,
        "product_en": en_product,
        "product_de": de_product,
        "attribute_reasons": attribute_gaps(en_product or {}, de_product or {})
        if isinstance(en_product, dict) and isinstance(de_product, dict)
        else ["store product missing"],
        "wp_pages": named,
        "surfaces": surfaces,
    }


def public_page(page: dict[str, Any] | None) -> dict[str, Any] | None:
    if page is None:
        return None
    return {key: value for key, value in page.items() if key != "main"}


def prompt_name(surface: str, page: dict[str, Any], ids: dict[str, Any]) -> str:
    """The name Preview::copy fills in. Product names drop a trailing parenthesis.

    The dock reads `data-page` title (PageContext), which for a product is
    `get_the_title` and for a category is `single_term_title`. The visible h1
    is only a fallback when that attribute is missing.
    """
    page_title = (page.get("page") or {}).get("title")
    if surface == "product":
        raw = page_title or page.get("h1") or ""
        return short_name(str(raw))
    if surface == "category":
        title = page_title or ids.get("name") or page.get("h1")
        return str(title)
    return ""


def run_prompts(journal: Journal, found: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    surfaces = found["surfaces"]
    for surface in ("product", "category", "draft", "account", "blog", "faq"):
        pair = surfaces.get(surface) or {}
        raw_ids = pair.get("ids") if isinstance(pair, dict) else None
        ids: dict[str, Any] = raw_ids if isinstance(raw_ids, dict) else {}
        for locale in ("en", "de"):
            page = pair.get(locale) if isinstance(pair, dict) else None
            row: dict[str, Any]
            if not isinstance(page, dict):
                row = {
                    "type": "prompts",
                    "surface": surface,
                    "locale": locale,
                    "reasons": ["page not loaded"],
                    "mechanical": "defect",
                }
            else:
                name = prompt_name(surface, page, ids if locale == "en" else {})
                if locale == "de" and surface == "category":
                    name = str(ids.get("de_name") or name)
                row = grade_prompts(
                    surface, locale, list(page.get("prompts") or []), name
                )
                nested = page.get("page")
                row["url"] = page.get("url")
                row["page_type"] = (
                    nested.get("type") if isinstance(nested, dict) else None
                )
                row["h1"] = page.get("h1")
            journal.write("prompts.jsonl", row)
            rows.append(row)
            print(f"prompts {surface} {locale} {row['mechanical']}", flush=True)
    return rows


def run_twins(
    journal: Journal,
    service: http.ServiceClient,
    db: Path,
    found: dict[str, Any],
    only: str,
) -> list[dict[str, Any]]:
    product_id = None
    product = found.get("product_en")
    if isinstance(product, dict) and isinstance(product.get("id"), int):
        product_id = product["id"]
    rows = []
    for case in TWINS:
        if only and not str(case["id"]).startswith(only):
            continue
        pair = found["surfaces"].get(case["surface"]) or {}
        graded_turns = {}
        for locale, question_key in (("en", "en"), ("de", "de")):
            page = pair.get(locale)
            if not isinstance(page, dict):
                graded_turns[locale] = {
                    "blocks": [],
                    "answer": "",
                    "log": {},
                    "_main": "",
                }
                continue
            turn = record_turn(
                journal,
                service,
                db,
                case=str(case["id"]),
                locale=locale,
                surface=str(case["surface"]),
                messages=[{"role": "user", "content": case[question_key]}],
                page=page["context"],
            )
            turn["_main"] = page.get("main") or ""
            graded_turns[locale] = turn
        row = grade_twin(case, graded_turns["en"], graded_turns["de"], product_id)
        journal.write("twins.jsonl", row)
        rows.append(row)
        print(f"twin {case['id']} {row['mechanical']}", flush=True)
    return rows


def run_language(
    journal: Journal,
    service: http.ServiceClient,
    db: Path,
    found: dict[str, Any],
) -> list[dict[str, Any]]:
    home = found["surfaces"].get("home") or {}
    rows = []
    mixed = "Welche battery passt zum SAJ H2-10K-T3 for a three-phase house?"
    for locale in ("en", "de"):
        page = home.get(locale)
        if not isinstance(page, dict):
            continue
        turn = record_turn(
            journal,
            service,
            db,
            case="L-mixed",
            locale=locale,
            surface="home",
            messages=[{"role": "user", "content": mixed}],
            page=page["context"],
        )
        reasons = grade.answer_language_reasons(mixed, turn["answer"], locale)
        row = {
            "type": "language",
            "case": f"L-mixed-{locale}",
            "question": mixed,
            "locale": locale,
            "answer": turn["answer"],
            "language": grade.language_of(turn["answer"]),
            "reasons": reasons,
            "mechanical": "defect" if reasons else "pass",
            "report_only": True,
        }
        journal.write("language.jsonl", row)
        rows.append(row)
    switches = [
        (
            "L-switch-en",
            "en",
            "Which batteries pair with the SAJ H2-10K-T3?",
            "Wie viele MPPT-Tracker hat er?",
        ),
        (
            "L-switch-de",
            "de",
            "Welche Batterien passen zum SAJ H2-10K-T3?",
            "How many MPPT trackers does it have?",
        ),
    ]
    for case, locale, first, second in switches:
        page = home.get(locale)
        if not isinstance(page, dict):
            continue
        conversation = f"c335-{case}-{int(time.time())}"
        context = dict(page["context"])
        context["_conversation"] = conversation
        first_turn = record_turn(
            journal,
            service,
            db,
            case=case,
            locale=locale,
            surface="home",
            messages=[{"role": "user", "content": first}],
            page=context,
        )
        second_turn = record_turn(
            journal,
            service,
            db,
            case=case,
            locale=locale,
            surface="home",
            messages=[
                {"role": "user", "content": first},
                {"role": "assistant", "content": first_turn["answer"]},
                {"role": "user", "content": second},
            ],
            page=context,
        )
        reasons = grade.answer_language_reasons(second, second_turn["answer"], locale)
        row = {
            "type": "language",
            "case": case,
            "locale": locale,
            "second_question": second,
            "answer": second_turn["answer"],
            "language": grade.language_of(second_turn["answer"]),
            "reasons": reasons,
            "mechanical": "defect" if reasons else "pass",
            "report_only": True,
        }
        journal.write("language.jsonl", row)
        rows.append(row)
        print(f"language {case} {row['mechanical']} {row['language']}", flush=True)
    for locale, question in (("en", "H2-10K-T3"), ("de", "H2-10K-T3")):
        page = home.get(locale)
        if not isinstance(page, dict):
            continue
        turn = record_turn(
            journal,
            service,
            db,
            case="L-bare",
            locale=locale,
            surface="home",
            messages=[{"role": "user", "content": question}],
            page=page["context"],
        )
        reasons = grade.answer_language_reasons(question, turn["answer"], locale)
        row = {
            "type": "language",
            "case": f"L-bare-{locale}",
            "locale": locale,
            "question": question,
            "answer": turn["answer"],
            "language": grade.language_of(turn["answer"]),
            "reasons": reasons,
            "mechanical": "defect" if reasons else "pass",
            "report_only": True,
        }
        journal.write("language.jsonl", row)
        rows.append(row)
    return rows


def drift_ask(
    journal: Journal,
    service: http.ServiceClient,
    db: Path,
    *,
    case: str,
    locale: str,
    page: dict[str, Any],
    question: str,
    marker: str,
) -> dict[str, Any]:
    turn = record_turn(
        journal,
        service,
        db,
        case=case,
        locale=locale,
        surface="drift",
        messages=[{"role": "user", "content": question}],
        page=page["context"],
    )
    log = turn.get("log") or {}
    tool_text = str(log.get("read_page_head") or "")
    # The head is 800 characters. A marker past that still counts via a second look.
    tool_has = marker in tool_text or marker in str(log.get("read_page_title") or "")
    if log.get("read_page") and not tool_has:
        tool_has = marker_in_log(db, str(turn["request"]["conversation_id"]), marker)
    http_has = marker in (page.get("main") or "") or marker in (page.get("h1") or "")
    answer_has = marker in turn["answer"]
    attribution = grade.drift_attribution(
        http_has_marker=http_has,
        tool_called=bool(log.get("read_page")),
        tool_has_marker=tool_has,
        answer_has_marker=answer_has,
    )
    row = {
        "type": "drift",
        "case": case,
        "locale": locale,
        "question": question,
        "url": page.get("url"),
        "h1": page.get("h1"),
        "page_title": (page.get("context") or {}).get("title"),
        "prompts": page.get("prompts"),
        "answer": turn["answer"],
        "http_has_marker": http_has,
        "tool_called": bool(log.get("read_page")),
        "tool_has_marker": tool_has,
        "answer_has_marker": answer_has,
        "read_page_head": log.get("read_page_head"),
        "attribution": attribution,
        "meta": turn.get("meta"),
    }
    journal.write("drift.jsonl", row)
    print(f"drift {case} {attribution}", flush=True)
    return row


def marker_in_log(db: Path, conversation_id: str, marker: str) -> bool:
    if not db.is_file():
        return False
    connection = sqlite3.connect(db)
    try:
        row = connection.execute(
            "SELECT tool_calls FROM turns WHERE conversation_id = ? ORDER BY id DESC LIMIT 1",
            (conversation_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return False
    return marker in (row[0] or "")


def run_drift(
    journal: Journal,
    service: http.ServiceClient,
    db: Path,
    instance: str,
    origin: str,
    found: dict[str, Any],
) -> dict[str, Any]:
    product = (found["surfaces"].get("product") or {}).get("en")
    blog = (found["surfaces"].get("blog") or {}).get("en")
    de_product_url = None
    de_page = (found["surfaces"].get("product") or {}).get("de")
    if isinstance(de_page, dict):
        de_product_url = de_page.get("url")
    en_id = (found.get("product_en") or {}).get("id")
    blog_id = ((found["surfaces"].get("blog") or {}).get("ids") or {}).get("id")
    evidence: dict[str, Any] = {"marker": MARKER, "restored": False}
    if not isinstance(product, dict) or not isinstance(en_id, int):
        evidence["error"] = "no english product to edit"
        return evidence
    original_title = wp(instance, "post", "get", str(en_id), "--field=post_title")
    new_title = grade.title_with_marker(original_title, MARKER)
    original_blog = ""
    if isinstance(blog_id, int) and blog_id > 0:
        original_blog = wp(
            instance, "post", "get", str(blog_id), "--field=post_content"
        )
        (journal.directory / "blog-original.html").write_text(
            original_blog, encoding="utf-8"
        )
    de_id = 0
    de_title_before = ""
    try:
        de_raw = wp(instance, "eval", f"echo (int) pll_get_post({en_id}, 'de');")
        found_id = re.search(r"\d+", de_raw)
        de_id = int(found_id.group(0)) if found_id is not None else 0
        if de_id:
            de_title_before = wp(
                instance, "post", "get", str(de_id), "--field=post_title"
            )
        evidence["edit"] = {
            "product_id": en_id,
            "de_product_id": de_id,
            "title_before": original_title,
            "title_after": new_title,
            "de_title_before": de_title_before,
            "blog_id": blog_id,
        }
        # The twin turns already warmed the product URL in both languages.
        # This warms the blog, whose body is the marker the title is not.
        if isinstance(blog, dict):
            drift_ask(
                journal,
                service,
                db,
                case="D-blog-warm",
                locale="en",
                page=blog,
                question="What is this post about? One sentence.",
                marker=MARKER,
            )
        wp_update(instance, en_id, "post_title", new_title, journal.directory)
        if original_blog and isinstance(blog_id, int):
            wp_update(
                instance,
                blog_id,
                "post_content",
                original_blog + BLOG_PARAGRAPH,
                journal.directory,
            )
        fresh_product = load_page(origin, str(product.get("url")))
        evidence["product_http_after_edit"] = {
            "h1": fresh_product["h1"],
            "prompts": fresh_product["prompts"],
            "title": fresh_product["context"].get("title"),
            "marker_in_h1": MARKER in fresh_product["h1"],
            "marker_in_prompts": any(
                MARKER in prompt for prompt in fresh_product["prompts"]
            ),
        }
        evidence["product_immediate"] = drift_ask(
            journal,
            service,
            db,
            case="D-title-immediate",
            locale="en",
            page=fresh_product,
            question="Quote this page's heading exactly.",
            marker=MARKER,
        )
        if isinstance(blog, dict) and original_blog:
            fresh_blog = load_page(origin, str(blog.get("url")))
            evidence["blog_http_after_edit"] = {
                "marker_in_main": MARKER in (fresh_blog.get("main") or ""),
                "h1": fresh_blog["h1"],
            }
            evidence["blog_immediate"] = drift_ask(
                journal,
                service,
                db,
                case="D-body-immediate",
                locale="en",
                page=fresh_blog,
                question="Quote the unusual token at the end of this post.",
                marker=MARKER,
            )
        translate_out = ""
        translate_code = 0
        try:
            translate_out = wp(
                instance, "linker-i18n", "translate", str(en_id), "--now", timeout=240
            )
        except RuntimeError as error:
            translate_out = str(error)
            translate_code = 1
        de_title_after = ""
        if de_id:
            de_title_after = wp(
                instance, "post", "get", str(de_id), "--field=post_title"
            )
        evidence["translation"] = {
            "code": translate_code,
            "output": translate_out[-2000:],
            "de_title_before": de_title_before,
            "de_title_after": de_title_after,
            "model_code_kept": "H2-10K-T3" in de_title_after,
            "marker_kept": MARKER in de_title_after,
            "title_numbers_before": grade.standalone_numbers(de_title_before),
            "title_numbers_after": grade.standalone_numbers(de_title_after),
            "en_title_numbers": grade.standalone_numbers(new_title),
        }
        # The German URL was warmed by the twins, before this translation.
        # No restart yet: a stale read here is the page cache, not the renderer.
        if de_product_url:
            de_cached = load_page(origin, de_product_url)
            evidence["de_http_cached"] = {
                "h1": de_cached["h1"],
                "prompts": de_cached["prompts"],
                "title": de_cached["context"].get("title"),
            }
            evidence["de_cached"] = drift_ask(
                journal,
                service,
                db,
                case="D-de-cached",
                locale="de",
                page=de_cached,
                question="Zitieren Sie die Überschrift dieser Seite wortgetreu.",
                marker=MARKER,
            )
        print("restarting genie to drop the page cache", flush=True)
        restarted = subprocess.run(
            ["just", "serve", instance],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        evidence["serve_restart"] = {
            "code": restarted.returncode,
            "tail": (restarted.stdout + restarted.stderr)[-1500:],
        }
        if restarted.returncode == 0:
            fresh_product = load_page(origin, str(product.get("url")))
            evidence["product_after_restart"] = drift_ask(
                journal,
                service,
                db,
                case="D-title-fresh",
                locale="en",
                page=fresh_product,
                question="Quote this page's heading exactly.",
                marker=MARKER,
            )
            if isinstance(blog, dict) and original_blog:
                fresh_blog = load_page(origin, str(blog.get("url")))
                evidence["blog_after_restart"] = drift_ask(
                    journal,
                    service,
                    db,
                    case="D-body-fresh",
                    locale="en",
                    page=fresh_blog,
                    question="Quote the unusual token at the end of this post.",
                    marker=MARKER,
                )
            if de_product_url:
                de_fresh = load_page(origin, de_product_url)
                evidence["de_http"] = {
                    "h1": de_fresh["h1"],
                    "prompts": de_fresh["prompts"],
                    "title": de_fresh["context"].get("title"),
                }
                evidence["de_fresh"] = drift_ask(
                    journal,
                    service,
                    db,
                    case="D-de-fresh",
                    locale="de",
                    page=de_fresh,
                    question="Zitieren Sie die Überschrift dieser Seite wortgetreu.",
                    marker=MARKER,
                )
                cost = record_turn(
                    journal,
                    service,
                    db,
                    case="D-de-cost",
                    locale="de",
                    surface="product",
                    messages=[
                        {"role": "user", "content": "Was kostet dieses Produkt?"}
                    ],
                    page=de_fresh["context"],
                )
                evidence["de_cost"] = {
                    "answer": cost["answer"],
                    "prices": grade.price_lines(cost["blocks"]),
                    "reasons": grade.price_reasons(
                        grade.price_lines(cost["blocks"]), "de", guest=True
                    ),
                    "cards": grade.card_ids(cost["blocks"]),
                }
    finally:
        try:
            wp_update(instance, en_id, "post_title", original_title, journal.directory)
            if de_id and de_title_before:
                wp_update(
                    instance, de_id, "post_title", de_title_before, journal.directory
                )
            if original_blog and isinstance(blog_id, int):
                wp_update(
                    instance, blog_id, "post_content", original_blog, journal.directory
                )
            evidence["restored"] = True
            evidence["title_restored_to"] = wp(
                instance, "post", "get", str(en_id), "--field=post_title"
            )
        except RuntimeError as error:
            evidence["restore_error"] = str(error)
    return evidence


def mail_names(instance: str) -> list[str]:
    mail = Path.home() / "de-linker-local" / instance / "mail"
    if not mail.is_dir():
        return []
    return sorted(path.name for path in mail.iterdir() if path.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--instance", default="c335")
    parser.add_argument(
        "--only", default="", help="case id prefix; limits the twin phase"
    )
    parser.add_argument(
        "--phase",
        action="append",
        choices=["prompts", "twins", "language", "drift"],
        help="which phases to run (default: all). drift edits one title and restores it",
    )
    args = parser.parse_args(argv)
    phases = set(args.phase or ["prompts", "twins", "language", "drift"])
    found_ports = ports(args.instance)
    origin = f"http://127.0.0.1:{found_ports['port']}"
    token = wp(
        args.instance, "config", "get", "LINKER_GENIE_SERVICE_TOKEN", "--type=constant"
    )
    token = token.splitlines()[-1].strip()
    service = http.ServiceClient(f"http://127.0.0.1:{found_ports['genie_port']}", token)
    db = Path.home() / "de-linker-local" / args.instance / "genie" / "turns.sqlite"
    journal = Journal(args.evidence)
    mail_before = mail_names(args.instance)
    print("discover", flush=True)
    found = discover(origin, args.instance)
    saved = {
        "origin": origin,
        "genie": f"http://127.0.0.1:{found_ports['genie_port']}",
        "product_en": found["product_en"],
        "product_de": found["product_de"],
        "attribute_reasons": found["attribute_reasons"],
        "wp_pages": found["wp_pages"],
        "surfaces": {
            key: {
                "en": public_page(value.get("en")),
                "de": public_page(value.get("de")),
                "ids": value.get("ids"),
            }
            for key, value in found["surfaces"].items()
        },
    }
    journal.dump("discover.json", saved)
    prompts = run_prompts(journal, found) if "prompts" in phases else []
    twins = (
        run_twins(journal, service, db, found, args.only) if "twins" in phases else []
    )
    language = run_language(journal, service, db, found) if "language" in phases else []
    drift: dict[str, Any] = {}
    if "drift" in phases:
        drift = run_drift(journal, service, db, args.instance, origin, found)
        journal.dump("drift.json", drift)
    mail_after = mail_names(args.instance)
    summary = {
        "prompts": [
            {
                "surface": row["surface"],
                "locale": row["locale"],
                "mechanical": row["mechanical"],
            }
            for row in prompts
        ],
        "twins": [
            {
                "case": row["case"],
                "mechanical": row["mechanical"],
                "reasons": row["reasons"],
            }
            for row in twins
        ],
        "language": [
            {
                "case": row["case"],
                "mechanical": row["mechanical"],
                "language": row.get("language"),
            }
            for row in language
        ],
        "attribute_reasons": found["attribute_reasons"],
        "drift_attributions": {
            key: value.get("attribution")
            for key, value in drift.items()
            if isinstance(value, dict) and "attribution" in value
        },
        "mail_before": mail_before,
        "mail_after": mail_after,
        "mail_grew": mail_before != mail_after,
        "restored": drift.get("restored"),
    }
    journal.dump("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
