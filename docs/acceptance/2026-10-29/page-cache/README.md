# Public page cache — login cookie exclusion

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
