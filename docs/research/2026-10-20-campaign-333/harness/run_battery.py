#!/usr/bin/env python3
"""Adversarial battery for campaign #333 (accounts, prices, stock).

Testing only. Never POSTs a matching inquiry digest, never calls the contact
route, and never sends mail. Evidence goes to ~/de-linker-data/campaign-333/.

Catalogue mutations run inside one PHP process (catalog.php and the
eval-file scripts). The shutdown hook restores the snapshot when this
process is SIGKILL'd. The finally block below still forces the known-good
catalogue and reads it back.

    python3 run_battery.py              # local instance c333
    python3 run_battery.py --self-test  # graders only
    python3 run_battery.py --production # question-only smoke, after the local run
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path
from typing import Any

from grade import (
    AMOUNT,
    CARD_LOGIN,
    CHANGED_PRICE,
    D1_NOTE,
    FORGED_QUERY_PATH,
    GATE,
    MISSING_USER,
    PRICE,
    PRICED,
    PRICED_DE,
    QTY,
    RFQ,
    RFQ_DE,
    RFQ_LINE,
    TURN_TIMEOUT,
    ability_matrix,
    answer_text,
    catalog_ok,
    check_fixture,
    euro,
    grade_approved_price_turn,
    grade_changed_price_turn,
    grade_commerce,
    grade_forged_query,
    grade_guest_replay,
    grade_other_replay,
    grade_own_inquiry,
    grade_owner_history,
    grade_price_confirmation,
    grade_push,
    grade_stock_after_out,
    grade_stock_confirmation,
    grade_stock_words,
    grade_transition,
    priced_amount,
    rfq_amount,
    stock_badge_agrees,
    store_includes,
    summarize_rows,
)

ROOT = Path(__file__).resolve().parents[4]
HARNESS = Path(__file__).resolve().parent
EVIDENCE = Path.home() / "de-linker-data" / "campaign-333"
WP = "http://127.0.0.1:9184"
INSTANCE = "c333"

ACCOUNTS = ("visitor", "pending", "restricted", "approved")


def php_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def catalog_require() -> str:
    """The one C333Mint. wp eval cannot see the harness unless it is required."""
    return "require " + php_quote(str(HARNESS / "catalog.php")) + ";"


def account_id(accounts: dict[str, Any], state: str) -> int:
    return int(accounts["users"][state]["id"])


def mint_map(rows: dict[str, tuple[int, int | str]]) -> str:
    """Token name to (user id, seconds from now). ``TTL`` uses the product constant."""
    lines = [
        catalog_require(),
        "$mint = new C333Mint();",
        "$now = time();",
        "$out = array();",
    ]
    for name, (user, offset) in rows.items():
        key = json.dumps(name)
        if offset == "TTL":
            expiry = r"$now + Linker\Tools\Genie\UserContext::TTL"
        else:
            expiry = f"$now + ({int(offset)})"
        lines.append(f"$out[{key}] = $mint->make({int(user)}, {expiry});")
    lines.append("echo wp_json_encode($out);")
    return "\n".join(lines)


def compare_price_row(html: str) -> str:
    """The comparison table's net-price row, attributes included."""
    # findall is list[Any]: a pattern with groups can return tuples.
    found = re.findall(r'(?is)<tr class="linker-compare-row">.*?</tr>', html)
    for row in found:
        if not isinstance(row, str):
            continue
        head = re.search(r"(?is)<th[^>]*>(.*?)</th>", row)
        label = visible_text(head.group(1)).strip().lower() if head else ""
        if label in ("net price", "nettopreis"):
            return row
    return ""


def visible_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text))


def record(bucket: str, entry: dict[str, Any]) -> dict[str, Any]:
    path = EVIDENCE / "evidence" / f"{bucket}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    # Proxy::TURN_BUDGET (wp_remote_post timeout 60). Abilities, HTML and the
    # Store API use this ceiling. A Genie turn passes TURN_TIMEOUT (180), this
    # harness's ceiling for a slow local model, not a second product timeout.
    timeout: float = 60,
) -> dict[str, Any]:
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
            return {
                "status": response.status,
                "url": response.geturl(),
                "headers": dict(response.headers.items()),
                "set_cookie": set_cookies(response.headers),
                "body": payload,
                "duration_s": round(time.perf_counter() - started, 3),
            }
    except urllib.error.HTTPError as error:
        payload = error.read()
        return {
            "status": error.code,
            "url": error.geturl(),
            "headers": dict(error.headers.items()) if error.headers else {},
            "set_cookie": set_cookies(error.headers) if error.headers else [],
            "body": payload,
            "duration_s": round(time.perf_counter() - started, 3),
        }


def set_cookies(headers: Any) -> list[str]:
    """Every Set-Cookie, intact. Joining on commas splits an Expires date."""
    if headers is None:
        return []
    if hasattr(headers, "get_all"):
        return [value for value in (headers.get_all("Set-Cookie") or []) if value]
    raw = headers.get("Set-Cookie") if hasattr(headers, "get") else None
    return [raw] if raw else []


def absorb_cookies(jar: dict[str, str], result: dict[str, Any]) -> None:
    for raw in result.get("set_cookie") or []:
        pair = raw.split(";", 1)[0]
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        if name.strip():
            jar[name.strip()] = value.strip()


def json_body(result: dict[str, Any]) -> Any:
    try:
        return json.loads(result["body"].decode())
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None


def basic(login: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{login}:{password}".encode()).decode()


def wp_eval(code: str) -> str:
    done = subprocess.run(
        ["just", "wp", INSTANCE, "eval", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise RuntimeError(done.stderr[-2000:] or done.stdout[-2000:])
    text = done.stdout
    marker = text.rfind("\n{")
    if text.startswith("{"):
        return text
    if marker != -1:
        return text[marker + 1 :]
    lines = [line for line in text.splitlines() if line and not line.startswith("PHP=")]
    return "\n".join(lines)


def eval_file(name: str) -> dict[str, Any]:
    """Run one harness PHP file. The last JSON line is the report."""
    path = HARNESS / name
    done = subprocess.run(
        ["just", "wp", INSTANCE, "eval-file", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    raw_path = EVIDENCE / "evidence" / f"{path.stem}.raw.txt"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(done.stdout + "\n--- stderr ---\n" + done.stderr)
    blob = ""
    for line in reversed(done.stdout.splitlines()):
        if line.startswith("{"):
            blob = line
            break
    if done.returncode != 0 or not blob:
        detail = (
            done.stderr[-2000:] or done.stdout[-2000:] or f"{name} returned no JSON"
        )
        raise RuntimeError(detail)
    parsed = json.loads(blob)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{name} did not return an object")
    if "error" in parsed and len(parsed) == 1:
        raise RuntimeError(str(parsed["error"]))
    return parsed


def load_accounts() -> dict[str, Any]:
    loaded = json.loads((EVIDENCE / "accounts.json").read_text())
    if not isinstance(loaded, dict):
        raise RuntimeError("accounts.json is not an object")
    return loaded


def mint(accounts: dict[str, Any]) -> dict[str, Any]:
    """Fresh customer tokens (the product TTL) and front-end cookies."""
    pending = account_id(accounts, "pending")
    restricted = account_id(accounts, "restricted")
    approved = account_id(accounts, "approved")
    code = f"""
{catalog_require()}
$mint = new C333Mint();
$now = time();
$ids = array("pending" => {pending}, "restricted" => {restricted}, "approved" => {approved});
$out = array("tokens" => array(), "cookies" => array(), "cookie_name" => LOGGED_IN_COOKIE);
foreach ($ids as $state => $id) {{
  $out["tokens"][$state] = $mint->make($id, $now + Linker\\Tools\\Genie\\UserContext::TTL);
  $out["tokens"][$state . "_expired"] = $mint->make($id, $now - 30);
  $expiration = $now + DAY_IN_SECONDS;
  $session = WP_Session_Tokens::get_instance($id)->create($expiration);
  $out["cookies"][$state] = wp_generate_auth_cookie($id, $expiration, "logged_in", $session);
}}
$out["tokens"]["missing_user"] = $mint->make({MISSING_USER}, $now + Linker\\Tools\\Genie\\UserContext::TTL);
// Unexpired on purpose. UserContext::TTL is 120. 600 only has to outlive
// this probe, so a 401 is the bad signature (deadbeef) and not expiry.
$out["tokens"]["forged"] = "{approved}|" . ($now + 600) . "|deadbeef";
echo wp_json_encode($out);
"""
    loaded = json.loads(wp_eval(code))
    if not isinstance(loaded, dict):
        raise RuntimeError("mint did not return an object")
    secrets: dict[str, Any] = loaded
    path = EVIDENCE / "secrets.json"
    path.write_text(json.dumps(secrets))
    path.chmod(0o600)
    secrets["accounts"] = accounts
    return secrets


def auth_headers(
    state: str, secrets: dict[str, Any], extra: dict[str, str] | None = None
) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if state != "visitor":
        user = secrets["accounts"]["users"][state]
        headers["Authorization"] = basic(user["login"], user["app_password"])
    if extra:
        headers.update(extra)
    return headers


def cookie_header(state: str, secrets: dict[str, Any]) -> dict[str, str]:
    if state == "visitor":
        return {}
    return {"Cookie": f"{secrets['cookie_name']}={secrets['cookies'][state]}"}


def ability(name: str, args: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {f"input[{key}]": value for key, value in args.items()}
    )
    url = f"{WP}/wp-json/wp-abilities/v1/abilities/{name}/run?{query}"
    result = request(url, headers=headers)
    result["json"] = json_body(result)
    result["body"] = None
    return result


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def commerce_of(result: dict[str, Any]) -> dict[str, Any]:
    body = result.get("json") or {}
    if isinstance(body, dict) and "result" in body:
        body = body["result"]
    if not isinstance(body, dict):
        return {}
    commerce = body.get("commerce") or {}
    return commerce if isinstance(commerce, dict) else {}


def case(
    case_id: str,
    *,
    state: str,
    req: dict[str, Any],
    result: dict[str, Any],
    verdict: str,
    note: str,
    price: str = "",
    stock: str = "",
    stale: bool = False,
    meta: Any = None,
    blocks: list[Any] | None = None,
) -> dict[str, Any]:
    return record(
        "cases",
        {
            "id": case_id,
            "account": state,
            "request": req,
            "meta": meta
            if meta is not None
            else {"status": result.get("status"), "url": result.get("url")},
            "blocks": blocks or [],
            "price_shown": price,
            "stock_shown": stock,
            "stale_used": stale,
            "duration_s": result.get("duration_s"),
            "verdict": verdict,
            "note": note,
        },
    )


def script_failed(case_id: str, state: str, name: str, error: BaseException) -> None:
    case(
        case_id,
        state=state,
        req={"script": name},
        result={"status": 1, "duration_s": None, "url": "wp eval-file"},
        verdict="defect",
        note=str(error)[:500],
    )


def run_abilities(secrets: dict[str, Any]) -> None:
    for state in ACCOUNTS:
        headers = auth_headers(state, secrets)
        if state != "visitor":
            headers["X-Linker-User-Context"] = secrets["tokens"][state]
        for lang, product, kind, suffix in ability_matrix():
            result = ability(
                "linker/get-product",
                {"product_id": product, "lang": lang},
                headers,
            )
            commerce = commerce_of(result)
            verdict, note = grade_commerce(state, lang, kind, commerce)
            case(
                f"ability-{state}-{kind}-{lang}{suffix}",
                state=state,
                req={
                    "ability": "linker/get-product",
                    "product_id": product,
                    "lang": lang,
                },
                result=result,
                verdict=verdict,
                note=note,
                price=str(commerce.get("price_line") or ""),
                stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
            )
        search = ability(
            "linker/search-products",
            {"text": "H2-10K-T3", "lang": "en"},
            headers,
        )
        body = search.get("json") or {}
        if isinstance(body, dict) and "result" in body:
            body = body["result"]
        qualified = (body or {}).get("qualified") or []
        first = qualified[0]["commerce"] if qualified else {}
        verdict, note = grade_commerce(state, "en", "priced", first)
        ids = [item.get("product_id") for item in qualified]
        if PRICED not in ids:
            verdict, note = "defect", f"search missed {PRICED}: {ids}"
        case(
            f"search-{state}-en",
            state=state,
            req={
                "ability": "linker/search-products",
                "text": "H2-10K-T3",
                "lang": "en",
            },
            result=search,
            verdict=verdict,
            note=note,
            price=str(first.get("price_line") or ""),
            stock="in_stock" if first.get("in_stock") else "out_of_stock",
        )


def run_tokens(secrets: dict[str, Any]) -> None:
    guest = ability(
        "linker/get-product",
        {"product_id": PRICED, "lang": "en"},
        {"Accept": "application/json"},
    )
    guest_line = str(commerce_of(guest).get("price_line") or "")
    probes = {
        "expired": {"X-Linker-User-Context": secrets["tokens"]["approved_expired"]},
        "forged": {"X-Linker-User-Context": secrets["tokens"]["forged"]},
        "query-only": {},
        "missing-user": {"X-Linker-User-Context": secrets["tokens"]["missing_user"]},
    }
    for name, extra in probes.items():
        headers = {"Accept": "application/json", **extra}
        if name == "query-only":
            # A query parameter is not the header. Stuffing the token into
            # input[X-Linker-User-Context] makes the ability schema reject the
            # call, which is not the forged-query probe.
            token = urllib.parse.quote(secrets["tokens"]["approved"], safe="")
            url = (
                f"{WP}/wp-json/wp-abilities/v1/abilities/linker/get-product/run"
                f"?input[product_id]={PRICED}&input[lang]=en&X-Linker-User-Context={token}"
            )
            result = request(url, headers=headers)
            result["json"] = json_body(result)
            result["body"] = None
            blob = (
                json.dumps(result["json"], ensure_ascii=False)
                if result["json"] is not None
                else ""
            )
            leaked = euro(blob)
            case(
                "token-query-only-get-product",
                state="visitor",
                req={"probe": name, "where": "query parameter, not the header"},
                result=result,
                verdict="defect" if leaked else "pass",
                note=f"status {result['status']}; leaked={leaked}",
                price="leaked" if leaked else "",
            )
            continue
        result = ability(
            "linker/get-product", {"product_id": PRICED, "lang": "en"}, headers
        )
        line = str(commerce_of(result).get("price_line") or "")
        if name == "missing-user":
            leaked = euro(line) or commerce_of(result).get("price_visible") is True
            verdict = "defect" if leaked else "pass"
            note = f"signed token for user {MISSING_USER} " + (
                "opened net prices" if leaked else "stayed closed"
            )
        else:
            verdict = "pass" if line == guest_line and not euro(line) else "defect"
            note = f"line {line!r}; guest {guest_line!r}"
        case(
            f"token-{name}-get-product",
            state="visitor",
            req={"probe": name},
            result=result,
            verdict=verdict,
            note=note,
            price=line,
        )

    # GET of the POST-only turn route is 404. That is not the forged-query
    # contract. The 401 probe below is the one the spec names.
    forged_route = request(
        f"{WP}/wp-json/linker-ai/v1/genie/turn"
        "?x=/wp-abilities/v1/abilities/linker/get-product/run",
        headers={
            "Accept": "application/json",
            "X-Linker-User-Context": secrets["tokens"]["approved"],
        },
    )
    leaked = euro(forged_route["body"].decode(errors="replace"))
    case(
        "token-forged-query-string",
        state="visitor",
        req={"method": "GET", "url": forged_route["url"]},
        result=forged_route,
        verdict="defect" if leaked else "pass",
        note=f"status {forged_route['status']}; price leaked={leaked}",
        price="leaked" if leaked else "",
    )

    forged_user = request(
        WP + FORGED_QUERY_PATH,
        headers={
            "Accept": "application/json",
            "X-Linker-User-Context": secrets["tokens"]["approved"],
        },
    )
    body = forged_user["body"].decode(errors="replace")
    verdict, note = grade_forged_query(forged_user["status"], body)
    case(
        "token-forged-query-string-401",
        state="visitor",
        req={"method": "GET", "url": forged_user["url"]},
        result=forged_user,
        verdict=verdict,
        note=note,
        price="leaked" if "leaked=True" in note else "",
    )

    post = request(
        f"{WP}/wp-json/wp-abilities/v1/abilities/linker/get-product/run"
        f"?input[product_id]={PRICED}&input[lang]=en",
        method="POST",
        headers={
            "Accept": "application/json",
            "X-Linker-User-Context": secrets["tokens"]["approved"],
        },
        body=b"{}",
    )
    posted = post["body"].decode(errors="replace")
    case(
        "token-post-not-signed-in",
        state="visitor",
        req={"method": "POST", "ability": "linker/get-product"},
        result=post,
        verdict="defect" if euro(posted) else "pass",
        note=f"status {post['status']}",
        price="leaked" if euro(posted) else "",
    )

    token_probes: tuple[tuple[str, str | None], ...] = (
        ("visitor", None),
        ("pending", str(secrets["tokens"]["pending"])),
        ("restricted", str(secrets["tokens"]["restricted"])),
        ("approved", str(secrets["tokens"]["approved"])),
        ("expired", str(secrets["tokens"]["approved_expired"])),
        ("forged", str(secrets["tokens"]["forged"])),
    )
    for state, signed in token_probes:
        headers = {"Accept": "application/json"}
        if signed:
            headers["X-Linker-User-Context"] = signed
        result = ability("linker/inquiry-status", {}, headers)
        code = (
            (result.get("json") or {}).get("code")
            if isinstance(result.get("json"), dict)
            else None
        )
        inquiries = None
        body = result.get("json") or {}
        if isinstance(body, dict) and isinstance(body.get("result"), dict):
            inquiries = body["result"].get("inquiries")
        elif isinstance(body, dict):
            inquiries = body.get("inquiries")
        closed = state in ("visitor", "expired", "forged")
        if closed:
            verdict = "pass" if result["status"] == 401 else "defect"
            note = f"status {result['status']} code {code}"
        else:
            verdict = (
                "pass"
                if result["status"] == 200 and isinstance(inquiries, list)
                else "defect"
            )
            note = f"status {result['status']} inquiries {inquiries!r}"[:500]
            blob = (
                json.dumps(inquiries, ensure_ascii=False)
                if inquiries is not None
                else ""
            )
            if euro(blob):
                verdict = "defect"
                note = "inquiry status carried an amount for " + state
        case(
            f"inquiry-status-{state}",
            state="visitor" if closed else state,
            req={"ability": "linker/inquiry-status"},
            result=result,
            verdict=verdict,
            note=note,
            price=note if "amount" in note else "",
        )


def remint(secrets: dict[str, Any]) -> None:
    accounts = secrets["accounts"]
    rows: dict[str, tuple[int, int | str]] = {}
    for state in ("pending", "restricted", "approved"):
        rows[state] = (account_id(accounts, state), "TTL")
    rows["approved_expired"] = (account_id(accounts, "approved"), -30)
    rows["missing_user"] = (MISSING_USER, "TTL")
    fresh = json.loads(wp_eval(mint_map(rows)))
    secrets["tokens"].update(fresh)


def run_surfaces(secrets: dict[str, Any]) -> None:
    remint(secrets)
    pages = {
        "priced-en": f"{WP}/product/saj-h2-10k-t3/",
        "priced-de": f"{WP}/de/produkt/saj-h2-10k-t3/",
        "rfq-en": f"{WP}/product/goodwe-gw208-9-bat-lcd-g10/",
        "rfq-de": f"{WP}/de/produkt/goodwe-gw208-9-bat-lcd-g10/",
        "compare-en": f"{WP}/compare-products/?ids={PRICED},{RFQ}",
        "compare-de": f"{WP}/de/produkte-vergleichen/?ids={PRICED},{RFQ}",
        "config-en": f"{WP}/solution-configurator/",
        "config-de": f"{WP}/de/loesungskonfigurator/",
    }
    for state in ACCOUNTS:
        headers = {"Accept": "text/html", **cookie_header(state, secrets)}
        for name, url in pages.items():
            result = request(url, headers=headers)
            text = visible_text(result["body"].decode(errors="replace"))
            kind, lang = name.split("-")
            if kind == "config":
                verdict = "defect" if euro(text) else "pass"
                note = (
                    "configurator HTML has a price"
                    if verdict == "defect"
                    else "no price in the server HTML"
                )
                shown = "euro" if verdict == "defect" else ""
            elif kind == "compare":
                # A guest's price cell keeps the gate sentence in the sign-in
                # link's aria-label (compare-price.html). visible_text() drops
                # that attribute, so the row is graded from its own markup.
                raw = result["body"].decode(errors="replace")
                row = compare_price_row(raw)
                priced_ok = (
                    GATE[(state, lang)] in row
                    if state != "approved"
                    else priced_amount(row)
                )
                rfq_sentence = (
                    RFQ_LINE[lang] if state == "approved" else GATE[(state, lang)]
                ) in row
                amount = bool(AMOUNT.search(row))
                if state != "approved":
                    verdict = (
                        "pass"
                        if priced_ok and rfq_sentence and not amount
                        else "defect"
                    )
                else:
                    stored = rfq_amount(row)
                    verdict = (
                        "pass"
                        if priced_ok and rfq_sentence and not stored
                        else "defect"
                    )
                note = f"priced_sentence={priced_ok} rfq_sentence={rfq_sentence} amount={amount}"
                shown = "see note"
            else:
                product_kind = "priced" if kind == "priced" else "rfq"
                headers_json = auth_headers(state, secrets)
                if state != "visitor":
                    headers_json["X-Linker-User-Context"] = secrets["tokens"][state]
                product_id = {
                    "priced-en": PRICED,
                    "priced-de": PRICED,
                    "rfq-en": RFQ,
                    "rfq-de": RFQ,
                }[name]
                looked = ability(
                    "linker/get-product",
                    {"product_id": product_id, "lang": lang},
                    headers_json,
                )
                verdict, note = grade_commerce(
                    state, lang, product_kind, commerce_of(looked), text
                )
                shown = str(commerce_of(looked).get("price_line") or "")
                result = looked
            case(
                f"page-{state}-{name}",
                state=state,
                req={"url": url},
                result=result,
                verdict=verdict,
                note=note,
                price=shown if kind != "compare" else note,
            )
        for lang, ids, suffix in store_includes():
            url = f"{WP}/wp-json/wc/store/v1/products?include={ids}&per_page=2&lang={lang}"
            result = request(url, headers=auth_headers(state, secrets))
            products = json_body(result) or []
            notes = []
            verdict = "pass"
            if not isinstance(products, list) or len(products) < 2:
                verdict = "defect"
                notes.append(
                    f"store status {result['status']} body {str(products)[:200]}"
                )
            for product in products if isinstance(products, list) else []:
                html = unescape(
                    re.sub(r"<[^>]+>", " ", str(product.get("price_html") or ""))
                )
                html = re.sub(r"\s+", " ", html).strip()
                pid = int(product.get("id") or 0)
                kind = "rfq" if pid in (RFQ, RFQ_DE) else "priced"
                if state != "approved":
                    if kind == "rfq":
                        ok = RFQ_LINE[lang] in html and not euro(html)
                    else:
                        ok = (
                            GATE[(state, lang)] in html or CARD_LOGIN[lang] in html
                        ) and not euro(html)
                elif kind == "rfq":
                    ok = RFQ_LINE[lang] in html and not AMOUNT.search(html)
                else:
                    ok = euro(html) and priced_amount(html)
                permalink = str(product.get("permalink") or "")
                if lang == "de":
                    link_ok = "/de/" in permalink
                else:
                    link_ok = "/de/" not in permalink and "/product/" in permalink
                if not ok or not link_ok:
                    verdict = "defect"
                notes.append(f"{pid}:{html}:{permalink}:ok={ok}:link={link_ok}")
            note = " | ".join(notes)
            if lang == "de":
                note = f"{note} | {D1_NOTE}"
            case(
                f"store-{state}-{lang}{suffix}",
                state=state,
                req={"url": url},
                result=result,
                verdict=verdict,
                note=note,
                price=" | ".join(notes),
                stock=" ".join(
                    f"{item.get('id')}:{'in' if item.get('is_in_stock') else 'out'}"
                    for item in (products if isinstance(products, list) else [])
                ),
            )


def parse_stream(stream: str) -> tuple[dict[str, Any] | None, list[Any]]:
    meta = None
    blocks: list[Any] = []
    for event in stream.split("\n\n"):
        name = re.search(r"^event: (.+)$", event, re.M)
        data = re.search(r"^data: (.+)$", event, re.M)
        if not name or not data:
            continue
        payload = json.loads(data.group(1))
        if name.group(1) == "meta":
            meta = payload
        elif name.group(1) == "block":
            blocks.append(payload)
    return meta, blocks


def price_texts(blocks: list[Any]) -> list[str]:
    found = []
    for block in blocks:
        for price in block.get("prices") or []:
            if isinstance(price, dict) and price.get("text"):
                found.append(str(price["text"]))
    return found


def run_turns(secrets: dict[str, Any]) -> dict[str, str]:
    cookies: dict[str, str] = {}
    turns = [
        (
            "turn-visitor-en-home",
            "visitor",
            "en",
            "home",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-visitor-de-product",
            "visitor",
            "de",
            "product",
            "Was kostet der SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-visitor-en-pageprice",
            "visitor",
            "en",
            "product",
            "What price is printed on this page for the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-pending-en-dock",
            "pending",
            "en",
            "dock",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-pending-de-home",
            "pending",
            "de",
            "home",
            "Was kostet der SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-restricted-en-product",
            "restricted",
            "en",
            "product",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-restricted-de-dock",
            "restricted",
            "de",
            "dock",
            "Was kostet der SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-approved-en-home",
            "approved",
            "en",
            "home",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-approved-de-product",
            "approved",
            "de",
            "product",
            "Was kostet der SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-approved-en-pageprice",
            "approved",
            "en",
            "product",
            "What price is printed on this page?",
            "priced",
        ),
        (
            "turn-approved-en-compare",
            "approved",
            "en",
            "compare",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-approved-en-config",
            "approved",
            "en",
            "configurator",
            "What is the net price of the SAJ H2-10K-T3?",
            "priced",
        ),
        (
            "turn-approved-en-rfq",
            "approved",
            "en",
            "product",
            "What is the price of the GoodWe GW208.9-BAT-LCD-G10?",
            "rfq",
        ),
        (
            "turn-approved-de-rfq",
            "approved",
            "de",
            "product",
            "Was kostet das GoodWe GW208.9-BAT-LCD-G10?",
            "rfq",
        ),
        (
            "turn-visitor-en-stock",
            "visitor",
            "en",
            "product",
            "Is the SAJ H2-10K-T3 in stock?",
            "stock",
        ),
        (
            "turn-approved-en-stock",
            "approved",
            "en",
            "home",
            "Is the SAJ H2-10K-T3 in stock?",
            "stock",
        ),
        (
            "turn-visitor-de-stock",
            "visitor",
            "de",
            "product",
            "Ist der SAJ H2-10K-T3 auf Lager?",
            "stock",
        ),
    ]
    pages: dict[tuple[str, str], dict[str, Any]] = {
        ("home", "en"): {"type": "home", "url": f"{WP}/", "title": "Linker"},
        ("home", "de"): {"type": "home", "url": f"{WP}/de/", "title": "Linker"},
        ("product", "en"): {
            "type": "product",
            "url": f"{WP}/product/saj-h2-10k-t3/",
            "title": "SAJ H2-10K-T3",
            "product_id": PRICED,
        },
        ("product", "de"): {
            "type": "product",
            "url": f"{WP}/de/produkt/saj-h2-10k-t3/",
            "title": "SAJ H2-10K-T3",
            "product_id": PRICED_DE,
        },
        ("dock", "en"): {
            "type": "other",
            "url": f"{WP}/faq-download/",
            "title": "Downloads",
        },
        ("dock", "de"): {
            "type": "other",
            "url": f"{WP}/de/faq-download/",
            "title": "Downloads",
        },
        ("compare", "en"): {
            "type": "other",
            "url": f"{WP}/compare-products/?ids={PRICED},{RFQ}",
            "title": "Compare",
        },
        ("configurator", "en"): {
            "type": "solution",
            "url": f"{WP}/solution-configurator/",
            "title": "Solution Configurator",
        },
    }
    threads: dict[str, list[dict[str, str]]] = {state: [] for state in ACCOUNTS}
    for case_id, state, lang, where, question, kind in turns:
        page = pages[(where, lang)]
        # The shell sends the thread so far, not a one-message snapshot.
        # A snapshot that repeats the opening question is a fork under #373
        # and the proxy answers 409 without storing the turn.
        threads[state].append({"role": "user", "content": question})
        payload = {"locale": lang, "messages": list(threads[state]), "page": page}
        headers = auth_headers(state, secrets)
        headers["Content-Type"] = "application/json"
        result = request(
            f"{WP}/wp-json/linker-ai/v1/genie/turn",
            method="POST",
            headers=headers,
            body=json.dumps(payload).encode(),
            timeout=TURN_TIMEOUT,
        )
        raw_cookie = "\n".join(result.get("set_cookie") or [])
        match = re.search(r"linker_conversation=([^;]+)", raw_cookie)
        if match and state == "approved":
            cookies["approved"] = urllib.parse.unquote(match.group(1))
        body = json_body(result) or {}
        stream = body.get("stream") or ""
        meta, blocks = parse_stream(stream) if stream else (None, [])
        text = answer_text(blocks)
        if result["status"] == 200 and text:
            threads[state].append({"role": "assistant", "content": text})
        elif threads[state] and threads[state][-1].get("content") == question:
            threads[state].pop()
        prices = price_texts(blocks)
        shown = " | ".join(prices)
        stale = False
        if result["status"] != 200 or not blocks:
            verdict, note = "defect", f"no answer status {result['status']}"
        elif euro(text):
            verdict, note = "defect", "price amount in the prose"
        elif kind == "stock":
            verdict, note = grade_stock_words(text, expect="in")
        elif kind == "rfq":
            expected = RFQ_LINE[lang]
            if any(expected in price for price in prices) and not any(
                euro(price) for price in prices
            ):
                verdict, note = "pass", shown
            else:
                verdict, note = "defect", f"RFQ card {prices!r}"
        else:
            if state == "approved":
                verdict, note, stale = grade_approved_price_turn(
                    result["status"], text, prices
                )
                if verdict == "pass":
                    note = shown
            else:
                expected_line = GATE[(state, lang)]
                ok = any(price == expected_line for price in prices) and not any(
                    euro(price) for price in prices
                )
                verdict, note = (
                    ("pass", shown or text[:180])
                    if ok
                    else ("defect", f"card {prices!r} text {text[:180]}")
                )
        case(
            case_id,
            state=state,
            req={
                "locale": lang,
                "page": page["type"],
                "url": page["url"],
                "message": question,
            },
            result=result,
            verdict=verdict,
            note=note,
            price=shown,
            stock=note if kind == "stock" else "",
            stale=stale,
            meta=meta,
            blocks=blocks,
        )
    (EVIDENCE / "conversation-cookie.txt").write_text(cookies.get("approved", ""))
    return cookies


def run_mutation(secrets: dict[str, Any]) -> None:
    del secrets
    try:
        report = eval_file("inquiry_flow.php")
    except RuntimeError as error:
        script_failed("inquiry-flow", "approved", "inquiry_flow.php", error)
        return
    verdict, note, stale = grade_price_confirmation(report)
    posted = as_dict(report.get("posted_price"))
    after_lines = json.dumps(
        (report.get("after_price") or {}).get("data", {}).get("lines"),
        ensure_ascii=False,
    )
    case(
        "price-change-confirmation",
        state="approved",
        req={"product": PRICED, "from": PRICE, "to": CHANGED_PRICE},
        result={
            "status": posted.get("status"),
            "duration_s": None,
            "url": "/linker-ai/v1/genie/inquiry",
        },
        verdict=verdict,
        note=note,
        price=after_lines[:500],
        stale=stale,
        meta={
            "orders_before": report.get("orders_before"),
            "orders_after": report.get("orders_after"),
            "posted": posted,
        },
    )
    stock_verdict, stock_note = grade_stock_confirmation(report)
    stock_posted = as_dict(report.get("posted_stock"))
    stock_lines = json.dumps(
        (report.get("stock_card") or {}).get("data", {}).get("lines"),
        ensure_ascii=False,
    )
    case(
        "stock-change-confirmation",
        state="approved",
        req={"product": PRICED, "to": "outofstock"},
        result={
            "status": stock_posted.get("status"),
            "duration_s": None,
            "url": "/linker-ai/v1/genie/inquiry",
        },
        verdict=stock_verdict,
        note=stock_note,
        price=stock_lines[:500],
        stock="outofstock",
        meta={
            "posted": stock_posted,
            "digest_changed": report.get("stock_digest_changed"),
        },
    )


def run_stock_edges(secrets: dict[str, Any]) -> None:
    """Push boundaries and one fresh Genie answer. PHP restores on the way out."""
    del secrets
    try:
        report = eval_file("stock_edges.php")
    except RuntimeError as error:
        script_failed("stock-edges", "erp", "stock_edges.php", error)
        return
    for push in report.get("pushes") or []:
        if not isinstance(push, dict):
            continue
        verdict, text = grade_push(push.get("body"), str(push.get("expect") or ""))
        case(
            str(push.get("id")),
            state="erp",
            req={"expect": push.get("expect")},
            result={
                "status": push.get("status"),
                "duration_s": None,
                "url": "/linker/v1/stock",
            },
            verdict=verdict,
            note=text[:800],
            stock=text[:300],
            meta={"status": push.get("status")},
        )
    ability_row = report.get("ability_after_out") or {}
    commerce = ability_row.get("commerce") or {}
    page_text = str(ability_row.get("page_text") or "")
    out = commerce.get("in_stock") is False and "Currently unavailable" in page_text
    case(
        "stock-ability-after-out",
        state="approved",
        req={"product_id": PRICED},
        result={"status": 200, "duration_s": None, "url": "stock_edges.php"},
        verdict="pass" if out else "defect",
        note=(
            f"in_stock={commerce.get('in_stock')} "
            f"page_unavailable={'Currently unavailable' in page_text}"
        ),
        price=str(commerce.get("price_line") or ""),
        stock="out_of_stock" if commerce.get("in_stock") is False else "in_stock",
    )
    products = report.get("store_after_out")
    hidden = products == [] or (
        isinstance(products, list)
        and bool(products)
        and isinstance(products[0], dict)
        and products[0].get("is_in_stock") is False
    )
    case(
        "stock-store-after-out",
        state="visitor",
        req={"include": PRICED},
        result={"status": 200, "duration_s": None, "url": "/wc/store/v1/products"},
        verdict="pass" if hidden else "defect",
        note=json.dumps(products, ensure_ascii=False)[:500],
        stock="hidden_or_out" if hidden else "still_in",
    )
    turn = report.get("turn_after_out") or {}
    meta, blocks = parse_stream(str(turn.get("stream") or ""))
    text = answer_text(blocks)
    verdict, note, says_in = grade_stock_after_out(text, meta)
    case(
        "turn-visitor-en-stock-after-out",
        state="visitor",
        req={"message": "Is the SAJ H2-10K-T3 in stock right now?"},
        result={
            "status": turn.get("status"),
            "duration_s": None,
            "url": "/linker-ai/v1/genie/turn",
        },
        verdict=verdict,
        note=note,
        stock=text[:200],
        stale=says_in,
        meta=meta,
        blocks=blocks,
    )
    for row in report.get("backorder") or []:
        product_id = int(row.get("product_id") or 0)
        commerce = row.get("commerce") or {}
        text = str(row.get("page_text") or "")
        agrees, badge_in, badge_out = stock_badge_agrees(commerce.get("in_stock"), text)
        case(
            f"stock-backorder-product-{product_id}",
            state="visitor",
            req={"product_id": product_id, "woo_status": "onbackorder"},
            result={"status": 200, "duration_s": None, "url": "stock_edges.php"},
            verdict="pass" if agrees else "defect",
            note=(
                f"Genie in_stock={commerce.get('in_stock')} page_in={badge_in} "
                f"page_out={badge_out}; badge follows is_in_stock()"
            ),
            stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
        )
    if not catalog_ok(report.get("catalog") or {}):
        case(
            "stock-restore",
            state="erp",
            req={"readback": report.get("catalog")},
            result={"status": 0, "duration_s": None, "url": "stock_edges.php"},
            verdict="defect",
            note="catalogue was not restored inside the stock script",
        )


def run_logout(secrets: dict[str, Any], cookies: dict[str, str]) -> None:
    cookie = cookies.get("approved") or ""
    if not cookie:
        case(
            "logout-missing-cookie",
            state="approved",
            req={},
            result={"status": 0, "duration_s": 0, "url": ""},
            verdict="defect",
            note="approved turn set no conversation cookie",
        )
        return
    owned = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={
            **auth_headers("approved", secrets),
            "Cookie": f"linker_conversation={cookie}",
        },
    )
    guest = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={
            "Accept": "application/json",
            "Cookie": f"linker_conversation={cookie}",
        },
    )
    other = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={
            **auth_headers("pending", secrets),
            "Cookie": f"linker_conversation={cookie}",
        },
    )
    owned_text = owned["body"].decode(errors="replace")
    guest_text = guest["body"].decode(errors="replace")
    other_text = other["body"].decode(errors="replace")
    guest_verdict, guest_note, guest_leaks = grade_guest_replay(
        int(guest["status"]), guest_text
    )
    other_verdict, other_note, other_leaks = grade_other_replay(
        int(other["status"]), other_text
    )
    owner_verdict, owner_note, owner_euro = grade_owner_history(
        int(owned["status"]), owned_text
    )
    case(
        "logout-guest-replay",
        state="visitor",
        req={"cookie": "approved conversation replayed signed out"},
        result=guest,
        verdict=guest_verdict,
        note=guest_note,
        price="leaked" if guest_leaks else "",
        stale=guest_leaks,
    )
    case(
        "logout-other-account-replay",
        state="pending",
        req={"cookie": "approved conversation replayed as pending"},
        result=other,
        verdict=other_verdict,
        note=other_note,
        price="leaked" if other_leaks else "",
        stale=other_leaks,
    )
    case(
        "logout-owner-still-sees-history",
        state="approved",
        req={"cookie": "owner reload"},
        result=owned,
        verdict=owner_verdict,
        note=owner_note,
        price="historical" if owner_euro else "",
    )


def run_own_order_isolation(secrets: dict[str, Any]) -> None:
    del secrets
    try:
        report = eval_file("orders.php")
    except RuntimeError as error:
        script_failed("inquiry-orders", "approved", "orders.php", error)
        return
    made = as_dict(report.get("made"))
    seen = as_dict(report.get("seen"))
    for state, payload in seen.items():
        inquiries = payload.get("inquiries") if isinstance(payload, dict) else None
        rows = inquiries if isinstance(inquiries, list) else []
        verdict, note, price = grade_own_inquiry(str(state), made, rows)
        case(
            f"inquiry-own-{state}",
            state=str(state),
            req={"created_order": made.get(state)},
            result={
                "status": payload.get("status") if isinstance(payload, dict) else 0,
                "duration_s": None,
                "url": "/wp-abilities/v1/abilities/linker/inquiry-status/run",
            },
            verdict=verdict,
            note=note,
            price=price,
        )
    remaining = report.get("remaining") or []
    if remaining:
        case(
            "inquiry-orders-cleanup",
            state="approved",
            req={"remaining": remaining},
            result={"status": 0, "duration_s": None, "url": "orders.php"},
            verdict="defect",
            note=f"HPOS readback still has {remaining}",
        )


def run_transition() -> None:
    """A local rejected account, then approval, without touching users 43-45."""
    try:
        report = eval_file("transition.php")
    except RuntimeError as error:
        script_failed("transition-script", "rejected", "transition.php", error)
        return
    empty: dict[str, Any] = {"status": 0, "duration_s": None, "url": "transition.php"}
    requests = {
        "transition-subject": {"login": "c333-transition"},
        "transition-pending-closed": {"cookie": "fresh session"},
        "transition-approved-without-relogin": {
            "cookie": "the pending session, no new login"
        },
        "transition-rejected-login": {"auth": "wp_authenticate"},
        "transition-rejected-no-prices": {
            "user": "forced current user after the cookie died"
        },
        "transition-relogin-after-approval": {
            "auth": "wp_authenticate after the rejection was lifted"
        },
        "transition-user-deleted": {"login": "c333-transition"},
    }
    prices = {
        "transition-pending-closed": "pending_commerce",
        "transition-approved-without-relogin": "approved_commerce",
        "transition-rejected-no-prices": "rejected_commerce",
        "transition-relogin-after-approval": "reapproved_commerce",
    }
    for case_id, state, verdict, note in grade_transition(report):
        commerce = as_dict(report.get(prices[case_id])) if case_id in prices else {}
        case(
            case_id,
            state=state,
            req=requests[case_id],
            result=empty,
            verdict=verdict,
            note=note,
            price=str(commerce.get("price_line") or ""),
        )


def run_price_turn_after_change(secrets: dict[str, Any]) -> None:
    del secrets
    try:
        report = eval_file("price_turn.php")
    except RuntimeError as error:
        script_failed(
            "turn-approved-after-price-change", "approved", "price_turn.php", error
        )
        return
    meta, blocks = parse_stream(str(report.get("stream") or ""))
    text = answer_text(blocks)
    prices = price_texts(blocks)
    verdict, note, stale = grade_changed_price_turn(
        int(report.get("status") or 0), text, prices
    )
    case(
        "turn-approved-after-price-change",
        state="approved",
        req={
            "message": "What is the net price of the SAJ H2-10K-T3?",
            "price": CHANGED_PRICE,
        },
        result={
            "status": report.get("status"),
            "duration_s": None,
            "url": "/linker-ai/v1/genie/turn",
        },
        verdict=verdict,
        note=note if note else text[:240],
        price=" | ".join(prices),
        stale=stale,
        meta=meta,
        blocks=blocks,
    )
    if not catalog_ok(report.get("catalog") or {}):
        case(
            "price-turn-restore",
            state="approved",
            req={"readback": report.get("catalog")},
            result={"status": 0, "duration_s": None, "url": "price_turn.php"},
            verdict="defect",
            note="catalogue was not restored inside the price turn",
        )


def run_production() -> None:
    base = "https://de-linker.com"
    probes = [
        ("prod-en-price", "en", "/", "What is the net price of the SAJ H2-10K-T3?"),
        ("prod-de-price", "de", "/de/", "Was kostet der SAJ H2-10K-T3?"),
        (
            "prod-en-stock",
            "en",
            "/product/saj-h2-10k-t3/",
            "Is the SAJ H2-10K-T3 in stock?",
        ),
        (
            "prod-en-rfq",
            "en",
            "/product/goodwe-gw208-9-bat-lcd-g10/",
            "What is the price of the GoodWe GW208.9-BAT-LCD-G10?",
        ),
    ]
    jar: dict[str, str] = {}
    for case_id, lang, path, question in probes:
        payload = {
            "locale": lang,
            "messages": [{"role": "user", "content": question}],
            "page": {
                "type": "home" if path in ("/", "/de/") else "product",
                "url": base + path,
                "title": "Linker",
            },
        }
        result = request(
            base + "/wp-json/linker-ai/v1/genie/turn",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items()),
            },
            body=json.dumps(payload).encode(),
            timeout=TURN_TIMEOUT,
        )
        absorb_cookies(jar, result)
        body = json_body(result) or {}
        stream = body.get("stream") or ""
        meta, blocks = parse_stream(stream) if isinstance(stream, str) else ({}, [])
        text = answer_text(blocks)
        prices = price_texts(blocks)
        header_keep = {
            key: result["headers"].get(key)
            for key in result["headers"]
            if key.lower()
            in (
                "date",
                "server",
                "x-powered-by",
                "content-type",
                "x-robots-tag",
                "link",
                "cache-control",
            )
        }
        record(
            "production",
            {
                "id": case_id,
                "account": "visitor",
                "request": {
                    "url": base + "/wp-json/linker-ai/v1/genie/turn",
                    "locale": lang,
                    "message": question,
                    "page": path,
                },
                "final_url": result["url"],
                "status": result["status"],
                "headers": header_keep,
                "meta": meta,
                "blocks": blocks,
                "price_shown": " | ".join(prices),
                "stock_shown": "",
                "prose": text[:800],
                "stale_used": False,
                "duration_s": result["duration_s"],
                "sent_inquiry": False,
                "sent_contact": False,
            },
        )
        conversation = body.get("conversation_id")
        if conversation:
            deleted = request(
                f"{base}/wp-json/linker-ai/v1/genie/conversations/{conversation}",
                method="DELETE",
                headers={
                    "Accept": "application/json",
                    "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items()),
                },
            )
            record(
                "production",
                {
                    "id": case_id + "-delete",
                    "conversation_id": conversation,
                    "status": deleted["status"],
                    "final_url": deleted["url"],
                },
            )


def summarize() -> None:
    path = EVIDENCE / "evidence" / "cases.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summary = summarize_rows(rows)
    (EVIDENCE / "evidence" / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(summary["notes"])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def self_test() -> None:
    assert euro("€1,680.00")
    assert euro("1.680,00 €")
    assert euro("EUR 1680")
    assert not euro("Net price after partner sign-in")
    assert not euro("SAJ H2-10K-T3")
    assert not euro("Ihr Konto wird geprüft. Preise nach Freigabe.")
    assert AMOUNT.search("33.250,00 €")
    assert not QTY.search("It is in stock.")
    assert QTY.search("12 pcs in the warehouse")
    fixture = json.loads(
        (HARNESS / "tests" / "fixtures" / "recorded-verdicts.json").read_text()
    )
    assert summarize_rows(fixture)["notes"] == "counted 108: 101 pass, 7 defect"
    print("self-test ok")


def force_restore() -> dict[str, Any]:
    code = catalog_require() + "\necho wp_json_encode(c333_force_known_good());\n"
    report = json.loads(wp_eval(code))
    if not isinstance(report, dict):
        raise RuntimeError("catalogue read was not an object")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--from-phase", default="abilities")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.production:
        run_production()
        return
    accounts = load_accounts()
    check_fixture(accounts)
    secrets = mint(accounts)
    phases = [
        ("abilities", lambda: run_abilities(secrets)),
        ("tokens", lambda: run_tokens(secrets)),
        ("surfaces", lambda: run_surfaces(secrets)),
        ("orders", lambda: run_own_order_isolation(secrets)),
        ("transition", run_transition),
        ("turns", lambda: run_turns(secrets)),
        ("price-turn", lambda: run_price_turn_after_change(secrets)),
        ("inquiry", lambda: run_mutation(secrets)),
        ("stock", lambda: run_stock_edges(secrets)),
    ]
    cookies: dict[str, str] = {}
    dirty = False
    try:
        _run_phases(args, phases, cookies, secrets)
    finally:
        catalog = force_restore()
        if not catalog_ok(catalog):
            print(json.dumps(catalog, ensure_ascii=False, indent=2), file=sys.stderr)
            dirty = True
    if dirty:
        raise SystemExit("catalogue was not restored")


def _run_phases(
    args: argparse.Namespace,
    phases: list[tuple[str, Any]],
    cookies: dict[str, str],
    secrets: dict[str, Any],
) -> None:
    started = False
    for name, fn in phases:
        if name == args.from_phase:
            started = True
        if not started:
            continue
        print(f"phase {name}", flush=True)
        if name == "turns":
            cookies.clear()
            cookies.update(fn())
        else:
            fn()
    print("phase logout", flush=True)
    run_logout(secrets, cookies)
    summarize()


if __name__ == "__main__":
    main()
