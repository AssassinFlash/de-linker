"""Real concurrent HTTP checks against the local publication-authority fixture."""

import concurrent.futures
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8888"
RACE = "/wp-json/linker-fixture/v1/publication-race"
CHECKS = []


def request(path, payload=None, method=None, headers=None):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        response = urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read()
    try:
        value = json.loads(raw)
    except ValueError:
        value = {"bytes": len(raw)}
    return response.status, {k.lower(): v for k, v in response.headers.items()}, value


def check(condition, case, **observation):
    if not condition:
        raise AssertionError({"case": case, **observation})
    CHECKS.append({"case": case, **observation})


def restore():
    status, _, _ = request(RACE, {"mode": "restore"})
    if status != 200:
        raise AssertionError("Local race fixture could not restore its own products")


def main():
    restore()
    _, _, manifest = request("/wp-json/linker/v1/publication/manifest")
    a = next(p for p in manifest["products"] if p["model"] == "Fixture-A")
    aid, deid = a["product_id"], a["locale_product_ids"]["de"]
    check(bool(manifest["products"]), "REST authority preserves all-language server scope")
    for lang, expected in [("en", aid), ("de", deid)]:
        out = request("/wp-json/wc/store/v1/products?lang=" + lang + "&linker_publication_internal=1")
        ids = [p["id"] for p in out[2]]
        check(out[0] == 200 and expected in ids and ({aid, deid} - {expected}).isdisjoint(ids),
              "Client marker cannot bypass native " + lang + " language scope", status=out[0])
    for alias in ["shared", "alias"]:
        for method, headers, status, size in [
            ("GET", {}, 200, None), ("HEAD", {}, 200, 0),
            ("GET", {"Range": "bytes=0-4"}, 206, 5),
        ]:
            out = request("/wp-content/uploads/publication-614/" + alias + ".pdf", method=method, headers=headers)
            check(out[0] == status and (size is None or out[2]["bytes"] == size),
                  "Current original/alias " + alias + " " + method, status=out[0], bytes=out[2]["bytes"])
            check("no-store" in out[1].get("cache-control", "") and "private" in out[1]["cache-control"],
                  "Current PDF response has no public cache grant")
    out = request("/wp-content/uploads/publication-614/unassociated.pdf")
    check(out[0] == 410, "Equal-SHA unassociated path is denied", status=out[0])
    out = request("/wp-json/linker/v1/publication/jobs/claim", {"consumer": "knowledge", "worker_id": "unauthorized", "lease_seconds": 30})
    check(out[0] == 401, "Anonymous build-worker claim is denied", status=out[0])
    signal = Path(request(RACE, {"mode": "describe"})[2]["signal"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for kind in ["document", "product"]:
            restore()
            signal.unlink(missing_ok=True)
            held = pool.submit(request, RACE, {"mode": "hold"})
            deadline = time.time() + 10
            while time.time() < deadline:
                if signal.is_file() and signal.read_text() == "waiting":
                    break
                time.sleep(0.025)
            else:
                raise AssertionError("Held HTTP worker did not reach barrier")
            # Parallel connections prevent the built-in server assigning the
            # sole mutation request to the same temporarily held PHP worker.
            changes = [pool.submit(request, RACE, {"mode": kind}) for _ in range(3)]
            first = next(concurrent.futures.as_completed(changes)).result()
            check(first[0] == 200, "Separate HTTP worker withdraws " + kind)
            out = held.result()
            check(out[0] == 200 and out[2]["valid_after_external_change"] is False
                  and first[2]["worker"] != out[2]["worker"],
                  "Primed Redis/request cache sees external " + kind + " withdrawal", status=out[0])
            for changed in changes:
                changed.result()
    restore()
    cart = request("/wp-json/wc/store/v1/cart")
    token = cart[1]["cart-token"]
    added = request("/wp-json/wc/store/v1/cart/add-item", {"id": aid, "quantity": 1}, headers={"Cart-Token": token})
    check(added[0] == 201 and len(added[2]["items"]) == 1, "Native cart adds a current product", status=added[0])
    request(RACE, {"mode": "mirror"})
    for product_id in [aid, deid]:
        out = request("/wp-json/wc/store/v1/products/" + str(product_id))
        check(out[0] == 404, "Native direct ID read denies withdrawn canonical source", status=out[0])
    out = request("/wp-json/wc/store/v1/products?include=" + str(deid) + "&linker_publication_internal=1")
    check(out[0] == 200 and not out[2], "Native collection cannot restore published DE mirror with client marker", status=out[0])
    after = request("/wp-json/wc/store/v1/cart", headers={"Cart-Token": token})
    check(after[0] == 200 and not after[2]["items"], "Native saved cart reveals no current withdrawn product facts", status=after[0])
    for alias in ["shared", "alias"]:
        for method, headers in [("GET", {}), ("HEAD", {}), ("GET", {"Range": "bytes=0-4"})]:
            out = request("/wp-content/uploads/publication-614/" + alias + ".pdf", method=method, headers=headers)
            check(out[0] == 410 and out[2]["bytes"] == 0,
                  "Withdrawn original/alias " + alias + " " + method, status=out[0])
    print(json.dumps({"checks": CHECKS, "count": len(CHECKS)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    finally:
        restore()
