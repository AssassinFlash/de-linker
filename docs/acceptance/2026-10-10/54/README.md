# #54 parity archive (2026-10-10)

Filenames: `<page>-<viewport>-<lang>-<state>.png` per `docs/acceptance/protocol.md` §3C.

Pages: cart, checkout (empty Proforma request / login gate), account, shop, product (`goodwe-gw60k-sts-g10`), archive (`ci-ac-coupled`).
Viewports: 1440, 390. Languages: en, de. States: `local` (`http://127.0.0.1:8912`) and `live` (`https://de-linker.com`). 48 files.

HTTP while capturing (`python3 /tmp/t54-parity-shots.py`):

- All **live** EN/DE URLs: 200.
- Local EN: 200 for every page type.
- Local DE cart/checkout/account/shop/archive: **404** (Polylang languages empty on this instance; `#12` W2 Twins pairing not merged). Local DE product URLs 200 (same English slug under `/de/produkt/…` is not routed).

Judgement of visual parity is for the review line; this directory is the archive only.

WindPress rebuild demo (not a screenshot): class `ring-4` added to `checkout_page.html` → provider scan HIT → `WindPress\WindPress\Core\Cache::save_cache` → visitor HTML `<link id='windpress-cached-css' href='…/tailwind.css?ver=1791629382'>` and the CSS body started with `/* t54-windpress-rebuild 1791629382 */`. Template restored afterwards.
