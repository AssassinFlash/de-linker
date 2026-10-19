#!/usr/bin/env python3
"""Adversarial battery for campaign #333 (accounts, prices, stock).

Testing only. Never POSTs a matching inquiry digest, never calls the contact
route, and never sends mail. Evidence goes to ~/de-linker-data/campaign-333/.

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
import time
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path.home() / "de-linker-data" / "campaign-333"
WP = "http://127.0.0.1:9184"
INSTANCE = "c333"
PRICED = 4107
PRICED_DE = 6628
RFQ = 1957
RFQ_DE = 6800
PRICE = "1680"
RFQ_AMOUNT = "33250"
GATE = {
    ("visitor", "en"): "Net price after partner sign-in",
    ("visitor", "de"): "Nettopreis nach Partner-Anmeldung",
    ("pending", "en"): "Account under review. Prices after approval.",
    ("pending", "de"): "Ihr Konto wird geprüft. Preise nach Freigabe.",
    ("restricted", "en"): "Not available for your account",
    ("restricted", "de"): "Für Ihr Konto nicht verfügbar",
}
RFQ_LINE = {"en": "Quoted per project", "de": "Angebot pro Projekt"}
CARD_LOGIN = {"en": "Log in for prices", "de": "Preise nach Anmeldung"}
EURO = re.compile(r"€|(?:\bEUR\b)", re.I)
AMOUNT = re.compile(
    r"1[.,]680(?:[.,]00)?|\b1680(?:[.,]00)?\b|33[.,]250(?:[.,]00)?|\b33250(?:[.,]00)?\b"
)
QTY = re.compile(
    r"\b\d+\s*(?:pcs|pieces|units|stück|stueck|stk)\b|\b(?:qty|quantity|menge)\s*[:=]?\s*\d+",
    re.I,
)

ACCOUNTS = ("visitor", "pending", "restricted", "approved")


def euro(text: str) -> bool:
    return bool(EURO.search(text) or AMOUNT.search(text))


def compare_price_row(html: str) -> str:
    """The comparison table's net-price row, attributes included."""
    for row in re.findall(r'(?is)<tr class="linker-compare-row">.*?</tr>', html):
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


def record(bucket: str, entry: dict) -> dict:
    path = EVIDENCE / "evidence" / f"{bucket}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def request(url: str, method: str = "GET", headers: dict | None = None, body: bytes | None = None, timeout: float = 60):
    req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = response.read()
            info = {
                "status": response.status,
                "url": response.geturl(),
                "headers": dict(response.headers.items()),
                "set_cookie": set_cookies(response.headers),
                "body": payload,
                "duration_s": round(time.perf_counter() - started, 3),
            }
            return info
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


def set_cookies(headers) -> list[str]:
    """Every Set-Cookie, intact. Joining on commas splits an Expires date."""
    if headers is None:
        return []
    if hasattr(headers, "get_all"):
        return [value for value in (headers.get_all("Set-Cookie") or []) if value]
    raw = headers.get("Set-Cookie") if hasattr(headers, "get") else None
    return [raw] if raw else []


def absorb_cookies(jar: dict[str, str], result: dict) -> None:
    for raw in result.get("set_cookie") or []:
        pair = raw.split(";", 1)[0]
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        if name.strip():
            jar[name.strip()] = value.strip()


def json_body(result: dict):
    try:
        return json.loads(result["body"].decode())
    except (UnicodeDecodeError, json.JSONDecodeError):
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


def load_accounts() -> dict:
    return json.loads((EVIDENCE / "accounts.json").read_text())


def mint(accounts: dict) -> dict:
    """Fresh customer tokens (TTL 120s) and front-end cookies. Secrets stay in the evidence dir."""
    code = r'''
class C333Mint extends Linker\Tools\Genie\UserContext {
  public function make(int $user, int $expiry): string {
    $payload = $user . "|" . $expiry;
    return $payload . "|" . $this->sign($payload);
  }
}
$mint = new C333Mint();
$now = time();
$ids = array("pending" => 43, "restricted" => 44, "approved" => 45);
$out = array("tokens" => array(), "cookies" => array(), "cookie_name" => LOGGED_IN_COOKIE);
foreach ($ids as $state => $id) {
  $out["tokens"][$state] = $mint->make($id, $now + Linker\Tools\Genie\UserContext::TTL);
  $out["tokens"][$state . "_expired"] = $mint->make($id, $now - 30);
  $expiration = $now + DAY_IN_SECONDS;
  $session = WP_Session_Tokens::get_instance($id)->create($expiration);
  $out["cookies"][$state] = wp_generate_auth_cookie($id, $expiration, "logged_in", $session);
}
$out["tokens"]["missing_user"] = $mint->make(999999, $now + Linker\Tools\Genie\UserContext::TTL);
$out["tokens"]["forged"] = "45|" . ($now + 600) . "|deadbeef";
echo wp_json_encode($out);
'''
    secrets = json.loads(wp_eval(code))
    path = EVIDENCE / "secrets.json"
    path.write_text(json.dumps(secrets))
    path.chmod(0o600)
    secrets["accounts"] = accounts
    return secrets


def auth_headers(state: str, secrets: dict, extra: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if state != "visitor":
        user = secrets["accounts"]["users"][state]
        headers["Authorization"] = basic(user["login"], user["app_password"])
    if extra:
        headers.update(extra)
    return headers


def cookie_header(state: str, secrets: dict) -> dict:
    if state == "visitor":
        return {}
    return {"Cookie": f"{secrets['cookie_name']}={secrets['cookies'][state]}"}


def ability(name: str, args: dict, headers: dict) -> dict:
    query = urllib.parse.urlencode({f"input[{key}]": value for key, value in args.items()})
    url = f"{WP}/wp-json/wp-abilities/v1/abilities/{name}/run?{query}"
    result = request(url, headers=headers)
    body = json_body(result)
    result["json"] = body
    result["body"] = None
    return result


def commerce_of(result: dict) -> dict:
    body = result.get("json") or {}
    if isinstance(body, dict) and "result" in body:
        body = body["result"]
    if not isinstance(body, dict):
        return {}
    return body.get("commerce") or {}


def expect_line(state: str, lang: str, kind: str) -> str:
    if state == "approved" and kind == "priced":
        return ""
    if state == "approved":
        return RFQ_LINE[lang]
    return GATE[(state, lang)]


def grade_commerce(state: str, lang: str, kind: str, commerce: dict, page_text: str | None = None) -> tuple[str, str]:
    line = str(commerce.get("price_line") or "")
    visible = commerce.get("price_visible")
    reason = commerce.get("price_reason")
    if state != "approved" or kind == "rfq":
        if visible or "price" in commerce or euro(line):
            return "defect", "price visible to a closed account or an RFQ product"
        expected = expect_line(state, lang, kind)
        if line != expected:
            return "defect", f"price line {line!r} != {expected!r}"
        if page_text is not None and expected not in page_text:
            return "defect", "product page does not carry the same sentence"
        if kind == "rfq" and page_text is not None and AMOUNT.search(page_text):
            return "defect", "RFQ page still shows the stored amount"
        return "pass", line
    if not visible or commerce.get("price") != PRICE or not euro(line):
        return "defect", f"approved price missing: {commerce}"
    if page_text is not None:
        # The ability line glues the currency symbol in its own span. The page
        # shows the same amount with a space or NBSP, so the raw line is not a
        # substring. Parity is the amount on the page and the visitor gate gone.
        compact = page_text.replace("\xa0", " ").replace("\u00a0", " ")
        amount_on_page = bool(re.search(r"1[.,]680", compact))
        gate_on_page = GATE[("visitor", lang)] in compact
        if not amount_on_page or gate_on_page:
            return "defect", "approved page missed the amount or still showed the visitor gate"
    return "pass", line


def case(case_id: str, state: str, req: dict, result: dict, verdict: str, note: str, price: str = "", stock: str = "", stale: bool = False, meta=None, blocks=None) -> dict:
    return record(
        "cases",
        {
            "id": case_id,
            "account": state,
            "request": req,
            "meta": meta if meta is not None else {"status": result.get("status"), "url": result.get("url")},
            "blocks": blocks or [],
            "price_shown": price,
            "stock_shown": stock,
            "stale_used": stale,
            "duration_s": result.get("duration_s"),
            "verdict": verdict,
            "note": note,
        },
    )


def run_abilities(secrets: dict) -> None:
    for state in ACCOUNTS:
        headers = auth_headers(state, secrets)
        if state != "visitor":
            headers["X-Linker-User-Context"] = secrets["tokens"][state]
        for lang, product, kind in (
            ("en", PRICED, "priced"),
            ("de", PRICED, "priced"),
            ("en", RFQ, "rfq"),
            ("de", RFQ, "rfq"),
        ):
            result = ability("linker/get-product", {"product_id": product, "lang": lang}, headers)
            commerce = commerce_of(result)
            verdict, note = grade_commerce(state, lang, kind, commerce)
            case(
                f"ability-{state}-{kind}-{lang}",
                state,
                {"ability": "linker/get-product", "product_id": product, "lang": lang},
                result,
                verdict,
                note,
                price=str(commerce.get("price_line") or ""),
                stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
            )
        search = ability("linker/search-products", {"text": "H2-10K-T3", "lang": "en"}, headers)
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
            state,
            {"ability": "linker/search-products", "text": "H2-10K-T3", "lang": "en"},
            search,
            verdict,
            note,
            price=str(first.get("price_line") or ""),
            stock="in_stock" if first.get("in_stock") else "out_of_stock",
        )


def run_tokens(secrets: dict) -> None:
    approved_line = None
    guest = ability("linker/get-product", {"product_id": PRICED, "lang": "en"}, {"Accept": "application/json"})
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
            blob = json.dumps(result["json"], ensure_ascii=False) if result["json"] is not None else ""
            leaked = euro(blob)
            case(
                "token-query-only-get-product",
                "visitor",
                {"probe": name, "where": "query parameter, not the header"},
                result,
                "defect" if leaked else "pass",
                f"status {result['status']}; leaked={leaked}",
                price="leaked" if leaked else "",
            )
            continue
        result = ability("linker/get-product", {"product_id": PRICED, "lang": "en"}, headers)
        line = str(commerce_of(result).get("price_line") or "")
        if name == "missing-user":
            # A signature needs the auth salt. Record what an unknown id does; grade below.
            leaked = euro(line) or commerce_of(result).get("price_visible") is True
            verdict = "defect" if leaked else "pass"
            note = "signed token for user 999999 " + ("opened net prices" if leaked else "stayed closed")
        else:
            verdict = "pass" if line == guest_line and not euro(line) else "defect"
            note = f"line {line!r}; guest {guest_line!r}"
        case(f"token-{name}-get-product", "visitor", {"probe": name}, result, verdict, note, price=line)

    forged_route = request(
        f"{WP}/wp-json/linker-ai/v1/genie/turn?x=/wp-abilities/v1/abilities/linker/get-product/run",
        headers={"Accept": "application/json", "X-Linker-User-Context": secrets["tokens"]["approved"]},
    )
    leaked = euro(forged_route["body"].decode(errors="replace"))
    case(
        "token-forged-query-string",
        "visitor",
        {"method": "GET", "url": forged_route["url"]},
        forged_route,
        "defect" if leaked else "pass",
        f"status {forged_route['status']}; price leaked={leaked}",
        price="leaked" if leaked else "",
    )

    post = request(
        f"{WP}/wp-json/wp-abilities/v1/abilities/linker/get-product/run?input[product_id]={PRICED}&input[lang]=en",
        method="POST",
        headers={"Accept": "application/json", "X-Linker-User-Context": secrets["tokens"]["approved"]},
        body=b"{}",
    )
    posted = post["body"].decode(errors="replace")
    case(
        "token-post-not-signed-in",
        "visitor",
        {"method": "POST", "ability": "linker/get-product"},
        post,
        "defect" if euro(posted) else "pass",
        f"status {post['status']}",
        price="leaked" if euro(posted) else "",
    )

    for state, token in (
        ("visitor", None),
        ("pending", secrets["tokens"]["pending"]),
        ("restricted", secrets["tokens"]["restricted"]),
        ("approved", secrets["tokens"]["approved"]),
        ("expired", secrets["tokens"]["approved_expired"]),
        ("forged", secrets["tokens"]["forged"]),
    ):
        headers = {"Accept": "application/json"}
        if token:
            headers["X-Linker-User-Context"] = token
        result = ability("linker/inquiry-status", {}, headers)
        code = (result.get("json") or {}).get("code") if isinstance(result.get("json"), dict) else None
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
            verdict = "pass" if result["status"] == 200 and isinstance(inquiries, list) else "defect"
            note = f"status {result['status']} inquiries {inquiries!r}"[:500]
            blob = json.dumps(inquiries, ensure_ascii=False) if inquiries is not None else ""
            if euro(blob):
                verdict = "defect"
                note = "inquiry status carried an amount for " + state
        case(
            f"inquiry-status-{state}",
            "visitor" if closed else state,
            {"ability": "linker/inquiry-status"},
            result,
            verdict,
            note,
            price=note if "amount" in note else "",
        )
    _ = approved_line


def remint(secrets: dict) -> None:
    fresh = json.loads(
        wp_eval(
            r'''
class C333Mint extends Linker\Tools\Genie\UserContext {
  public function make(int $user, int $expiry): string {
    $payload = $user . "|" . $expiry;
    return $payload . "|" . $this->sign($payload);
  }
}
$mint = new C333Mint();
$now = time();
echo wp_json_encode(array(
  "pending" => $mint->make(43, $now + 120),
  "restricted" => $mint->make(44, $now + 120),
  "approved" => $mint->make(45, $now + 120),
  "approved_expired" => $mint->make(45, $now - 30),
  "missing_user" => $mint->make(999999, $now + 120),
));
'''
        )
    )
    secrets["tokens"].update(fresh)


def run_surfaces(secrets: dict) -> None:
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
    texts: dict[tuple[str, str], str] = {}
    for state in ACCOUNTS:
        headers = {"Accept": "text/html", **cookie_header(state, secrets)}
        for name, url in pages.items():
            result = request(url, headers=headers)
            text = visible_text(result["body"].decode(errors="replace"))
            texts[(state, name)] = text
            kind, lang = name.split("-")
            if kind == "config":
                verdict = "defect" if euro(text) else "pass"
                note = "configurator HTML has a price" if verdict == "defect" else "no price in the server HTML"
                shown = "euro" if verdict == "defect" else ""
            elif kind == "compare":
                # A guest's price cell keeps the gate sentence in the sign-in
                # link's aria-label (compare-price.html). visible_text() drops
                # that attribute, so the row is graded from its own markup.
                raw = result["body"].decode(errors="replace")
                row = compare_price_row(raw)
                priced_ok = GATE[(state, lang)] in row if state != "approved" else bool(re.search(r"1[.,]680", row))
                rfq_sentence = (RFQ_LINE[lang] if state == "approved" else GATE[(state, lang)]) in row
                amount = bool(AMOUNT.search(row))
                if state != "approved":
                    verdict = "pass" if priced_ok and rfq_sentence and not amount else "defect"
                else:
                    verdict = "pass" if priced_ok and rfq_sentence and not re.search(r"33[.,]250|33250", row) else "defect"
                note = f"priced_sentence={priced_ok} rfq_sentence={rfq_sentence} amount={amount}"
                shown = "see note"
            else:
                product_kind = "priced" if kind == "priced" else "rfq"
                headers_json = auth_headers(state, secrets)
                if state != "visitor":
                    headers_json["X-Linker-User-Context"] = secrets["tokens"][state]
                product_id = {"priced-en": PRICED, "priced-de": PRICED, "rfq-en": RFQ, "rfq-de": RFQ}[name]
                looked = ability("linker/get-product", {"product_id": product_id, "lang": lang}, headers_json)
                verdict, note = grade_commerce(state, lang, product_kind, commerce_of(looked), text)
                shown = str(commerce_of(looked).get("price_line") or "")
                result = looked
            case(
                f"page-{state}-{name}",
                state,
                {"url": url},
                result,
                verdict,
                note,
                price=shown if kind != "compare" else note,
            )
        for lang, ids in (("en", f"{PRICED},{RFQ}"), ("de", f"{PRICED},{RFQ}")):
            url = f"{WP}/wp-json/wc/store/v1/products?include={ids}&per_page=2&lang={lang}"
            result = request(url, headers=auth_headers(state, secrets))
            products = json_body(result) or []
            notes = []
            verdict = "pass"
            if not isinstance(products, list) or len(products) < 2:
                verdict = "defect"
                notes.append(f"store status {result['status']} body {str(products)[:200]}")
            for product in products if isinstance(products, list) else []:
                html = unescape(re.sub(r"<[^>]+>", " ", str(product.get("price_html") or "")))
                html = re.sub(r"\s+", " ", html).strip()
                pid = int(product.get("id") or 0)
                kind = "rfq" if pid in (RFQ, RFQ_DE) else "priced"
                if state != "approved":
                    if kind == "rfq":
                        ok = RFQ_LINE[lang] in html and not euro(html)
                    else:
                        ok = (GATE[(state, lang)] in html or CARD_LOGIN[lang] in html) and not euro(html)
                elif kind == "rfq":
                    ok = RFQ_LINE[lang] in html and not AMOUNT.search(html)
                else:
                    ok = euro(html) and bool(re.search(r"1[.,]680", html))
                permalink = str(product.get("permalink") or "")
                link_ok = ("/de/" in permalink) if lang == "de" else ("/de/" not in permalink and "/product/" in permalink)
                if not ok or not link_ok:
                    verdict = "defect"
                notes.append(f"{pid}:{html}:{permalink}:ok={ok}:link={link_ok}")
            case(
                f"store-{state}-{lang}",
                state,
                {"url": url},
                result,
                verdict,
                " | ".join(notes),
                price=" | ".join(notes),
                stock=" ".join(
                    f"{item.get('id')}:{'in' if item.get('is_in_stock') else 'out'}"
                    for item in (products if isinstance(products, list) else [])
                ),
            )


def parse_stream(stream: str) -> tuple[dict | None, list]:
    meta = None
    blocks = []
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


def answer_text(blocks: list) -> str:
    return "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text")


def price_texts(blocks: list) -> list[str]:
    found = []
    for block in blocks:
        for price in block.get("prices") or []:
            if isinstance(price, dict) and price.get("text"):
                found.append(str(price["text"]))
    return found


def run_turns(secrets: dict) -> dict:
    cookies: dict[str, str] = {}
    turns = [
        ("turn-visitor-en-home", "visitor", "en", "home", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-visitor-de-product", "visitor", "de", "product", "Was kostet der SAJ H2-10K-T3?", "priced"),
        ("turn-visitor-en-pageprice", "visitor", "en", "product", "What price is printed on this page for the SAJ H2-10K-T3?", "priced"),
        ("turn-pending-en-dock", "pending", "en", "dock", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-pending-de-home", "pending", "de", "home", "Was kostet der SAJ H2-10K-T3?", "priced"),
        ("turn-restricted-en-product", "restricted", "en", "product", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-restricted-de-dock", "restricted", "de", "dock", "Was kostet der SAJ H2-10K-T3?", "priced"),
        ("turn-approved-en-home", "approved", "en", "home", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-approved-de-product", "approved", "de", "product", "Was kostet der SAJ H2-10K-T3?", "priced"),
        ("turn-approved-en-pageprice", "approved", "en", "product", "What price is printed on this page?", "priced"),
        ("turn-approved-en-compare", "approved", "en", "compare", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-approved-en-config", "approved", "en", "configurator", "What is the net price of the SAJ H2-10K-T3?", "priced"),
        ("turn-approved-en-rfq", "approved", "en", "product", "What is the price of the GoodWe GW208.9-BAT-LCD-G10?", "rfq"),
        ("turn-approved-de-rfq", "approved", "de", "product", "Was kostet das GoodWe GW208.9-BAT-LCD-G10?", "rfq"),
        ("turn-visitor-en-stock", "visitor", "en", "product", "Is the SAJ H2-10K-T3 in stock?", "stock"),
        ("turn-approved-en-stock", "approved", "en", "home", "Is the SAJ H2-10K-T3 in stock?", "stock"),
        ("turn-visitor-de-stock", "visitor", "de", "product", "Ist der SAJ H2-10K-T3 auf Lager?", "stock"),
    ]
    pages = {
        ("home", "en"): {"type": "home", "url": f"{WP}/", "title": "Linker"},
        ("home", "de"): {"type": "home", "url": f"{WP}/de/", "title": "Linker"},
        ("product", "en"): {"type": "product", "url": f"{WP}/product/saj-h2-10k-t3/", "title": "SAJ H2-10K-T3", "product_id": PRICED},
        ("product", "de"): {"type": "product", "url": f"{WP}/de/produkt/saj-h2-10k-t3/", "title": "SAJ H2-10K-T3", "product_id": PRICED_DE},
        ("dock", "en"): {"type": "other", "url": f"{WP}/faq-download/", "title": "Downloads"},
        ("dock", "de"): {"type": "other", "url": f"{WP}/de/faq-download/", "title": "Downloads"},
        ("compare", "en"): {"type": "other", "url": f"{WP}/compare-products/?ids={PRICED},{RFQ}", "title": "Compare"},
        ("configurator", "en"): {"type": "solution", "url": f"{WP}/solution-configurator/", "title": "Solution Configurator"},
    }
    saved = {}
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
            timeout=180,
        )
        raw_cookie = result["headers"].get("Set-Cookie") or result["headers"].get("set-cookie") or ""
        match = re.search(r"linker_conversation=([^;]+)", raw_cookie)
        if match and state == "approved":
            cookies["approved"] = urllib.parse.unquote(match.group(1))
        body = json_body(result) or {}
        stream = body.get("stream") or ""
        meta, blocks = parse_stream(stream) if stream else ({}, [])
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
            lowered = text.lower()
            says_in = ("in stock" in lowered) or ("auf lager" in lowered) or ("lieferbar" in lowered)
            says_out = ("unavailable" in lowered) or ("out of stock" in lowered) or ("nicht verfügbar" in lowered) or ("nicht auf lager" in lowered)
            if says_in and not says_out:
                verdict, note = "pass", "says in stock"
            else:
                verdict, note = "defect", f"stock wording unclear: {text[:240]}"
            if QTY.search(text):
                verdict, note = "defect", "stock answer gave a quantity"
        elif kind == "rfq":
            expected = RFQ_LINE[lang]
            if any(expected in price for price in prices) and not any(euro(price) for price in prices):
                verdict, note = "pass", shown
            else:
                verdict, note = "defect", f"RFQ card {prices!r}"
        else:
            expected = GATE[(state, lang)] if state != "approved" else None
            if state == "approved":
                ok = any(re.search(r"1[.,]680", price) for price in prices)
                verdict, note = ("pass", shown) if ok else ("defect", f"approved card {prices!r}")
            else:
                ok = any(price == expected for price in prices) and not any(euro(price) for price in prices)
                verdict, note = ("pass", shown or text[:180]) if ok else ("defect", f"card {prices!r} text {text[:180]}")
        saved[case_id] = case(
            case_id,
            state,
            {"locale": lang, "page": page["type"], "url": page["url"], "message": question},
            result,
            verdict,
            note,
            price=shown,
            stock=note if kind == "stock" else "",
            stale=stale,
            meta=meta,
            blocks=blocks,
        )
    (EVIDENCE / "conversation-cookie.txt").write_text(cookies.get("approved", ""))
    return cookies


def run_mutation(secrets: dict) -> None:
    done = subprocess.run(
        ["just", "wp", INSTANCE, "eval-file", str(Path(__file__).with_name("inquiry_flow.php"))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    (EVIDENCE / "evidence").mkdir(parents=True, exist_ok=True)
    (EVIDENCE / "evidence" / "inquiry-flow.raw.txt").write_text(done.stdout + "\n--- stderr ---\n" + done.stderr)
    blob = ""
    for line in reversed(done.stdout.splitlines()):
        if line.startswith("{"):
            blob = line
            break
    if done.returncode != 0 or not blob:
        case(
            "inquiry-flow",
            "approved",
            {"script": "inquiry_flow.php"},
            {"status": done.returncode, "duration_s": None, "url": "wp eval-file"},
            "defect",
            "flow script failed",
        )
        return
    report = json.loads(blob)
    before_lines = json.dumps(report.get("visible_lines_before"), ensure_ascii=False)
    after_lines = json.dumps((report.get("after_price") or {}).get("data", {}).get("lines"), ensure_ascii=False)
    price_changed = report.get("price_digest_changed")
    posted = report.get("posted_price") or {}
    shows_new = any(token in after_lines for token in ("1701", "1,701", "1.701"))
    shows_old = "1,680" in after_lines or "1.680" in after_lines
    stale_price = (not shows_new) or shows_old
    sent = report["orders_after"] != report["orders_before"]
    if sent:
        verdict = "defect"
        note = "stale confirmation created an order"
    elif not price_changed:
        verdict = "defect"
        note = "price change left the confirmation digest unchanged"
    elif posted.get("status") != 409:
        verdict = "defect"
        note = f"stale POST status {posted.get('status')} {posted.get('data')}"
    elif stale_price:
        verdict = "defect"
        note = "confirmation card kept the old price"
    else:
        verdict = "pass"
        note = "new price on the card; stale digest refused; no order"
    case(
        "price-change-confirmation",
        "approved",
        {"product": PRICED, "from": PRICE, "to": "1701"},
        {"status": posted.get("status"), "duration_s": None, "url": "/linker-ai/v1/genie/inquiry"},
        verdict,
        note,
        price=after_lines[:500],
        stale="1,680" in after_lines or "1.680" in after_lines,
        meta={"orders_before": report["orders_before"], "orders_after": report["orders_after"], "posted": posted},
    )
    stock_lines = json.dumps((report.get("stock_card") or {}).get("data", {}).get("lines"), ensure_ascii=False)
    stock_posted = report.get("posted_stock") or {}
    if sent:
        stock_verdict, stock_note = "defect", "an order exists after the stock probe"
    elif not report.get("stock_digest_changed"):
        stock_verdict, stock_note = "defect", "stock change left the confirmation digest unchanged"
    elif stock_posted.get("status") != 409:
        stock_verdict, stock_note = "defect", f"stale stock POST {stock_posted.get('status')}"
    else:
        stock_verdict, stock_note = "pass", "out-of-stock digest refused; no order"
    case(
        "stock-change-confirmation",
        "approved",
        {"product": PRICED, "to": "outofstock"},
        {"status": stock_posted.get("status"), "duration_s": None, "url": "/linker-ai/v1/genie/inquiry"},
        stock_verdict,
        stock_note,
        price=stock_lines[:500],
        stock="outofstock",
        stale=False,
        meta={"posted": stock_posted, "digest_changed": report.get("stock_digest_changed")},
    )
    _ = before_lines


def run_stock_edges(secrets: dict) -> None:
    """Push boundaries, then a fresh Genie answer. Restores status afterwards."""
    code = r'''
add_filter("pre_wp_mail", static function () { return true; });
$key = Linker\Commerce\Stock\PushKey::generate();
Linker\Commerce\Stock\PushKey::set($key);
$back = array();
foreach (wc_get_products(array("status" => "publish", "stock_status" => "onbackorder", "limit" => 5, "return" => "ids")) as $id) {
  $back[] = (int) $id;
}
echo wp_json_encode(array("key" => $key, "backorder" => $back));
'''
    setup = json.loads(wp_eval(code))
    key = setup["key"]
    header = {"Content-Type": "application/json", "X-Linker-Stock-Key": key, "Accept": "application/json"}

    def push(items, case_id, note_expect):
        result = request(
            f"{WP}/wp-json/linker/v1/stock",
            method="POST",
            headers=header,
            body=json.dumps({"items": items}).encode(),
        )
        body = json_body(result) or {}
        text = json.dumps(body, ensure_ascii=False)
        ok = note_expect in text
        case(
            case_id,
            "erp",
            {"items": items},
            result,
            "pass" if ok else "defect",
            text[:800],
            stock=text[:300],
            meta={"status": result["status"]},
        )
        return body

    push([{"sku": "DLK-SAJ-H210KT3", "qty": -1}], "stock-negative-qty", "invalid_qty")
    push([{"sku": "DLK-SAJ-H210KT3", "qty": 0}], "stock-qty-on-unmanaged", "not_stock_managed")
    push([{"sku": "DLK-SAJ-H210KT3", "state": "onbackorder"}], "stock-reject-backorder", "invalid_state")
    push(
        [
            {"sku": "DLK-SAJ-H210KT3", "state": "outofstock"},
            {"sku": "DLK-GOODWE-GW2089BATLCDG10", "state": "outofstock"},
        ],
        "stock-state-out",
        "outofstock",
    )
    headers = auth_headers("approved", secrets)
    headers["X-Linker-User-Context"] = secrets["tokens"]["approved"]
    # Token may have expired during the turns. Remint.
    fresh = json.loads(wp_eval(r'''
class C333Mint extends Linker\Tools\Genie\UserContext {
  public function make(int $user, int $expiry): string {
    $payload = $user . "|" . $expiry;
    return $payload . "|" . $this->sign($payload);
  }
}
echo wp_json_encode(array("approved" => (new C333Mint())->make(45, time() + 120)));
'''))
    headers["X-Linker-User-Context"] = fresh["approved"]
    looked = ability("linker/get-product", {"product_id": PRICED, "lang": "en"}, headers)
    commerce = commerce_of(looked)
    page = request(f"{WP}/product/saj-h2-10k-t3/", headers={"Accept": "text/html", **cookie_header("visitor", secrets)})
    text = visible_text(page["body"].decode(errors="replace"))
    out = commerce.get("in_stock") is False and "Currently unavailable" in text
    case(
        "stock-ability-after-out",
        "approved",
        {"product_id": PRICED},
        looked,
        "pass" if out else "defect",
        f"in_stock={commerce.get('in_stock')} page_unavailable={'Currently unavailable' in text}",
        price=str(commerce.get("price_line") or ""),
        stock="out_of_stock" if commerce.get("in_stock") is False else "in_stock",
    )
    store = request(
        f"{WP}/wp-json/wc/store/v1/products?include={PRICED}&lang=en",
        headers=auth_headers("visitor", secrets),
    )
    products = json_body(store) or []
    hidden = products == [] or (isinstance(products, list) and products and products[0].get("is_in_stock") is False)
    case(
        "stock-store-after-out",
        "visitor",
        {"url": store["url"]},
        store,
        "pass" if hidden else "defect",
        json.dumps(products, ensure_ascii=False)[:500],
        stock="hidden_or_out" if hidden else "still_in",
    )
    question = "Is the SAJ H2-10K-T3 in stock right now?"
    payload = {
        "locale": "en",
        "messages": [{"role": "user", "content": question}],
        "page": {"type": "product", "url": f"{WP}/product/saj-h2-10k-t3/", "title": "SAJ H2-10K-T3", "product_id": PRICED},
    }
    turn_headers = auth_headers("visitor", secrets)
    turn_headers["Content-Type"] = "application/json"
    turn = request(
        f"{WP}/wp-json/linker-ai/v1/genie/turn",
        method="POST",
        headers=turn_headers,
        body=json.dumps(payload).encode(),
        timeout=180,
    )
    body = json_body(turn) or {}
    meta, blocks = parse_stream(body.get("stream") or "")
    text = answer_text(blocks)
    lowered = text.lower()
    says_out = any(phrase in lowered for phrase in ("unavailable", "out of stock", "not in stock", "nicht verfügbar"))
    says_in = (("in stock" in lowered) or ("auf lager" in lowered)) and not says_out
    verdict = "pass" if says_out and not says_in and not QTY.search(text) else "defect"
    case(
        "turn-visitor-en-stock-after-out",
        "visitor",
        {"message": question},
        turn,
        verdict,
        text[:400],
        stock=text[:200],
        stale=bool(says_in),
        meta=meta,
        blocks=blocks,
    )
    push([{"sku": "DLK-SAJ-H210KT3", "state": "instock"}], "stock-state-restore", "instock")
    wp_eval('Linker\\Commerce\\Stock\\PushKey::clear(); echo "cleared";')
    # The out-of-stock push above also moved the RFQ SKU. The snapshot's
    # onbackorder rows go back before they are read. is_in_stock() is true
    # for any status other than outofstock, and spec 69's badge follows it.
    if setup["backorder"]:
        id_list = ",".join(str(int(product_id)) for product_id in setup["backorder"])
        wp_eval(
            "foreach (array("
            + id_list
            + ') as $id) { $product = wc_get_product((int) $id); if ($product instanceof WC_Product) { $product->set_stock_status("onbackorder"); $product->save(); } } echo "back";'
        )
        for product_id in setup["backorder"]:
            looked = ability("linker/get-product", {"product_id": product_id, "lang": "en"}, {"Accept": "application/json"})
            commerce = commerce_of(looked)
            page = request(
                f"{WP}/?p={int(product_id)}",
                headers={"Accept": "text/html"},
            )
            text = visible_text(page["body"].decode(errors="replace"))
            badge_in = "In stock" in text or "Auf Lager" in text
            badge_out = "Currently unavailable" in text or "Derzeit nicht verfügbar" in text
            agrees = (commerce.get("in_stock") is True and badge_in and not badge_out) or (
                commerce.get("in_stock") is False and badge_out and not badge_in
            )
            case(
                f"stock-backorder-product-{product_id}",
                "visitor",
                {"product_id": product_id, "woo_status": "onbackorder"},
                looked,
                "pass" if agrees else "defect",
                f"Genie in_stock={commerce.get('in_stock')} page_in={badge_in} page_out={badge_out}; badge follows is_in_stock()",
                stock="in_stock" if commerce.get("in_stock") else "out_of_stock",
            )


def run_logout(secrets: dict, cookies: dict) -> None:
    cookie = cookies.get("approved") or ""
    if not cookie:
        case("logout-missing-cookie", "approved", {}, {"status": 0, "duration_s": 0, "url": ""}, "defect", "approved turn set no conversation cookie")
        return
    owned = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={**auth_headers("approved", secrets), "Cookie": f"linker_conversation={cookie}"},
    )
    guest = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={"Accept": "application/json", "Cookie": f"linker_conversation={cookie}"},
    )
    other = request(
        f"{WP}/wp-json/linker-ai/v1/genie/conversation",
        headers={**auth_headers("pending", secrets), "Cookie": f"linker_conversation={cookie}"},
    )
    owned_text = owned["body"].decode(errors="replace")
    guest_text = guest["body"].decode(errors="replace")
    other_text = other["body"].decode(errors="replace")
    guest_leaks = euro(guest_text)
    other_leaks = euro(other_text) and ("1,680" in other_text or "1.680" in other_text)
    case(
        "logout-guest-replay",
        "visitor",
        {"cookie": "approved conversation replayed signed out"},
        guest,
        "defect" if guest_leaks else "pass",
        f"status {guest['status']}; euro={guest_leaks}",
        price="leaked" if guest_leaks else "",
        stale=guest_leaks,
    )
    case(
        "logout-other-account-replay",
        "pending",
        {"cookie": "approved conversation replayed as pending"},
        other,
        "defect" if other_leaks else "pass",
        f"status {other['status']}; euro={other_leaks}",
        price="leaked" if other_leaks else "",
        stale=other_leaks,
    )
    case(
        "logout-owner-still-sees-history",
        "approved",
        {"cookie": "owner reload"},
        owned,
        "pass" if owned["status"] == 200 else "defect",
        "historical thread kept for the owner" if "1,680" in owned_text or "1680" in owned_text else "owner thread had no stored price line",
        price="historical" if euro(owned_text) else "",
    )


def run_own_order_isolation(secrets: dict) -> None:
    code = r'''
add_filter("pre_wp_mail", static function () { return true; });
$made = array();
foreach (array(43 => "pending", 44 => "restricted", 45 => "approved") as $id => $state) {
  $order = wc_create_order(array("customer_id" => $id));
  $order->set_status("inquiry-received");
  $order->set_currency("EUR");
  $order->set_total("1680");
  $order->save();
  $made[$state] = $order->get_id();
}
echo wp_json_encode($made);
'''
    made = json.loads(wp_eval(code))
    fresh = json.loads(wp_eval(r'''
class C333Mint extends Linker\Tools\Genie\UserContext {
  public function make(int $user, int $expiry): string {
    $payload = $user . "|" . $expiry;
    return $payload . "|" . $this->sign($payload);
  }
}
$mint = new C333Mint();
$now = time() + 120;
echo wp_json_encode(array(
  "pending" => $mint->make(43, $now),
  "restricted" => $mint->make(44, $now),
  "approved" => $mint->make(45, $now),
));
'''))
    seen = {}
    for state, token in fresh.items():
        result = ability("linker/inquiry-status", {}, {"Accept": "application/json", "X-Linker-User-Context": token})
        body = result.get("json") or {}
        if isinstance(body, dict) and "result" in body:
            body = body["result"]
        inquiries = body.get("inquiries") if isinstance(body, dict) else None
        ids = [item.get("id") for item in inquiries] if isinstance(inquiries, list) else []
        totals = [item.get("total") for item in inquiries] if isinstance(inquiries, list) else []
        seen[state] = {"ids": ids, "totals": totals}
        own = made[state] in ids
        foreign = any(value in ids for key, value in made.items() if key != state)
        amount = any(euro(str(total)) or "1680" in str(total) for total in totals)
        if not own or foreign:
            verdict, note = "defect", f"list {ids} expected only {made[state]}"
        elif state != "approved" and amount:
            verdict, note = "defect", f"closed account received totals {totals}"
        else:
            verdict, note = "pass", f"own inquiry only; totals {totals}"
        case(
            f"inquiry-own-{state}",
            state,
            {"created_order": made[state]},
            result,
            verdict,
            note,
            price="" if not amount or state == "approved" else str(totals),
        )
    wp_eval(
        "foreach (array(" + ",".join(str(value) for value in made.values()) + ") as $id) { wp_delete_post((int) $id, true); } echo 'deleted';"
    )


def run_price_turn_after_change(secrets: dict) -> None:
    wp_eval(
        r'''
foreach (array(4107, 6628) as $id) {
  $product = wc_get_product($id);
  $product->set_regular_price("1701");
  $product->set_price("1701");
  $product->save();
}
echo "set";
'''
    )
    try:
        question = "What is the net price of the SAJ H2-10K-T3?"
        payload = {
            "locale": "en",
            "messages": [{"role": "user", "content": question}],
            "page": {"type": "home", "url": f"{WP}/", "title": "Linker"},
        }
        headers = auth_headers("approved", secrets)
        headers["Content-Type"] = "application/json"
        result = request(
            f"{WP}/wp-json/linker-ai/v1/genie/turn",
            method="POST",
            headers=headers,
            body=json.dumps(payload).encode(),
            timeout=180,
        )
        body = json_body(result) or {}
        meta, blocks = parse_stream(body.get("stream") or "")
        text = answer_text(blocks)
        prices = price_texts(blocks)
        shown = " | ".join(prices)
        stale = any(re.search(r"1[.,]680", price) for price in prices) or bool(re.search(r"1[.,]680", text))
        current = any("1,701" in price or "1701" in price for price in prices)
        prose = euro(text)
        if prose or stale or not current:
            verdict = "defect"
        else:
            verdict = "pass"
        case(
            "turn-approved-after-price-change",
            "approved",
            {"message": question, "price": "1701"},
            result,
            verdict,
            shown or text[:240],
            price=shown,
            stale=stale,
            meta=meta,
            blocks=blocks,
        )
    finally:
        wp_eval(
            r'''
foreach (array(4107, 6628) as $id) {
  $product = wc_get_product($id);
  $product->set_regular_price("1680");
  $product->set_price("1680");
  $product->save();
}
echo "restored";
'''
        )


def run_production() -> None:
    base = "https://de-linker.com"
    probes = [
        ("prod-en-price", "en", "/", "What is the net price of the SAJ H2-10K-T3?"),
        ("prod-de-price", "de", "/de/", "Was kostet der SAJ H2-10K-T3?"),
        ("prod-en-stock", "en", "/product/saj-h2-10k-t3/", "Is the SAJ H2-10K-T3 in stock?"),
        ("prod-en-rfq", "en", "/product/goodwe-gw208-9-bat-lcd-g10/", "What is the price of the GoodWe GW208.9-BAT-LCD-G10?"),
    ]
    jar: dict[str, str] = {}
    for case_id, lang, path, question in probes:
        payload = {
            "locale": lang,
            "messages": [{"role": "user", "content": question}],
            "page": {"type": "home" if path in ("/", "/de/") else "product", "url": base + path, "title": "Linker"},
        }
        result = request(
            base + "/wp-json/linker-ai/v1/genie/turn",
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json", "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items())},
            body=json.dumps(payload).encode(),
            timeout=180,
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
            if key.lower() in ("date", "server", "x-powered-by", "content-type", "x-robots-tag", "link", "cache-control")
        }
        record(
            "production",
            {
                "id": case_id,
                "account": "visitor",
                "request": {"url": base + "/wp-json/linker-ai/v1/genie/turn", "locale": lang, "message": question, "page": path},
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
                headers={"Accept": "application/json", "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items())},
            )
            record(
                "production",
                {"id": case_id + "-delete", "conversation_id": conversation, "status": deleted["status"], "final_url": deleted["url"]},
            )


def summarize() -> None:
    path = EVIDENCE / "evidence" / "cases.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    durations = sorted(row["duration_s"] for row in rows if isinstance(row.get("duration_s"), (int, float)))
    summary = {
        "cases": len(rows),
        "counts": counts,
        "defects": [row["id"] + ": " + row["note"] for row in rows if row["verdict"] == "defect"],
    }
    if durations:
        summary["p50_s"] = durations[len(durations) // 2]
        summary["max_s"] = durations[-1]
    (EVIDENCE / "evidence" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
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
    print("self-test ok")


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
    secrets = mint(accounts)
    phases = [
        ("abilities", lambda: run_abilities(secrets)),
        ("tokens", lambda: run_tokens(secrets)),
        ("surfaces", lambda: run_surfaces(secrets)),
        ("orders", lambda: run_own_order_isolation(secrets)),
        ("turns", lambda: run_turns(secrets)),
        ("price-turn", lambda: run_price_turn_after_change(secrets)),
        ("inquiry", lambda: run_mutation(secrets)),
        ("stock", lambda: run_stock_edges(secrets)),
    ]
    cookies: dict[str, str] = {}
    started = False
    try:
        _run_phases(args, phases, cookies, secrets)
    finally:
        wp_eval(
            r'''
Linker\Commerce\Stock\PushKey::clear();
foreach (array(4107 => "1680", 6628 => "1680") as $id => $price) {
  $product = wc_get_product($id);
  if ($product instanceof WC_Product) {
    $product->set_regular_price($price);
    $product->set_price($price);
    $product->set_stock_status("instock");
    $product->save();
  }
}
foreach (array(1957, 6800) as $id) {
  $product = wc_get_product($id);
  if ($product instanceof WC_Product) {
    $product->set_stock_status("onbackorder");
    $product->save();
  }
}
echo "restored";
'''
        )


def _run_phases(args, phases, cookies, secrets) -> None:
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
    run_logout(secrets, cookies)  # noqa: the caller passes this run's secrets
    summarize()


if __name__ == "__main__":
    main()
