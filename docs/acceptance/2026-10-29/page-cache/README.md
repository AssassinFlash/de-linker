# Public page cache — login cookie exclusion

> Correction, 2026-11-01: the original `cache-login_cookie = LOGGED_IN_COOKIE` setting below is invalid and must not be reapplied. LiteSpeed uses that option as the name of its own MD5-valued vary cookie, so it overwrites the WordPress authentication cookie. The correct setting is an empty `cache-login_cookie` (native `_lscache_vary`); keep `cache-exc_cookies = [LOGGED_IN_COOKIE]` as the independent authenticated-page exclusion. Production correction and authenticated Generate readback are tracked in [the current acceptance record](../../2026-10-31/548/INDEX.md).

## Original application and limited evidence

LiteSpeed Cache 7.9.2 on production. Applied 2026-10-29 with the plugin's own options, not a hand-edited rewrite.

| Option | Applied | Rollback |
| --- | --- | --- |
| `litespeed.conf.cache-login_cookie` | `LOGGED_IN_COOKIE` | empty |
| `litespeed.conf.cache-exc_cookies` | `[LOGGED_IN_COOKIE]` | `[]` |

`LOGGED_IN_COOKIE` is WordPress's runtime login-cookie name. The live `.htaccess` LSCACHE block now has `NOCACHE COOKIES` and `LOGIN COOKIE` markers. This does not change the public TTL or the decision that anonymous Home and product pages stay cacheable.

## Readback

Invalid value of the login cookie, 2026-10-29:

| URL | Anonymous | Login cookie |
| --- | --- | --- |
| `https://de-linker.com/` | `X-LiteSpeed-Cache: hit` | `X-LiteSpeed-Cache-Control: no-cache` |
| `https://de-linker.com/product/saj-h2-10k-t3/` | `X-LiteSpeed-Cache: hit` | `X-LiteSpeed-Cache-Control: no-cache` |

The login-cookie response also sent `Cache-Control: no-cache, must-revalidate, max-age=0, no-store, private`.

## Why the original readback was insufficient

The invalid-cookie cache probe established only that a response was not cached. It did not prove that a valid WordPress login cookie survived a response or that authenticated REST requests still worked. Production later showed a valid secure-admin cookie alongside an overwritten 32-character root login cookie, repeated `rest_cookie_invalid_nonce` responses, and core api-fetch nonce-refresh retries. Successful native sign-in alone could not repair it while LiteSpeed continued overwriting the cookie. A corrected acceptance must cover the native login, authenticated REST, official WindPress Generate/store, and retained no-cache behavior.
